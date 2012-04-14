# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
# Copyright (C) 2012 by TheSeven
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import time
import struct
import threading
from .jtag import JTAG

class DeviceNotOpened(Exception): pass
class NoAvailableDevices(Exception): pass
class InvalidChain(Exception): pass
class WriteError(Exception): pass


class FT232R_PortList:
  """Information about which of the 8 GPIO pins to use."""
  def __init__(self, tck0, tms0, tdi0, tdo0, tck1, tms1, tdi1, tdo1):
    self.tck0 = tck0
    self.tms0 = tms0
    self.tdi0 = tdi0
    self.tdo0 = tdo0
    self.tck1 = tck1
    self.tms1 = tms1
    self.tdi1 = tdi1
    self.tdo1 = tdo1
  
  def output_mask(self):
    return (1 << self.tck0) | (1 << self.tms0) | (1 << self.tdi0) | \
           (1 << self.tck1) | (1 << self.tms1) | (1 << self.tdi1)

  def format(self, tck, tms, tdi, chain=2):
    """Format the pin states as a single byte for sending to the FT232R
    Chain is the JTAG chain: 0 or 1, or 2 for both
    """
    if chain == 0:
      return struct.pack('B', ((tck & 1) << self.tck0) | ((tms & 1) << self.tms0) | ((tdi & 1) << self.tdi0))
    if chain == 1:
      return struct.pack('B', ((tck & 1) << self.tck1) | ((tms & 1) << self.tms1) | ((tdi & 1) << self.tdi1))
    if chain == 2:
      return struct.pack('B', ((tck & 1) << self.tck0) | ((tms & 1) << self.tms0) | ((tdi & 1) << self.tdi0) |
                              ((tck & 1) << self.tck1) | ((tms & 1) << self.tms1) | ((tdi & 1) << self.tdi1))
    else:
      raise InvalidChain()
  
  def chain_portlist(self, chain=0):
    """Returns a JTAG_PortList object for the specified chain"""
    if chain == 0:
      return JTAG_PortList(self.tck0, self.tms0, self.tdi0, self.tdo0)
    elif chain == 1:
      return JTAG_PortList(self.tck1, self.tms1, self.tdi1, self.tdo1)
    elif chain == 2:
      return self
    else:
      raise InvalidChain()


class JTAG_PortList:
  """A smaller version of the FT232R_PortList class, specific to the JTAG chain"""
  def __init__(self, tck, tms, tdi, tdo):
    self.tck = tck
    self.tms = tms
    self.tdi = tdi
    self.tdo = tdo
  
  def format(self, tck, tms, tdi):
    return struct.pack('B', ((tck & 1) << self.tck) | ((tms & 1) << self.tms) | ((tdi & 1) << self.tdi))


class FT232R:
  def __init__(self, handle):
    self.mutex = threading.RLock()
    self.handle = handle
    self.serial = handle.serial
    self.synchronous = None
    self.write_buffer = b""
    self.portlist = FT232R_PortList(7, 6, 5, 4, 3, 2, 1, 0)
    self.setSyncMode()
    self.handle.purgeBuffers()
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    with self.mutex:
      self.handle.close()
  
  def setSyncMode(self):
    """Put the FT232R into Synchronous mode."""
    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 4)
    self.synchronous = True

  def setAsyncMode(self):
    """Put the FT232R into Asynchronous mode."""
    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 1)
    self.synchronous = False
  
  def purgeBuffers(self):
    self.handle.purgeBuffers()

  def _setCBUSBits(self, sc, cs):
    # CBUS pins:
    #  SIO_0 = CBUS0 = input
    #  SIO_1 = CBUS1 = input
    #  CS    = CBUS2 = output
    #  SC    = CBUS3 = output
    
    SIO_0 = 0
    SIO_1 = 1
    CS    = 2
    SC    = 3
    read_mask = ( (1 << SC) | (1 << CS) | (0 << SIO_1) | (0 << SIO_0) ) << 4
    CBUS_mode = 0x20
    
    # set up I/O and start conversion:
    pin_state = (sc << SC) | (cs << CS)
    self.handle.setBitMode(read_mask | pin_state, CBUS_mode)

  def _getCBUSBits(self):
    SIO_0 = 0
    SIO_1 = 1
    data = self.handle.getBitMode()
    return (((data >> SIO_0) & 1), ((data >> SIO_1) & 1)) 
    
  def write(self, data):
    with self.mutex:
      self.handle.write(data)
    
  def read(self, size, timeout):
    with self.mutex:
      return self.handle.write(size, timeout)
    
  def flush(self):
    with self.mutex:
      """Write all data in the write buffer and purge the FT232R buffers"""
      self.setAsyncMode()
      self.handle.write(self.write_buffer)
      self.write_buffer = b""
      self.setSyncMode()
      self.handle.purgeBuffers()
  
  def read_data(self, num):
    with self.mutex:
      """Read num bytes from the FT232R and return an array of data."""
      
      if num == 0:
        self.flush()
        return b""

      # Repeat the last byte so we can read the last bit of TDO.
      write_buffer = self.write_buffer[-(num*3):]
      self.write_buffer = self.write_buffer[:-(num*3)]

      # Write all data that we don't care about.
      if len(self.write_buffer) > 0:
        self.flush()
        self.handle.purgeBuffers()

      data = b""

      while len(write_buffer) > 0:
        bytes_to_write = min(len(write_buffer), 3072)
        
        self.write(write_buffer[:bytes_to_write])
        write_buffer = write_buffer[bytes_to_write:]
        
        data = data + self.handle.read(bytes_to_write, 3)
        
      return data

  def read_temps(self):
    with self.mutex:
      
      # clock SC with CS high:
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      
      # drop CS to start conversion:
      self._setCBUSBits(0, 0)
      
      code0 = 0
      code1 = 0
      
      for i in range(16):
        self._setCBUSBits(1, 0)
        (sio_0, sio_1) = self._getCBUSBits()
        code0 |= sio_0 << (15 - i)
        code1 |= sio_1 << (15 - i)
        self._setCBUSBits(0, 0)
      
      # assert CS and clock SC:
      self._setCBUSBits(0, 1)
      self._setCBUSBits(1, 1)
      self._setCBUSBits(0, 1)
      
      if code0 == 0xFFFF or code0 == 0: temp0 = None
      else:
        if (code0 >> 15) & 1 == 1: code0 -= (1 << 16)
        temp0 = (code0 >> 2) * 0.03125
      if code1 == 0xFFFF or code1 == 0: temp1 = None
      else:
        if (code1 >> 15) & 1 == 1: code1 -= (1 << 16)
        temp1 = (code1 >> 2) * 0.03125
      
      return (temp0, temp1)
      
      
