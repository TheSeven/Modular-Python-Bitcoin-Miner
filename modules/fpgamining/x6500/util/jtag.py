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

# Usage Example:
# with JTAG() as jtag:
#   blah blah blah ...
#

from .TAP import TAP
import sys
import time
import struct
import threading
try: import queue
except ImportError: import Queue as queue


class NoDevicesDetected(Exception): pass
class IDCodesNotRead(Exception): pass
class ChainNotProperlyDetected(Exception): pass
class InvalidChain(Exception): pass
class WriteError(Exception): pass

class UnknownIDCode(Exception):
  def __init__(self, idcode):
    self.idcode = idcode
  def __str__(self):
    return repr(self.idcode)

# LUT for instruction register length based on ID code:
irlength_lut = {0x403d093: 6, 0x401d093: 6, 0x4008093: 6, 0x5057093: 16, 0x5059093: 16};
# LUT for device name based on ID code:
name_lut = {0x403d093: 'Spartan 6 LX150T', 0x401d093: 'Spartan 6 LX150', 0x5059093: 'Unknown', 0x5057093: 'Unknown'}

class JTAG:
  def __init__(self, ft232r, chain):
    self.ft232r = ft232r
    self.chain = chain
    self.deviceCount = None
    self.idcodes = None
    self.irlengths = None
    self.current_instructions = [1] * 100  # Default is to put all possible devices into BYPASS. # TODO: Should be 1000
    self.current_part = 0
    self._tckcount = 0
    self.portlist = ft232r.portlist.chain_portlist(chain)
    self.tap = TAP(self.jtagClock)

    
  def detect(self):
    """Detect all devices on the JTAG chain. Call this after open."""
    self.deviceCount = None
    self.idcodes = None
    self.irlengths = None
    
    retries_left = 5
    while retries_left > 0:
      self.deviceCount = self._readDeviceCount()
      if self.deviceCount is None or self.deviceCount == 0:
        retries_left -= 1
      else:
        break
    if self.deviceCount is None or self.deviceCount == 0:
      raise NoDevicesDetected
    
    self._readIdcodes()
    self._processIdcodes()
    
    self.reset()
    self.part(0)
    self.ft232r.flush()
  
  def part(self, part):
    """Change the active part."""
    self.current_part = part
  
  def instruction(self, instruction):
    """Sets the current_instructions to a new instruction.
    Accepts an integer instruction and builds an array of bits.
    """
    if self.irlengths is None:
      raise ChainNotProperlyDetected()
    
    start = sum(self.irlengths[self.current_part+1:])
    end = start + self.irlengths[self.current_part]
    
    for i in range(len(self.current_instructions)):
      if i >= start and i < end:
        self.current_instructions[i] = instruction & 1
        instruction >>= 1
      else:
        self.current_instructions[i] = 1
  
  def reset(self):
    """Reset JTAG chain"""
    total_ir = 100 # TODO: Should be 1000
    if self.irlengths is not None:
      total_ir = sum(self.irlengths)

    self.current_instructions = [1] * total_ir
    #self.shift_ir()
    self.tap.reset()
  
  def shift_ir(self, read=False):
    self.tap.goto(TAP.SELECT_IR)
    self.tap.goto(TAP.SHIFT_IR)
    
    for bit in self.current_instructions[:-1]:
      self.jtagClock(tdi=bit)
    self.jtagClock(tdi=self.current_instructions[-1], tms=1)

    self._tckcount = 0
    self.tap.goto(TAP.IDLE)

    if read:
      return self.read_tdo(len(self.current_instructions)+self._tckcount)[:-self._tckcount]
  
  def read_ir(self):
    return self.shift_ir(read=True)
  
  # TODO: Doesn't work correctly if not operating on the last device in the chain
  def shift_dr(self, bits, read=False):
    self.tap.goto(TAP.SELECT_DR)
    self.tap.goto(TAP.SHIFT_DR)

    bits += [0] * self.current_part

    for bit in bits[:-1]:
      self.jtagClock(tdi=bit)
    self.jtagClock(tdi=bits[-1], tms=1)

    self._tckcount = 0
    self.tap.goto(TAP.IDLE)

    if read:
      return self.read_tdo(len(bits)+self._tckcount)[:len(bits)-self.current_part]
  
  def read_dr(self, bits):
    return self.shift_dr(bits, read=True)
  
  def read_tdo(self, num):
    """Reads num bits from TDO, and returns the bits as an array."""
    data = self.ft232r.read_data(num)
    bits = []
    for n in range(len(data)//3):
      bits.append((struct.unpack("B", data[n*3+2:n*3+3])[0] >> self.portlist.tdo)&1)
    
    return bits
  
  def runtest(self, tckcount):
    """Clock TCK in the IDLE state for tckcount cycles"""
    self.tap.goto(TAP.IDLE)
    for i in range(tckcount):
      self.jtagClock(tms=0)
      
  def bitstream_preparation_thread(self, bitstream, buffer):
    python2 = sys.hexversion // 0x1000000 < 3
    bytetotal = len(bitstream)
    for i in range(0, bytetotal, 1024):
      chunk = b""
      for d in bitstream[i : min(bytetotal - 1, i + 1024)]:
        if python2: d = ord(d)
        val7 = (d >> 6) & 2
        val7 = val7 | (val7 << 4)
        val6 = (d >> 5) & 2
        val6 = val6 | (val6 << 4)
        val5 = (d >> 4) & 2
        val5 = val5 | (val5 << 4)
        val4 = (d >> 3) & 2
        val4 = val4 | (val4 << 4)
        val3 = (d >> 2) & 2
        val3 = val3 | (val3 << 4)
        val2 = (d >> 1) & 2
        val2 = val2 | (val2 << 4)
        val1 = d & 2
        val1 = val1 | (val1 << 4)
        val0 = (d & 1) << 1
        val0 = val0 | (val0 << 4)
        chunk += struct.pack("16B", val7, val7 | 0x88, val6, val6 | 0x88, \
                                    val5, val5 | 0x88, val4, val4 | 0x88, \
                                    val3, val3 | 0x88, val2, val2 | 0x88, \
                                    val1, val1 | 0x88, val0, val0 | 0x88)
      buffer.put(chunk)               
    buffer.put(None)
  
  def load_bitstream(self, bitstream, progressCallback=None):
    self.tap.goto(TAP.SELECT_DR)
    self.tap.goto(TAP.SHIFT_DR)
    self.ft232r.flush()
    
    self.ft232r.setAsyncMode()
    
    start_time = time.time()
    last_update = 0

    bytetotal = len(bitstream)
    written = 0
    buffer = queue.Queue(16)
    thread = threading.Thread(None, self.bitstream_preparation_thread, "bitstreamprepare", kwargs = {"bitstream": bitstream, "buffer": buffer})
    thread.daemon = True
    thread.start()
    
    while True:
      chunk = buffer.get()
      if chunk == None: break
      self.ft232r.write(chunk)
      written = written + len(chunk) / 16
      
      if time.time() > (last_update + 3) and progressCallback:
        progressCallback(start_time, time.time(), written, bytetotal)
        last_update = time.time()
    
    self.ft232r.setSyncMode()
    self.ft232r.purgeBuffers()
    
    d = struct.unpack("B", bitstream[-1:])[0]
    for i in range(7, 0, -1):
      self.jtagClock(tdi=(d >> i) & 1)
    self.jtagClock(tdi=d & 1, tms=1)
    
    self.tap.goto(TAP.IDLE)
    self.ft232r.flush()
  
  def _formatJtagClock(self, tms=0, tdi=0):
    return self._formatJtagState(0, tms, tdi) + self._formatJtagState(1, tms, tdi)
  
  def _formatJtagState(self, tck, tms, tdi):
    return self.portlist.format(tck, tms, tdi)
  
  def jtagClock(self, tms=0, tdi=0):    
    self.ft232r.write_buffer += self._formatJtagState(0, tms, tdi)
    self.ft232r.write_buffer += self._formatJtagState(1, tms, tdi)
    self.ft232r.write_buffer += self._formatJtagState(1, tms, tdi)

    self.tap.clocked(tms)
    self._tckcount += 1
  
  def parseByte(self, bits):
    return (bits[7] << 7) | (bits[6] << 6) | (bits[5] << 5) | (bits[4] << 4) | (bits[3] << 3) | (bits[2] << 2) |  (bits[1] << 1) | bits[0]
  
  def _readDeviceCount(self):
    deviceCount = None
    #self.tap.reset()

    # Force BYPASS
    self.reset()
    self.part(0)

    # Force BYPASS
    self.shift_ir()
    #self.shiftIR([1]*100)  # Should be 1000

    # Flush DR registers
    self.shift_dr([0]*100)


    # Fill with 1s to detect chain length
    data = self.read_dr([1]*100)

    # Now see how many devices there were.
    for i in range(0, len(data)-1):
      if data[i] == 1:
        deviceCount = i
        break

    return deviceCount
  
  def _readIdcodes(self):
    if self.deviceCount is None:
      raise NoDevicesDetected()

    self.idcodes = []

    #self.tap.reset()
    self.reset()
    self.part(0)

    data = self.read_dr([1]*32*self.deviceCount)
    
    for d in range(self.deviceCount):
      idcode = self.parseByte(data[0:8])
      idcode |= self.parseByte(data[8:16]) << 8
      idcode |= self.parseByte(data[16:24]) << 16
      idcode |= self.parseByte(data[24:32]) << 24
      data = data[32:]

      self.idcodes.insert(0, idcode)
  
  def _processIdcodes(self):
    if self.idcodes is None:
      raise IDCodesNotRead()

    self.irlengths = []


    for idcode in self.idcodes:
      if (idcode & 0x0FFFFFFF) in irlength_lut:
        self.irlengths.append(irlength_lut[idcode & 0x0FFFFFFF])
      else:
        self.irlengths = None
        raise UnknownIDCode(idcode)
  
  @staticmethod
  def decodeIdcode(idcode):
    if (idcode & 1) != 1:
      return "Warning: Bit 0 of IDCODE is not 1. Not a valid Xilinx IDCODE."

    manuf = (idcode >> 1) & 0x07ff
    size = (idcode >> 12) & 0x01ff
    family = (idcode >> 21) & 0x007f
    rev = (idcode >> 28) & 0x000f

    return name_lut[idcode & 0xFFFFFFF]
    #print "Manuf: %x, Part Size: %x, Family Code: %x, Revision: %0d" % (manuf, size, family, rev)
