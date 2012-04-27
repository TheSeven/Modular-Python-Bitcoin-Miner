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



########################################################
# Generic FTDI JTAG bitbanging worker low level driver #
########################################################



import time
import usb
import struct
from binascii import unhexlify
from threading import RLock



jtagscript_mmq = {}
jtagscript_mmq["Bus 0"] = {}
jtagscript_mmq["Bus 0"]["s6_user1"] = unhexlify(b"000401050004000400040004")
jtagscript_mmq["Bus 0"]["leave_shift"] = unhexlify(b"080c")
jtagscript_mmq["Bus 0"]["tdi"] = unhexlify(b"01")
jtagscript_mmq["Bus 0"]["tms"] = unhexlify(b"08")
jtagscript_mmq["Bus 0"]["tdo"] = unhexlify(b"02")
jtagscript_mmq["Bus 0"]["shift_dr"] = unhexlify(b"080c00040004")
jtagscript_mmq["Bus 0"]["highclock"] = unhexlify(b"0105")
jtagscript_mmq["Bus 0"]["clock"] = unhexlify(b"0004")
jtagscript_mmq["Bus 0"]["tap_reset"] = unhexlify(b"080c080c080c080c080c0004")
jtagscript_mmq["Bus 0"]["s6_cfg_in"] = unhexlify(b"010500040105000400040004")
jtagscript_mmq["Bus 0"]["shift_ir"] = unhexlify(b"080c080c00040004")
jtagscript_mmq["Bus 0"]["s6_jprogram"] = unhexlify(b"010501050004010500040004")
jtagscript_mmq["Bus 0"]["tck"] = unhexlify(b"04")
jtagscript_mmq["Bus 0"]["s6_jstart"] = unhexlify(b"000400040105010500040004")
jtagscript_mmq["Bus 0"]["fm_getnonce"] = unhexlify(b"000401050105010500040004")
jtagscript_mmq["Bus 0"]["s6_usercode"] = unhexlify(b"000400040004010500040004")
jtagscript_mmq["Bus 0"]["s6_jshutdown"] = unhexlify(b"010500040105010500040004")
jtagscript_x6500 = {}
jtagscript_x6500["Bus 1"] = {}
jtagscript_x6500["Bus 1"]["s6_user1"] = unhexlify(b"c0c8c2cac0c8c0c8c0c8c0c8")
jtagscript_x6500["Bus 1"]["leave_shift"] = unhexlify(b"c4cc")
jtagscript_x6500["Bus 1"]["tdi"] = unhexlify(b"c2")
jtagscript_x6500["Bus 1"]["tms"] = unhexlify(b"c4")
jtagscript_x6500["Bus 1"]["tdo"] = unhexlify(b"01")
jtagscript_x6500["Bus 1"]["shift_dr"] = unhexlify(b"c4ccc0c8c0c8")
jtagscript_x6500["Bus 1"]["highclock"] = unhexlify(b"c2ca")
jtagscript_x6500["Bus 1"]["clock"] = unhexlify(b"c0c8")
jtagscript_x6500["Bus 1"]["tap_reset"] = unhexlify(b"c4ccc4ccc4ccc4ccc4ccc0c8")
jtagscript_x6500["Bus 1"]["s6_cfg_in"] = unhexlify(b"c2cac0c8c2cac0c8c0c8c0c8")
jtagscript_x6500["Bus 1"]["shift_ir"] = unhexlify(b"c4ccc4ccc0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_jprogram"] = unhexlify(b"c2cac2cac0c8c2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["tck"] = unhexlify(b"c8")
jtagscript_x6500["Bus 1"]["s6_jstart"] = unhexlify(b"c0c8c0c8c2cac2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["fm_getnonce"] = unhexlify(b"c0c8c2cac2cac2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_usercode"] = unhexlify(b"c0c8c0c8c0c8c2cac0c8c0c8")
jtagscript_x6500["Bus 1"]["s6_jshutdown"] = unhexlify(b"c2cac0c8c2cac2cac0c8c0c8")
jtagscript_x6500["Bus 0"] = {}
jtagscript_x6500["Bus 0"]["s6_user1"] = unhexlify(b"0c8c2cac0c8c0c8c0c8c0c8c")
jtagscript_x6500["Bus 0"]["leave_shift"] = unhexlify(b"4ccc")
jtagscript_x6500["Bus 0"]["tdi"] = unhexlify(b"2c")
jtagscript_x6500["Bus 0"]["tms"] = unhexlify(b"4c")
jtagscript_x6500["Bus 0"]["tdo"] = unhexlify(b"10")
jtagscript_x6500["Bus 0"]["shift_dr"] = unhexlify(b"4ccc0c8c0c8c")
jtagscript_x6500["Bus 0"]["highclock"] = unhexlify(b"2cac")
jtagscript_x6500["Bus 0"]["clock"] = unhexlify(b"0c8c")
jtagscript_x6500["Bus 0"]["tap_reset"] = unhexlify(b"4ccc4ccc4ccc4ccc4ccc0c8c")
jtagscript_x6500["Bus 0"]["s6_cfg_in"] = unhexlify(b"2cac0c8c2cac0c8c0c8c0c8c")
jtagscript_x6500["Bus 0"]["shift_ir"] = unhexlify(b"4ccc4ccc0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_jprogram"] = unhexlify(b"2cac2cac0c8c2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["tck"] = unhexlify(b"8c")
jtagscript_x6500["Bus 0"]["s6_jstart"] = unhexlify(b"0c8c0c8c2cac2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["fm_getnonce"] = unhexlify(b"0c8c2cac2cac2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_usercode"] = unhexlify(b"0c8c0c8c0c8c2cac0c8c0c8c")
jtagscript_x6500["Bus 0"]["s6_jshutdown"] = unhexlify(b"2cac0c8c2cac2cac0c8c0c8c")


def byte2int(byte):
  if type(byte) is int: return byte
  return struct.unpack("B", byte)[0]


def int2byte(value):
  return struct.pack("B", value)


def orbytes(byte1, byte2):
  return int2byte(byte2int(byte1) | byte2int(byte2))
  
  
def int2bits(bits, value):
  result = []
  for bit in range(bits):
    result.append(value & 1)
    value = value >> 1
  return result


def bits2int(data):
  result = 0
  for bit in range(len(data)): result |= data[bit] << bit
  return result

  
def jtagcomm_checksum(bits):
  checksum = 1
  for bit in bits: checksum ^= bit
  return [checksum]
  
  
  
class DeviceException(Exception): pass
    
  

class Spartan6FPGA(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.irlength = idcodemap[idcode & 0xfffffff]["irlength"]
    if idcode & 0xfffffff == 0x401d093: self.typename = "Xilinx Spartan 6 LX150 FPGA"
    elif idcode & 0xfffffff == 0x403d093: self.typename = "Xilinx Spartan 6 LX150T FPGA"
    else: self.typename = "Unknown Xilinx Spartan 6 FPGA (0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
  
  def init(self):
    self._prepare_firmware()
    script = self.driver.jtagscript[self.bus]
    self.driver.set_ir(self, script["s6_usercode"])
    self.usercode = bits2int(self.driver.get_dr(self, 32))
    if self.usercode != self.fwusercode: self._upload_firmware()
    self.driver.set_ir(self, script["s6_usercode"])
    self.usercode = bits2int(self.driver.get_dr(self, 32))
    if self.usercode == 0xffffffff: raise DeviceException("USERCODE register not available!")
    self.firmware_rev = (self.usercode >> 8) & 0xff
    self.firmware_build = self.usercode & 0xf
    self.proxy.log("%s: Firmware version %d, build %d\n" % (self.name, self.firmware_rev, self.firmware_build), 500)
    clock = script["clock"]
    hc = script["highclock"]
    self.selectscript = script["shift_ir"] \
                      + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_user1"] + hc * self.irtail) \
                      + script["ir_to_dr"]
    self.unselectscript = script["leave_shift"]
    self.reselectscript = script["shift_dr"]
    self.writescript = script["clock"] * self.drtail
    self.readscript = script["clock"] * self.drhead
    self.readnonce_ir = script["s6_user1"]
    self.readnonce_push_dr = clock * 32 + script["fm_getnonce"]
    self.readnonce_pull_len = 38
    self.usable = True
    self.driver.register(self)
    
    
  def _format_reg_write_dr(self, addr, data):
    bits = int2bits(32, data) + int2bits(4, addr) + [1]
    bits += jtagcomm_checksum(bits)
    return self.driver.format_dr(self.bus, bits)
    
    
  def _write_reg(self, reg, data):
    data = self.selectscript \
         + self.driver._tmstail(self.bus, self._format_reg_write_dr(reg, data) + self.writescript) \
         + self.unselectscript
    with self.driver.lock: self.driver._write(data)
  
  
  def _format_reg_read_dr(self, addr):
    bits = int2bits(4, addr) + [0]
    bits += jtagcomm_checksum(bits)
    return self.driver.format_dr(self.bus, bits)
    
    
  def _read_reg(self, reg):
    script = self.driver.jtagscript[self.bus]
    data1 = self.selectscript \
          + self.driver._tmstail(self.bus, self._format_reg_read_dr(reg) + self.writescript) \
          + self.unselectscript \
          + self.reselectscript \
          + self.readscript
    data2 = self.driver._tmstail(self.bus, script["clock"] * 32)
    data3 = script["leave_shift"]
    with self.driver.lock:
      self.driver._write(data1)
      data = self.driver._shift(self.bus, data2)
      self.driver._write(data3)
    return bits2int(data)
    
    
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
      script = self.driver.jtagscript[self.bus]
      clock = script["clock"]
      hc = script["highclock"]
      self.proxy.log("%s: Programming FPGA...\n" % self.name, 300, "B")
      starttime = time.time()
      with self.driver.lock:
        data = script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_jprogram"] + hc * self.irtail) \
             + script["leave_shift"] \
             + script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_cfg_in"] + hc * self.irtail) \
             + script["ir_to_dr"]
        self.driver._write(data)
        bytesleft = self.fwlength
        bytes = 0
        while bytesleft:
          chunksize = min(4096, bytesleft)
          bytes += chunksize
          bytesleft -= chunksize
          chunk = file.read(chunksize)
          data = b""
          for byte in chunk:
            if type(byte) is not int: byte = struct.unpack("B", byte)[0]
            data += (hc if byte & 0x80 else clock) \
                  + (hc if byte & 0x40 else clock) \
                  + (hc if byte & 0x20 else clock) \
                  + (hc if byte & 0x10 else clock) \
                  + (hc if byte & 0x08 else clock) \
                  + (hc if byte & 0x04 else clock) \
                  + (hc if byte & 0x02 else clock) \
                  + (hc if byte & 0x01 else clock)
          if not bytesleft: data = self.driver._tmstail(self.bus, data + clock * self.drtail)
          self.driver._write(data)
          if not bytes & 0x3ffff:
            percent = 100. * bytes / self.fwlength
            speed = bytes / (time.time() - starttime) / 1024.
            self.proxy.log("%s: Programming: %.1f%% done, %.1f kiB/s\n" % (self.name, percent, speed), 300, "B")
        data = script["leave_shift"] \
             + script["shift_ir"] \
             + self.driver._tmstail(self.bus, hc * self.irhead + script["s6_jstart"] + hc * self.irtail) \
             + script["leave_shift"] \
             + clock * 16
        self.driver._write(data)
        status = self.driver.get_ir(self)
        if not status[-1]: raise DeviceException("FPGA did not accept bitstream!")
    
    
  def get_speed(self):
    return self._read_reg(0xd)
    
    
  def set_speed(self, speed):
    self._write_reg(0xd, speed)
    
    
  def send_job(self, job):
    job = struct.unpack("<11I", job)
    data = b""
    for i in range(11):
      data += (self.reselectscript if i else self.selectscript) \
            + self.driver._tmstail(self.bus, self._format_reg_write_dr(1 + i, job[i]) + self.writescript) \
            + self.unselectscript
    with self.driver.lock: self.driver._write(data)
    
    
  def parse_nonce(self, data):
    data = bits2int(data[:32])
    if data != 0xffffffff: return struct.pack("<I", data)

    
    
class UnknownJTAGDevice(object):

  
  def __init__(self, proxy, driver, bus, id, idcode):
    self.proxy = proxy
    self.driver = driver
    self.bus = bus
    self.id = id
    self.idcode = idcode
    self.usable = False
    self.irlength = idcodemap[idcode & 0xfffffff]["irlength"]
    self.typename = "Unknown JTAG Device (0x%08X)" % idcode
    self.name = "%s Device %d" % (bus, id)
    
    
  def init(self): pass

    
    
idcodemap = {
  0x401d093: {"irlength": 6, "handler": Spartan6FPGA},
  0x403d093: {"irlength": 6, "handler": Spartan6FPGA},
}



class FTDIJTAGDevice(object):
  

  def __init__(self, proxy, deviceid, takeover, firmware):
    self.lock = RLock()
    self.proxy = proxy
    self.serial = deviceid
    self.takeover = takeover
    self.firmware = firmware
    self.handle = None
    permissionproblem = False
    deviceinuse = False
    for bus in usb.busses():
      if self.handle != None: break
      for dev in bus.devices:
        if self.handle != None: break
        if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
          try:
            handle = dev.open()
            manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
            product = handle.getString(dev.iProduct, 100).decode("latin1")
            serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
            boardtype = None
            if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
              boardtype = "X6500"
            elif manufacturer == "BTCFPGA" and product == "ModMiner":
              boardtype = "ModMiner"
            if boardtype and (deviceid == "" or deviceid == serial):
              try:
                if takeover:
                  handle.reset()
                  time.sleep(1)
                configuration = dev.configurations[0]
                interface = configuration.interfaces[0][0]
                handle.setConfiguration(configuration.value)
                handle.claimInterface(interface.interfaceNumber)
                handle.setAltInterface(interface.alternateSetting)
                self.inep = interface.endpoints[0].address
                self.inepsize = interface.endpoints[0].maxPacketSize
                self.outep = interface.endpoints[1].address
                self.outepsize = interface.endpoints[1].maxPacketSize
                self.index = 1
                self.handle = handle
                self.serial = serial
                self.boardtype = boardtype
              except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")
    self.outmask = 0
    if self.boardtype == "X6500": self.jtagscript = jtagscript_x6500
    elif self.boardtype == "ModMiner": self.jtagscript = jtagscript_mmq
    else: raise Exception("Unknown board: %s" % self.boardtype)
    for bus in self.jtagscript:
      script = self.jtagscript[bus]
      script["clocklen"] = len(script["clock"])
      script["tckmask"] = byte2int(script["tck"])
      script["tmsmask"] = byte2int(script["tms"])
      script["tdimask"] = byte2int(script["tdi"])
      script["tdomask"] = byte2int(script["tdo"])
      script["ir_to_dr"] = script["leave_shift"] + script["shift_dr"]
      self.outmask |= script["tckmask"] | script["tmsmask"] | script["tdimask"]
    self.handle.controlMsg(0x40, 3, None, 0, 0, 1000)
    self._switch_async()
    self.busdevices = {}
    self.devices = []
    for bus in sorted(self.jtagscript.keys()): self._init_bus(bus)
    
    
  def _init_bus(self, bus):
    max_devices = 100
    max_ir_len = 16
    script = self.jtagscript[bus]
    clock = script["clock"]
    hc = script["highclock"]
    data = script["tap_reset"] \
         + script["shift_ir"] \
         + self._tmstail(bus, script["highclock"] * max_ir_len * max_devices) \
         + script["ir_to_dr"] \
         + clock * max_devices
    self._write(data)
    data = self._shift(bus, self._tmstail(bus, hc * max_devices))
    devicecount = 0
    for bit in data:
      if not bit: devicecount += 1
      else: break
    if devicecount == max_devices: raise Exception("%s: JTAG chain contains more than 99 devices!" % bus)
    for i in range(devicecount, max_devices):
      if not data[i]: raise Exception("%s: Failed to detect JTAG chain device count!" % bus)
    self.proxy.log("%s: Detected %d devices\n" % (bus, devicecount), 500)
    devices = []
    if devicecount:
      self._write(script["tap_reset"] + script["shift_dr"])
      data = self._shift(bus, self._tmstail(bus, clock * devicecount * 32))
      self._write(script["leave_shift"])
      totalirlength = 0
      for i in range(devicecount):
        if not data[0]: raise Exception("%s: Device %d does not support IDCODE!" % (bus, i))
        idcode = bits2int(data[:32])
        data = data[32:]
        if not idcode & 0xfffffff in idcodemap:
          raise Exception("%s Device %d: Unknown IDCODE 0x%08X!" % (bus, i, idcode))
        if not "handler" in idcodemap[idcode & 0xfffffff]:
          idcodemap[idcode & 0xfffffff]["handler"] = UnknownJTAGDevice
        device = idcodemap[idcode & 0xfffffff]["handler"](self.proxy, self, bus, i, idcode)
        self.proxy.log("%s: %s\n" % (device.name, device.typename), 500)
        totalirlength += device.irlength
        devices.append(device)
    self.busdevices[bus] = devices
    irpos = 0
    for device in devices:
      device.irhead = irpos
      device.irtail = totalirlength - irpos - device.irlength
      device.drhead = device.id
      device.drtail = devicecount - device.id - 1
      irpos += device.irlength
      try: device.init()
      except DeviceException as e: self.proxy.log("%s: %s\n" % (device.name, str(e)), 200, "r")
    readnonce_ir = b""
    readnonce_push_dr = b""
    readnonce_pull_len = 0
    for device in devices:
      if device.usable:
        readnonce_ir += device.readnonce_ir
        readnonce_push_dr += device.readnonce_push_dr
        readnonce_pull_len += device.readnonce_pull_len
      else:
        readnonce_ir += hc * device.irlength
        readnonce_push_dr += clock
        readnonce_pull_len += 1
    script["readnonce_head"] = script["shift_ir"] \
                             + self._tmstail(bus, readnonce_ir) \
                             + script["ir_to_dr"] \
                             + self._tmstail(bus, readnonce_push_dr) \
                             + script["leave_shift"] \
                             + script["shift_dr"]
    script["readnonce_pull"] = self._tmstail(bus, clock * readnonce_pull_len)
    script["readnonce_tail"] = script["leave_shift"]
    
    
  def register(self, device):
    device.index = len(self.devices)
    self.devices.append(device)
      

  def set_ir(self, device, ir):
    script = self.jtagscript[device.bus]
    hc = script["highclock"]
    self._write(script["shift_ir"] + self._tmstail(device.bus, hc * device.irhead + ir + hc * device.irtail) + script["leave_shift"])
    
    
  def get_ir(self, device):
    script = self.jtagscript[device.bus]
    hc = script["highclock"]
    self._write(script["shift_ir"] + hc * device.irhead)
    data = self._shift(device.bus, hc * device.irlength)
    self._write(self._tmstail(device.bus, hc * max(1, device.irtail)) + script["leave_shift"])
    return data
    
    
  def set_dr(self, device, dr):
    script = self.jtagscript[device.bus]
    clock = script["clock"]
    self._write(script["shift_dr"] + self._tmstail(device.bus, dr + script["clock"] * device.drtail) + script["leave_shift"])
    
    
  def get_dr(self, device, length):
    script = self.jtagscript[device.bus]
    self._write(script["shift_dr"] + script["clock"] * device.drhead)
    data = self._shift(device.bus, self._tmstail(device.bus, script["clock"] * length))
    self._write(script["leave_shift"])
    return data
    
    
  def format_dr(self, bus, bits):
    script = self.jtagscript[bus]
    clock = script["clock"]
    hc = script["highclock"]
    result = b""
    for bit in bits: result += hc if bit else clock
    return result
    
    
  def _tmstail(self, bus, data):
    script = self.jtagscript[bus]
    clocklen = script["clocklen"]
    tmsmask = script["tmsmask"]
    result = data[:-clocklen]
    for byte in data[-clocklen:]: result += int2byte(byte2int(byte) | tmsmask)
    return result
    
    
  def _purge_buffers(self):
    self.handle.controlMsg(0x40, 0, None, 1, self.index, 1000)
    self.handle.controlMsg(0x40, 0, None, 2, self.index, 1000)
    
    
  def _set_bit_mode(self, mask, mode):
    self.handle.controlMsg(0x40, 0xb, None, (mode << 8) | mask, self.index, 1000)
  
  
  def _get_bit_mode(self):
    return struct.unpack("B", bytes(bytearray(self.handle.controlMsg(0xc0, 0xc, 1, 0, self.index, 1000))))[0]
    
  
  def _switch_async(self):
    self._set_bit_mode(self.outmask, 0)
    self._set_bit_mode(self.outmask, 1)
    
    
  def _switch_sync(self):
    self._set_bit_mode(self.outmask, 0)
    self._set_bit_mode(self.outmask, 4)
    
    
  def _write(self, data):
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.bulkWrite(self.outep, data[offset : offset + write_size], 1000)
      offset = offset + ret
    
    
  def _read(self, size, timeout = 1):
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = bytes(bytearray(self.handle.bulkRead(self.inep, min(64, size - offset + 2), 1000)))
      data += ret[2:]
      offset += len(ret) - 2
    return data
    
    
  def _bidi(self, data, timeout = 1):
    recv = b""
    offset = 0
    self._switch_sync()
    self._purge_buffers()
    while offset < len(data):
      bytes = min(124, len(data) - offset)
      self._write(data[offset : offset + bytes])
      recv += self._read(bytes, timeout)
      offset += bytes
    self._switch_async()
    return recv
    
    
  def _shift(self, bus, data, timeout = 1):
    script = self.jtagscript[bus]
    tdomask = script["tdomask"]
    clocklen = script["clocklen"]
    data = self._bidi(data + data[-1:], timeout)
    result = []
    for i in range(clocklen, len(data), clocklen):
      result.append(1 if byte2int(data[i]) & tdomask else 0)
    return result
    
    
  def _set_cbus_bits(self, outmask, data):
    self._set_bit_mode((outmask << 4) | data, 0x20)

    
  def _get_cbus_bits(self):
    return self._get_bit_mode()
    
    
  def get_fpga_count(self):
    return len(self.devices)

  
  def send_job(self, fpga, job):
    self.devices[fpga].send_job(job)

  
  def set_speed(self, fpga, speed):
    self.devices[fpga].set_speed(speed)

  
  def get_speed(self, fpga):
    return self.devices[fpga].get_speed()

  
  def read_nonces(self):
    nonces = {}
    for bus in self.jtagscript:
      script = self.jtagscript[bus]
      with self.lock:
        self._write(script["readnonce_head"])
        data = self._shift(bus, script["readnonce_pull"])
        self._write(script["readnonce_tail"])
      for device in self.busdevices[bus]:
        if not device.usable:
          data = data[1:]
          continue
        slice = data[:device.readnonce_pull_len]
        data = data[device.readnonce_pull_len:]
        nonce = device.parse_nonce(slice)
        if nonce is not None: nonces[device.index] = nonce
    return nonces
    
    
  def read_temperatures(self):
    temps = {}
    
    if self.boardtype == "X6500":
      with self.lock:
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x0)
        data0 = 0
        data1 = 0
        for i in range(16):
          self._set_cbus_bits(0xc, 0x8)
          data = self._get_cbus_bits()
          data0 = (data0 << 1) | (data & 1)
          data1 = (data1 << 1) | ((data >> 1) & 1)
          self._set_cbus_bits(0xc, 0x0)
        self._set_cbus_bits(0xc, 0x4)
        self._set_cbus_bits(0xc, 0xc)
        self._set_cbus_bits(0xc, 0x4)
        self._switch_async()
      if data0 != 0xffff and data0 != 0:
        if ((data0 >> 15) & 1) == 1: data0 -= (1 << 16)
        temps[0] = (data0 >> 2) * 0.03125
      if data1 != 0xffff and data1 != 0:
        if ((data1 >> 15) & 1) == 1: data1 -= (1 << 16)
        temps[1] = (data1 >> 2) * 0.03125
          
    return temps