class FT232R_D2XX:
  def __init__(self, deviceid):
    import d2xx
    self.handle = None
    self.serial = deviceid
    devices = d2xx.listDevices()
    for devicenum, serial in enumerate(devices):
      if deviceid != "" and deviceid != serial: continue
      try:
        self.handle = d2xx.open(devicenum)
        self.serial = serial
        break
      except: pass
    if self.handle == None: raise Exception("Can not open the specified device")
    self.handle.setBaudRate(3000000)
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    if self.handle is None:
      return
    try:
      self.handle.close()
    finally:
      self.handle = None
  
  def purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.purge(0)
  
  def setBitMode(self, mask, mode):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.setBitMode(mask, mode)

  def getBitMode(self):
    if self.handle is None:
      raise DeviceNotOpened()
    return self.handle.getBitMode()
    
  def write(self, data):
    if self.handle is None:
      raise DeviceNotOpened()
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.write(data[offset : offset + write_size])
      offset = offset + ret
    
  def read(self, size, timeout):
    if self.handle is None:
      raise DeviceNotOpened()
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = self.handle.read(min(4096, size - offset))
      data = data + ret
      offset = offset + len(ret)
    return data
    
      
class FT232R_PyUSB:
  def __init__(self, deviceid, takeover):
    import usb
    self.handle = None
    self.serial = deviceid
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
            if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
              if deviceid == "" or deviceid == serial:
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
                except: deviceinuse = True
          except: permissionproblem = True
    if self.handle == None:
      if deviceinuse:
        raise Exception("Can not open the specified device, possibly because it is already in use")
      if permissionproblem:
        raise Exception("Can not open the specified device, possibly due to insufficient permissions")
      raise Exception("Can not open the specified device")
    self.handle.controlMsg(0x40, 3, None, 0, 0, 1000)
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def close(self):
    if self.handle is None:
      return
    try:
      self.handle.releaseInterface()
      self.handle.setConfiguration(0)
      self.handle.reset()
    finally:
      self.handle = None
  
  def purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.controlMsg(0x40, 0, None, 1, self.index, 1000)
    self.handle.controlMsg(0x40, 0, None, 2, self.index, 1000)
    
  def setBitMode(self, mask, mode):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.controlMsg(0x40, 0xb, None, (mode << 8) | mask, self.index, 1000)
  
  def getBitMode(self):
    if self.handle is None:
      raise DeviceNotOpened()
    return struct.unpack("B", bytes(bytearray(self.handle.controlMsg(0xc0, 0xc, 1, 0, self.index, 1000))))[0]
    
  def write(self, data):
    if self.handle is None:
      raise DeviceNotOpened()
    size = len(data)
    offset = 0
    while offset < size:
      write_size = min(4096, size - offset)
      ret = self.handle.bulkWrite(self.outep, data[offset : offset + write_size], 1000)
      offset = offset + ret
    
  def read(self, size, timeout):
    if self.handle is None:
      raise DeviceNotOpened()
    timeout = timeout + time.time()
    data = b""
    offset = 0
    while offset < size and time.time() < timeout:
      ret = bytes(bytearray(self.handle.bulkRead(self.inep, min(64, size - offset + 2), 1000)))
      data = data + ret[2:]
      offset = offset + len(ret) - 2
    return data
