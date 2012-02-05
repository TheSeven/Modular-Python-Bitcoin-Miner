# Copyright (C) 2011 by fizzisist <fizzisist@fpgamining.com>
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

import struct
from .jtag import JTAG

class Object(object):
  pass

# JTAG instructions:
USER_INSTRUCTION = 0b000010
JSHUTDOWN        = 0b001101
JSTART           = 0b001100
JPROGRAM         = 0b001011
CFG_IN           = 0b000101
CFG_OUT          = 0b000100
BYPASS           = 0b111111

def int2bits(i, bits):
  """Convert an integer to an array of bits, LSB first."""
  result = []
  for n in range(bits):
    result.append(i & 1)
    i = i >> 1
  return result

def bits2int(bits):
  """Convert an array of bits to an integer, LSB first."""
  x = 0
  for i in range(len(bits)):
    x |= bits[i] << i
  return x

class FPGA:
  def __init__(self, miner, name, ft232r, chain):
    self.miner = miner
    self.name = name
    self.ft232r = ft232r
    self.chain = chain
    self.jtag = JTAG(miner, name, ft232r, chain)
    
    self.asleep = True
  
  def readByte(self):
    bits = int2bits(0, 13)
    byte = bits2int(self.jtag.read_dr(bits))
    return byte
  
  def readNonce(self):
    with self.ft232r.mutex:
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()
      self.asleep = False

      # Sync to the beginning of a nonce.
      # The MSB is a VALID flag. If 0, data is invalid (queue empty).
      # The next 4-bits indicate which byte of the nonce we got.
      # 1111 is LSB, and then 0111, 0011, 0001.
      byte = None
      while True:
        byte = self.readByte()

        #if byte != 0: self.miner.log(self.name + ": FPGA: Read: %04x\n" % byte)

        # check data valid bit:
        if byte < 0x1000:
          self.jtag.tap.reset()
          return None
        
        #self.miner.log(self.name + ": FPGA: Read: %04x\n" % byte)
        
        # check byte counter:
        if (byte & 0xF00) == 0xF00:
          break
      
      # We now have the first byte
      nonce = byte & 0xFF
      count = 1
      #self.miner.log(self.name + ": FPGA: Potential nonce, reading the rest...\n")
      while True:
        byte = self.readByte()
        
        #if byte != 0: self.miner.log(self.name + ": FPGA: Read: %04x\n" % byte)
        
        # check data valid bit:
        if byte < 0x1000:
          self.jtag.tap.reset()
          return None
        
        # check byte counter:
        if (byte & 0xF00) >> 8 != (0xF >> count):
          self.jtag.tap.reset()
          return None
        
        nonce |= (byte & 0xFF) << (count * 8)
        count += 1
        
        if (byte & 0xF00) == 0x100:
          break

      self.jtag.tap.reset()

      #self.miner.log(self.name + ": FPGA: Nonce completely read: %08x\n" % nonce)

      return struct.pack("<I", nonce)
  
  # TODO: This may not actually clear the queue, but should be correct most of the time.
  def clearQueue(self):
    with self.ft232r.mutex:
      self.wake()
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()
      self.asleep = False
      
      #self.miner.log(self.name + ": FPGA: Clearing queue...\n")
      while True:
        if self.readByte() < 0x1000:
          break
      self.jtag.tap.reset()
      
      #self.miner.log(self.name + ": FPGA: Queue cleared...\n")
  
  def writeJob(self, job):
    with self.ft232r.mutex:
      # We need the 256-bit midstate, and 12 bytes from data.
      # The first 64 bytes of data are already hashed (hence midstate),
      # so we skip that. Of the last 64 bytes, 52 bytes are constant and
      # not needed by the FPGA.
      
      #start_time = time.time()
      
      midstate = job.state[::-1]
      data = job.data[75:63:-1]

      #self.miner.log(self.name + ": FPGA: Loading job data...\n")

      #self.jtag._setAsyncMode()
      
      self.jtag.tap.reset()
      self.jtag.instruction(USER_INSTRUCTION)
      self.jtag.shift_ir()

      data = midstate + data + b"\0"

      for i in range(len(data)):
        x = struct.unpack("B", data[i : i + 1])[0]

        if i != 0:
          x = 0x100 | x
          
        self.jtag.shift_dr(int2bits(x, 13))
      
      self.jtag.tap.reset()

      self.ft232r.flush()
      
      #self.miner.log(self.name + ": FPGA: Job data loaded in %.3f seconds\n" % (time.time() - start_time))
      #self.miner.log(self.name + ": FPGA: Job data loaded\n")
  
  def sleep(self):
    with self.ft232r.mutex:
      self.miner.log(self.name + ": Going to sleep...\n")
      '''
      self.jtag.tap.reset()
      self.jtag.instruction(JSHUTDOWN)
      self.jtag.shift_ir()
      self.jtag.runtest(24)
      self.jtag.tap.reset()
      
      self.ft232r.flush()
      '''
      self.asleep = True
  
  def wake(self):
    with self.ft232r.mutex:
      self.miner.log(self.name + ": Waking up...\n")
      self.jtag.tap.reset()
      self.jtag.instruction(JSTART)
      self.jtag.shift_ir()
      self.jtag.runtest(24)
      self.jtag.instruction(BYPASS)
      self.jtag.shift_ir()
      self.jtag.instruction(BYPASS)
      self.jtag.shift_ir()
      self.jtag.instruction(JSTART)
      self.jtag.shift_ir()
      self.jtag.runtest(24)
      self.jtag.tap.reset()
      
      self.ft232r.flush()
      self.asleep = False
  
  @staticmethod
  def programBitstream(miner, ft232r, jtag, bitstream, progresscallback = None):
    with ft232r.mutex:
      # Select the device
      jtag.reset()
      jtag.part(jtag.deviceCount-1)
      
      jtag.instruction(BYPASS) 
      jtag.shift_ir()

      jtag.instruction(JPROGRAM)
      jtag.shift_ir()

      jtag.instruction(CFG_IN)
      jtag.shift_ir()

      # Clock TCK for 10000 cycles
      jtag.runtest(10000)

      jtag.instruction(CFG_IN)
      jtag.shift_ir()
      jtag.shift_dr([0]*32)
      jtag.instruction(CFG_IN)
      jtag.shift_ir()

      ft232r.flush()
      
      # Load bitstream into CFG_IN
      jtag.load_bitstream(bitstream, progresscallback)

      jtag.instruction(JSTART)
      jtag.shift_ir()

      # Let the device start
      jtag.runtest(24)
      
      jtag.instruction(BYPASS)
      jtag.shift_ir()
      jtag.instruction(BYPASS)
      jtag.shift_ir()

      jtag.instruction(JSTART)
      jtag.shift_ir()

      jtag.runtest(24)
      
      # Check done pin
      #jtag.instruction(BYPASS)
      # TODO: Figure this part out. & 0x20 should equal 0x20 to check the DONE pin ... ???
      #print jtag.read_ir() # & 0x20 == 0x21
      #jtag.instruction(BYPASS)
      #jtag.shift_ir()
      #jtag.shift_dr([0])

      ft232r.flush()
