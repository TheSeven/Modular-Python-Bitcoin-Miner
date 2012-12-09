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
# ModMiner Quad worker low level driver #
#########################################



import time
import serial
import struct
from binascii import hexlify, unhexlify
from threading import RLock, Condition, Thread
try: from queue import Queue
except: from Queue import Queue



class DeviceException(Exception): pass



class Spartan6FPGA(object):

  
  def __init__(self, proxy, driver, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.speed = 0
    if idcode & 0xfffffff == 0x401d093: self.typename = "Xilinx Spartan 6 LX150 FPGA"
    elif idcode & 0xfffffff == 0x403d093: self.typename = "Xilinx Spartan 6 LX150T FPGA"
    else: self.typename = "Unknown Xilinx Spartan 6 FPGA (0x%08X)" % idcode
    self.name = "Device %d" % id
    
  
  def init(self):
    self._prepare_firmware()
    self.usercode = self.driver.get_usercode(self.id)
    if self.usercode != self.fwusercode: self._upload_firmware()
    self.usercode = self.driver.get_usercode(self.id)
    if self.usercode == 0xffffffff: raise DeviceException("USERCODE register not available!")
    self.firmware_rev = (self.usercode >> 8) & 0xff
    self.firmware_build = self.usercode & 0xf
    self.proxy.log("%s: Firmware version %d, build %d\n" % (self.name, self.firmware_rev, self.firmware_build), 500)
    self.usable = True
    self.driver.register(self)
    
    
  def _prepare_firmware(self):
    try:
      self.firmware = self.driver.firmware
      if self.firmware[-1] == "/": self.firmware += "%08x.bit" % (self.idcode & 0xfffffff)
      with open(self.firmware, "rb") as file:
        if struct.unpack(">H", file.read(2))[0] != 9: raise Exception("Bad firmware file format!")
        file.read(11)
        if file.read(1) != b"a": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdesignname = file.read(bytes).decode("latin1").rstrip('\0')
        self.fwusercode = int(self.fwdesignname.split(';')[-1].split('=')[-1], base = 16)
        if file.read(1) != b"b": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwpart = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"c": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwdate = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"d": raise Exception("Bad firmware file format!")
        bytes = struct.unpack(">H", file.read(2))[0]
        self.fwtime = file.read(bytes).decode("latin1").rstrip('\0')
        if file.read(1) != b"e": raise Exception("Bad firmware file format!")
        self.fwlength = struct.unpack(">I", file.read(4))[0]
        self.fwoffset = file.tell()
      self.proxy.log("%s: Firmware file %s information:\n" % (self.name, self.firmware), 500, "B")
      self.proxy.log("%s:   Design name: %s\n" % (self.name, self.fwdesignname), 500)
      self.proxy.log("%s:   Version: %d, build %d\n" % (self.name, (self.fwusercode >> 8) & 0xff, self.fwusercode & 0xff), 500)
      self.proxy.log("%s:   Build time: %s %s\n" % (self.name, self.fwdate, self.fwtime), 500)
      self.proxy.log("%s:   Part number: %s\n" % (self.name, self.fwpart), 500)
      self.proxy.log("%s:   Bitstream length: %d bytes\n" % (self.name, self.fwlength), 500)
      idcodemap = {"6slx150fgg484": 0x401d093, "6slx150tfgg676": 0x403d093}
      if not self.fwpart in idcodemap or idcodemap[self.fwpart] != self.idcode & 0xfffffff:
        raise Exception("Firmware is for wrong device type!")
      if self.fwusercode == 0xffffffff: raise Exception("Firmware does not support USERCODE!")
    except Exception as e: raise DeviceException(str(e))
    
  def _upload_firmware(self):
    with open(self.firmware, "rb") as file:
      file.seek(self.fwoffset)
      self.proxy.log("%s: Programming FPGA...\n" % self.name, 300, "B")
      starttime = time.time()
      with self.driver.lock:
        if struct.unpack("B", self.driver._txn(struct.pack("<BBI", 5, self.id, self.fwlength), 1))[0] != 1:
          raise DeviceException("Failed to start bitstream upload!")
        bytesleft = self.fwlength
        bytes = 0
        while bytesleft:
          chunksize = min(32, bytesleft)
          bytesleft -= chunksize
          chunk = file.read(chunksize)
          if struct.unpack("B", self.driver._txn(chunk, 1))[0] != 1:
            raise DeviceException("Error during bitstream upload!")
          bytes += chunksize
          if not bytes & 0x3ffff:
            percent = 100. * bytes / self.fwlength
            speed = bytes / (time.time() - starttime) / 1024.
            self.proxy.log("%s: Programming: %.1f%% done, %.1f kiB/s\n" % (self.name, percent, speed), 300, "B")
    if struct.unpack("B", self.driver._txn(b"", 1))[0] != 1: raise DeviceException("FPGA didn't accept bitstream!")
    
    
  def parse_nonce(self, data):
    value = struct.unpack("<I", data)[0]
    if value != 0xffffffff: return data

    
    
class UnknownDevice(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.typename = "Unknown Device (IDCODE 0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
    
  def init(self): pass

    
    
idcodemap = {
  0x401d093: {"handler": Spartan6FPGA},
  0x403d093: {"handler": Spartan6FPGA},
}



class MMQDevice(object):
  

  def __init__(self, proxy, port, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.port = port
    self.firmware = firmware
    self.handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
    self.handle.write(b"\0" + b"\xff" * 45)
    self.handle.write(b"\0")
    result = self.handle.read(64)
    if result[-1:] != b"\0": raise Exception("Failed to sync interface: %s" % (hexlify(result).decode("ascii") if result else str(result)))
    self.handle.write(b"\x01")
    data = b""
    while True:
      byte = self.handle.read(1)
      if byte == b"\0": break
      data += byte
    proxy.log("Device model: %s\n" % data.decode("utf_8"), 400)
    devicecount = struct.unpack("B", self._txn(struct.pack("B", 2), 1))[0]
    proxy.log("Number of chips: %s\n" % devicecount, 450)
    self.devices = []
    devices = []
    for i in range(devicecount):
      try:
        idcode = struct.unpack("<I", self._txn(struct.pack("BB", 3, i), 4))[0]
        if not idcode & 0xfffffff in idcodemap or not "handler" in idcodemap[idcode & 0xfffffff]:
          idcodemap[idcode & 0xfffffff] = {"handler": UnknownDevice}
        device = idcodemap[idcode & 0xfffffff]["handler"](self.proxy, self, i, idcode)
        devices.append(device)
        self.proxy.log("%s: %s\n" % (device.name, device.typename), 500)
      except Exception as e: self.proxy.log("%s\n" % str(e), 150, "rB")
    for device in devices:
      try: device.init()
      except DeviceException as e: self.proxy.log("%s: %s\n" % (device.name, str(e)), 200, "r")
    
    
  def register(self, device):
    device.index = len(self.devices)
    self.devices.append(device)
    
    
  def close(self):
    self.shutdown = True
    try: self.listenerthread.join(2)
    except: pass
    
    
  def _txn(self, data, expectlen):
    with self.lock:
      self.handle.write(data)
      result = self.handle.read(expectlen)
    if len(result) != expectlen: raise Exception("Short read: Expected %d bytes, got %d (%s)!" % (expectlen, len(result), hexlify(result).decode("ascii")))
    return result
    
    
  def get_usercode(self, id):
    return struct.unpack("<I", self._txn(struct.pack("BB", 4, id), 4))[0]
    
    
  def get_fpga_count(self):
    return len(self.devices)

  
  def send_job(self, fpga, job):
    result = struct.unpack("B", self._txn(struct.pack("BB", 8, self.devices[fpga].id) + job, 1))[0]
    if result != 1: raise Exception("%s: Device didn't accept job: 0x%02x" % (self.devices[fpga].name, result))

  
  def write_reg(self, fpga, reg, value):
    result = struct.unpack("B", self._txn(struct.pack("<BBBI", 11, self.devices[fpga].id, reg, value), 1))[0]
    if result != 1: raise Exception("%s: Writing register %d failed: 0x%02x" % (self.devices[fpga].name, reg, result))

  
  def read_reg(self, fpga, reg):
    return struct.unpack("<I", self._txn(struct.pack("BBB", 12, self.devices[fpga].id, reg), 4))[0]

  
  def set_speed(self, fpga, speed):
    result = struct.unpack("B", self._txn(struct.pack("<BBI", 6, self.devices[fpga].id, speed), 1))[0]
    if result != 1: raise Exception("%s: Device didn't accept clock speed %d!" % (self.devices[fpga].name, speed))

  
  def get_speed(self, fpga):
    return struct.unpack("<I", self._txn(struct.pack("BB", 7, self.devices[fpga].id), 4))[0]

  
  def read_nonces(self):
    nonces = {}
    with self.lock:
      for device in self.devices:
        if not device.usable: continue
        nonce = device.parse_nonce(self._txn(struct.pack("BB", 9, device.id), 4))
        if nonce is not None: nonces[device.index] = nonce
    return nonces
    
    
  def read_temperatures(self):
    temps = {}
    with self.lock:
      for device in self.devices:
        temps[device.index] = struct.unpack("<h", self._txn(struct.pack("BB", 13, device.id), 2))[0] / 128.
    return temps
