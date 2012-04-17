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



##############################################################################
# Generic FTDI JTAG bitbanging worker out of process board access dispatcher #
##############################################################################



import time
import signal
import traceback
from threading import Thread, Condition, RLock
from multiprocessing import Process
from .driver import FTDIJTAGDevice



class FTDIJTAGBoardProxy(Process):
  

  def __init__(self, rxconn, txconn, serial, takeover, firmware, pollinterval):
    super(FTDIJTAGBoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.serial = serial
    self.takeover = takeover
    self.firmware = firmware
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
    self.lock = RLock()
    self.wakeup = Condition()
    self.error = None
    self.pollingthread = None
    self.shutdown = False
  
    try:

      # Listen for setup commands
      while True:
        data = self.rxconn.recv()
        
        if data[0] == "connect": break
        
        else: raise Exception("Unknown setup message: %s" % str(data))
        
      # Connect to board
      self.device = FTDIJTAGDevice(self, self.serial, self.takeover, self.firmware)
      self.fpgacount = self.device.get_fpga_count()
      self.log("Found %i FPGA%s\n" % (self.fpgacount, 's' if self.fpgacount != 1 else ''), 500)
      if not self.fpgacount: raise Exception("No FPGAs detected!")
      
      # Drain leftover nonces
      while True:
        nonces = self.device.read_nonces()
        if not nonces: break

      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up", self.fpgacount)

      # Listen for commands
      while True:
        if self.error: raise self.error
      
        data = self.rxconn.recv()
        
        if data[0] == "shutdown": break

        elif data[0] == "ping": self.send("pong")

        elif data[0] == "pong": pass

        elif data[0] == "set_pollinterval":
          self.pollinterval = data[1]
          with self.wakeup: self.wakeup.notify()
        
        elif data[0] == "send_job":
          start = time.time()
          self.device.send_job(data[1], data[2])
          end = time.time()
          self.respond(start, end)
        
        elif data[0] == "set_speed":
          self.device.set_speed(data[1], data[2])
        
        elif data[0] == "get_speed":
          self.respond(self.device.get_speed(data[1]))
        
        else: raise Exception("Unknown message: %s" % str(data))
      
    except: self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
    finally:
      self.shutdown = True
      with self.wakeup: self.wakeup.notify()
      try: self.pollingthread.join(2)
      except: pass
      self.send("dying")
      
      
  def send(self, *args):
    with self.lock: self.txconn.send(args)
      
      
  def respond(self, *args):
    self.send("response", *args)
      
      
  def log(self, message, loglevel, format = ""):
    self.send("log", message, loglevel, format)
    
    
  def polling_thread(self):
    try:
      counter = 0
      while not self.shutdown:
        # Poll for nonces
        nonces = self.device.read_nonces()
        for fpga in nonces: self.send("nonce_found", fpga, time.time(), nonces[fpga])
        
        counter += 1
        if counter >= 20:
          counter = 0
          self.send("temperatures_read", self.device.read_temperatures())
    
        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.log("Exception caught: %s" % traceback.format_exc(), 100, "r")
      self.error = e
      # Unblock main thread
      self.send("ping")
