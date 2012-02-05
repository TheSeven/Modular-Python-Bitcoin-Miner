# Copyright (C) 2011 by fpgaminer <fpgaminer@bitcoin-mining.com>
#                       fizzisist <fizzisist@fpgamining.com>
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

import d2xx
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
    devices = d2xx.listDevices()
    for devicenum, serial in enumerate(devices):
      if deviceid != "" and deviceid != serial: continue
      try:
        self.handle = d2xx.open(devicenum)
        self.serial = serial
        break
      except: pass
    if self.handle == None: raise Exception("Can not open the specified device")
    self.portlist = FT232R_PortList(7, 6, 5, 4, 3, 2, 1, 0)
    self._setBaudRate(DEFAULT_FREQUENCY)
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
        self.handle.close()
      finally:
        self.handle = None

      self._log("Device closed.")
  
  # Purges the FT232R's buffers.
  def _purgeBuffers(self):
    if self.handle is None:
      raise DeviceNotOpened()

    self.handle.purge(0)
  
  def _setBaudRate(self, rate):
    self._log("Setting baudrate to %i" % rate)

    # Documentation says that we should set a baudrate 16 times lower than
    # the desired transfer speed (for bit-banging). However I found this to
    # not be the case. 3Mbaud is the maximum speed of the FT232RL
    self.handle.setBaudRate(rate)
    #self.handle.setDivisor(0)  # Another way to set the maximum speed.
  
  def _setSyncMode(self):
    """Put the FT232R into Synchronous mode."""
    if self.handle is None:
      raise DeviceNotOpened()

    self._log("Device entering Synchronous mode.")

    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 4)
    self.synchronous = True

  def _setAsyncMode(self):
    """Put the FT232R into Asynchronous mode."""
    if self.handle is None:
      raise DeviceNotOpened()

    self._log("Device entering Asynchronous mode.")

    self.handle.setBitMode(self.portlist.output_mask(), 0)
    self.handle.setBitMode(self.portlist.output_mask(), 1)
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
    self.handle.setBitMode(read_mask | pin_state, CBUS_mode)

  def _getCBUSBits(self):
    SIO_0 = 0
    SIO_1 = 1
    data = self.handle.getBitMode()
    return (((data >> SIO_0) & 1), ((data >> SIO_1) & 1)) 
    
  def write(self, data):
    with self.mutex:
      size = len(data)
      offset = 0
      while offset < size:
        self._log("Writing: %d bytes left" % (size - offset))
        write_size = min(4096, size - offset)
        ret = self.handle.write(data[offset : offset + write_size])
        offset = offset + ret
    
  def read(self, size):
    with self.mutex:
      data = ""
      offset = 0
      while offset < size:
        self._log("Reading: %d bytes left" % (size - offset))
        ret = self.handle.read(min(4096, size - offset))
        data = data + ret
        offset = offset + len(ret)
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
        wrote = self.handle.write(write_buffer[:bytes_to_write])
        self._log("Wrote %d bytes" % wrote)
        if wrote != bytes_to_write:
          raise WriteError()
        write_buffer = write_buffer[wrote:]
        #self._log("Status: " + str(self.handle.getStatus()))
        #self._log("QueueStatus: " + str(self.handle.getQueueStatus()))
        
        start_time = time.time()
        while self.handle.getQueueStatus() < wrote:
          if time.time() - start_time > 5:
            self._log("Timeout while reading data!")
            return data
          time.sleep(0.1)
          #self._log("QueueStatus: " + str(self.handle.getQueueStatus()))
        
        data.extend(self.handle.read(wrote))
        
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
      