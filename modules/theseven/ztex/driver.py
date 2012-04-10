# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



#########################################
# ZTEX USB FPGA Module low level driver #
#########################################



import time
import usb
import struct
import traceback
from array import array
from threading import RLock



class ZtexDevice(object):
  

  def __init__(self, proxy, serial, takeover, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.serial = serial
    self.takeover = takeover
    self.firmware = firmware
    self.handle = None
    permissionproblem = False
    deviceinuse = False
    for bus in usb.busses():
      if self.handle != None: break
      for dev in bus.devices:
        if self.handle != None: break
        if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
          try:
            handle = dev.open()
            _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
            if serial == "" or serial == _serial:
              try:
                if self.takeover:
                  handle.reset()
                  time.sleep(1)
                configuration = dev.configurations[0]
                interface = configuration.interfaces[0][0]
                handle.setConfiguration(configuration.value)
                handle.claimInterface(interface.interfaceNumber)
                handle.setAltInterface(interface.alternateSetting)
                self.handle = handle
                self.serial = _serial
              except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")

    descriptor = array("B", self.handle.controlMsg(0xc0, 0x22, 40, 0, 0, 100))
    if len(descriptor) != 40: raise Exception("Bad ZTEX descriptor length: %d" % len(descriptor))
    size, version, magic = struct.unpack("<2BI", descriptor[:6])
    product = struct.unpack("4B", descriptor[6:10])
    fwversion, ifversion, = struct.unpack("2B", descriptor[10:12])
    ifcaps = struct.unpack("6B", descriptor[12:18])
    moduledata = struct.unpack("12B", descriptor[18:30])
    sn = struct.unpack("10s", descriptor[30:])[0].decode("ascii")
    if size != 40: raise Exception("Bad ZTEX descriptor size: %d" % size)
    if version != 1: raise Exception("Bad ZTEX descriptor version: %d" % version)
    if magic != struct.unpack("<I", b"ZTEX")[0]: raise Exception("Bad ZTEX descriptor magic: %08X" % magic)
    if product[0] != 10: raise Exception("Firmware vendor is not ZTEX: %d.%d.%d.%d" % product)
    if product[2:] != (1, 1): raise Exception("Device is not running a bitcoin miner firmware: %02X %02X %02X %02X" % product)
    if ifversion != 1: raise Exception("Bad ZTEX interface version: %d" % ifversion)
    if not (ifcaps[0] & 2): raise Exception("Firmware doesn't support FPGA capability")
    self.hs_supported = ifcaps[0] & 32
    self.proxy.log("MCU firmware: %d.%d.%d.%d, version %d, serial number %s, high speed programming%s supported\n" % (product + (fwversion, sn, "" if self.hs_supported else " NOT")), 400, "B")
    
    descriptor = array("B", self.handle.controlMsg(0xc0, 0x82, 64, 0, 0, 100))
    if len(descriptor) != 64: raise Exception("Bad BTCMiner descriptor length: %d" % len(descriptor))
    version, numnonces, offset, basefreq, defaultmultiplier, maxmultiplier, hashesperclock = struct.unpack("<BBHHBBH", descriptor[:10])
    firmware = struct.unpack("54s", descriptor[10:])[0].split(b"\0", 1)[0].decode("ascii")
    if version != 4: raise Exception("Bad BTCMiner descriptor version: %d, firmware outdated?" % version)
    self.num_nonces = numnonces + 1
    self.nonce_offset = offset - 10000
    self.base_frequency = basefreq * 10000
    self.default_multiplier = min(defaultmultiplier, maxmultiplier)
    self.maximum_multiplier = maxmultiplier
    self.hashes_per_clock = hashesperclock / 128.
    self.firmware_name = firmware
    defaultspeed = self.base_frequency * self.default_multiplier * self.hashes_per_clock / 1000000
    maxspeed = self.base_frequency * self.maximum_multiplier * self.hashes_per_clock / 1000000
    self.proxy.log("FPGA firmware: %s, default speed: %f MH/s, maximum speed: %f MH/s\n" % (self.firmware_name, defaultspeed, maxspeed), 400, "B")
    
    unconfigured, checksum, bytestransferred, initb, result, bitswap = struct.unpack("<BBIBBB", array("B", self.handle.controlMsg(0xc0, 0x30, 9, 0, 0, 100)))
    if unconfigured:
      self.proxy.log("Programming FPGA with firmware %s...\n" % self.firmware_name, 300, "B")
      firmwarepath = "%s/%s.bit" % (self.firmware, self.firmware_name)
      try:
        fwfile = open(firmwarepath, "rb")
        bitstream = fwfile.read()
        fwfile.close()
      except Exception as e: raise Exception("Could not read firmware from %s: %s" % (firmwarepath, str(e)))
      sig1 = bitstream.find(b"\xaa\x99\x55\x66")
      sig2 = bitstream.find(b"\x55\x99\xaa\x66")
      if sig2 < 0 or (sig1 >= 0 and sig1 < sig2): raise Exception("Signature not found in bitstream, wrong bit order?")
      self.handle.controlMsg(0x40, 0x31, b"", 0, 0, 100)
      if self.hs_supported:
        ep, interface = struct.unpack("<BB", array("B", self.handle.controlMsg(0xc0, 0x33, 2, 0, 0, 100)))
        self.handle.controlMsg(0x40, 0x34, b"", 0, 0, 100)
        pos = 0
        while pos < len(bitstream): pos += self.handle.bulkWrite(ep, bitstream[pos : pos + 65536], 500)
        self.handle.controlMsg(0x40, 0x35, b"", 0, 0, 100)
      else:
        pos = 0
        while pos < len(bitstream): pos += self.handle.controlMsg(0x40, 0x32, bitstream[pos : pos + 2048], 0, 0, 500)
      unconfigured, checksum, bytestransferred, initb, result, bitswap = struct.unpack("<BBIBBB", array("B", self.handle.controlMsg(0xc0, 0x30, 9, 0, 0, 100)))
      if unconfigured: raise Exception("FPGA configuration failed: FPGA did not assert DONE")
      
  
  def set_multiplier(self, multiplier):
    with self.lock:
      self.handle.controlMsg(0x40, 0x83, b"", multiplier, 0, 100)
      
  
  def send_job(self, data):
    with self.lock:
      self.handle.controlMsg(0x40, 0x80, data, 0, 0, 100)
      
  
  def read_nonces(self):
    with self.lock:
      data = array("B", self.handle.controlMsg(0xc0, 0x81, 12 * self.num_nonces, 0, 0, 100))
    nonces = []
    for i in range(self.num_nonces):
      values = struct.unpack("<III", data[12 * i : 12 * (i + 1)])
      nonces.append((values[0] - self.nonce_offset, values[1] - self.nonce_offset, values[2]))
    return nonces
      