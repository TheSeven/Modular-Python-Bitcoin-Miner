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

class TAPStateError(Exception):
  def __init__(self, current, destination):
    self.current = TAP.STR_TRANSLATE[current]
    self.destination = TAP.STR_TRANSLATE[destination]
  def __str__(self):
    return self.current + " -> " + self.destination

class TAP:
  TLR = 0
  IDLE = 1
  SELECT_DR = 2
  CAPTURE_DR = 3
  SHIFT_DR = 4
  EXIT1_DR = 5
  PAUSE_DR = 6
  EXIT2_DR = 7
  UPDATE_DR = 8
  SELECT_IR = 9
  CAPTURE_IR = 10
  SHIFT_IR = 11
  EXIT1_IR = 12
  PAUSE_IR = 13
  EXIT2_IR = 14
  UPDATE_IR = 15

  STR_TRANSLATE = ['TLR','IDLE','SELECT_DR','CAPTURE_DR','SHIFT_DR','EXIT1_DR','PAUSE_DR','EXIT2_DR','UPDATE_DR','SELECT_IR','CAPTURE_IR','SHIFT_IR','EXIT1_IR','PAUSE_IR','EXIT2_IR','UPDATE_IR']

  TRANSITIONS = {
    TLR: [IDLE, TLR],
    IDLE: [IDLE, SELECT_DR],
    SELECT_DR: [CAPTURE_DR, SELECT_IR],
    CAPTURE_DR: [SHIFT_DR, EXIT1_DR],
    SHIFT_DR: [SHIFT_DR, EXIT1_DR],
    EXIT1_DR: [PAUSE_DR, UPDATE_DR],
    PAUSE_DR: [PAUSE_DR, EXIT2_DR],
    EXIT2_DR: [SHIFT_DR, UPDATE_DR],
    UPDATE_DR: [IDLE, SELECT_DR],
    SELECT_IR: [CAPTURE_IR, TLR],
    CAPTURE_IR: [SHIFT_IR, EXIT1_IR],
    SHIFT_IR: [SHIFT_IR, EXIT1_IR],
    EXIT1_IR: [PAUSE_IR, UPDATE_IR],
    PAUSE_IR: [PAUSE_IR, EXIT2_IR],
    EXIT2_IR: [SHIFT_IR, UPDATE_IR],
    UPDATE_IR: [IDLE, SELECT_DR]
  }

  def __init__(self, jtagClock):
    self.jtagClock = jtagClock
    self.state = None
  
  def reset(self):
    for i in range(6):
      self.jtagClock(tms=1)

    self.state = TAP.TLR
  
  def clocked(self, tms):
    if self.state is None:
      return
    
    state = self.state
    self.state = TAP.TRANSITIONS[self.state][tms]

  
  # When goto is called, we look at where we want to go and where we are.
  # Based on that we choose where to clock TMS low or high.
  # After that we see if we've reached our goal. If not, call goto again.
  # This recursive behavior keeps the function simple.
  def goto(self, state):
    # If state is Unknown, reset.
    if self.state is None:
      self.reset()
    elif state == TAP.TLR:
      self.jtagClock(tms=1)
    elif self.state == TAP.TLR:
      self.jtagClock(tms=0)
    elif state == TAP.SELECT_DR:
      if self.state != TAP.IDLE:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=1)
    elif state == TAP.SELECT_IR:
      if self.state != TAP.IDLE:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=1)
      self.jtagClock(tms=1)
    elif state == TAP.SHIFT_DR:
      if self.state != TAP.SELECT_DR:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=0)
      self.jtagClock(tms=0)
    elif state == TAP.SHIFT_IR:
      if self.state != TAP.SELECT_IR:
        raise TAPStateError(self.state, state)

      self.jtagClock(tms=0)
      self.jtagClock(tms=0)
    elif state == TAP.IDLE:
      if self.state == TAP.IDLE:
        self.jtagClock(tms=0)
      elif self.state == TAP.EXIT1_DR or self.state == TAP.EXIT1_IR:
        self.jtagClock(tms=1)
        self.jtagClock(tms=0)
      else:
        raise TAPStateError(self.state, state)
    else:
      raise TAPStateError(self.state, state)


    if self.state != state:
      self.goto(state)
    
  
  

