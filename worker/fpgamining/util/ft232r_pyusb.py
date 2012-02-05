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
# FT232R bitbanging interface via PyUSB #
#########################################

import usb
import struct
import threading
from jtag import JTAG
import time

DEFAULT_FREQUENCY = 3000000

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
      return struct.pack('=c', chr(((tck&1) << self.tck0) | ((tms&1) << self.tms0) | ((tdi&1) << self.tdi0)))
    if chain == 1:
      return struct.pack('=c', chr(((tck&1) << self.tck1) | ((tms&1) << self.tms1) | ((tdi&1) << self.tdi1)))
    if chain == 2:
      return struct.pack('=c', chr(((tck&1) << self.tck0) | ((tms&1) << self.tms0) | ((tdi&1) << self.tdi0) |
                                   ((tck&1) << self.tck1) | ((tms&1) << self.tms1) | ((tdi&1) << self.tdi1)))
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
    return struct.pack('=c', chr(((tck&1) << self.tck) | ((tms&1) << self.tms) | ((tdi&1) << self.tdi)))


class FT232R:
  def __init__(self, miner, worker, deviceid):
    self.mutex = threading.RLock()
    self.miner = miner
    self.worker = worker
    self.handle = None
    self.debug = 0
    self.synchronous = None
    self.write_buffer = ""
    self.portlist = None
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
            manufacturer = handle.getString(dev.iManufacturer, 100)
            product = handle.getString(dev.iProduct, 100)
            serial = handle.getString(dev.iSerialNumber, 100)
            if manufacturer == "FTDI" and product == "FT232R USB UART":
              if deviceid == "" or deviceid == serial:
                try:
                  handle.reset()
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
    self.portlist = FT232R_PortList(7, 6, 5, 4, 3, 2, 1, 0)
    self.handle.controlMsg(0x40, 3, None, 0, 0)
    self._setSyncMode()
    self._purgeBuffers()
    
  def __enter__(self): 
    return self

  # Be sure to close the opened handle, if there is one.
  # The device may become locked if we don't (requiring an unplug/plug cycle)
  def __exit__(self, exc_type, exc_value, traceback):
    self.close()
    return False
  
  def _log(self, msg, level=1):
    if level <= self.debug:
      self.miner.log(self.worker.name + ": FT232R: " + msg + "\n")
  
  def close(self):
    with self.mutex:
      if self.handle is None:
        return

      self._log("Closing device...")

      try:
        self.handle.releaseInterface()
        self.handle.setConfiguration(0)
        self.handle.reset()
      finally:
        self.handle = None

      self._log("Device closed.")
  
  # Purges the FT232R's buffers.
  def _purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()
    self.handle.controlMsg(0x40, 0, None, 1, self.index)
    self.handle.controlMsg(0x40, 0, None, 2, self.index)
    
  def _setBitMode(self, mask, mode):
    self.handle.controlMsg(0x40, 0xb, None, (mode << 8) | mask, self.index)
  
  def _setSyncMode(self):
    """Put the FT232R into Synchronous mode."""
    if self.handle is None:
      raise DeviceNotOpened()

    self._log("Device entering Synchronous mode.")

    self._setBitMode(self.portlist.output_mask(), 0)
    self._setBitMode(self.portlist.output_mask(), 4)
    self.synchronous = True

  def _setAsyncMode(self):
    """Put the FT232R into Asynchronous mode."""
    if self.handle is None:
      raise DeviceNotOpened()

    self._log("Device entering Asynchronous mode.")

    self._setBitMode(self.portlist.output_mask(), 0)
    self._setBitMode(self.portlist.output_mask(), 1)
    self.synchronous = False
  
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
    self._setBitMode(read_mask | pin_state, CBUS_mode)

  def _getCBUSBits(self):
    SIO_0 = 0
    SIO_1 = 1
    data = self.handle.controlMsg(0xc0, 0xc, 1, 0, self.index)
    return (((data[0] >> SIO_0) & 1), ((data[0] >> SIO_1) & 1)) 
    
  def write(self, data):
    with self.mutex:
      size = len(data)
      offset = 0
      while offset < size:
        self._log("Writing: %d bytes left" % (size - offset))
        write_size = min(4096, size - offset)
        ret = self.handle.bulkWrite(self.outep, data[offset : offset + write_size])
        offset = offset + ret
    
  def read(self, size):
    with self.mutex:
      data = ""
      offset = 0
      while offset < size:
        self._log("Reading: %d bytes left" % (size - offset))
        ret = self.handle.bulkRead(self.inep, min(64, size - offset + 2))
        data = data + struct.pack("%dB" % (len(ret) - 2), *ret[2:])
        offset = offset + len(ret) - 2
      return data
    
  def flush(self):
    with self.mutex:
      """Write all data in the write buffer and purge the FT232R buffers"""
      self._setAsyncMode()
      self.write(self.write_buffer)
      self.write_buffer = ""
      self._setSyncMode()
      self._purgeBuffers()
  
  def read_data(self, num):
    with self.mutex:
      """Read num bytes from the FT232R and return an array of data."""
      self._log("Reading %d bytes." % num)
      
      if num == 0:
        self.flush()
        return []

      # Repeat the last byte so we can read the last bit of TDO.
      write_buffer = self.write_buffer[-(num*3):]
      self.write_buffer = self.write_buffer[:-(num*3)]

      # Write all data that we don't care about.
      if len(self.write_buffer) > 0:
        self._log("Flushing out " + str(len(self.write_buffer)))
        self.flush()
        self._purgeBuffers()

      data = []

      while len(write_buffer) > 0:
        bytes_to_write = min(len(write_buffer), 3072)
        
        self._log("Writing %d/%d bytes" % (bytes_to_write, len(write_buffer)))
        self.write(write_buffer[:bytes_to_write])
        write_buffer = write_buffer[bytes_to_write:]
        #self._log("Status: " + str(self.handle.getStatus()))
        #self._log("QueueStatus: " + str(self.handle.getQueueStatus()))
        
        data.extend(self.read(bytes_to_write))
        
      self._log("Read %d bytes." % len(data))
      
      return data

  def read_temps(self):
    with self.mutex:
      self._log("Reading temp sensors.")
      
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
      