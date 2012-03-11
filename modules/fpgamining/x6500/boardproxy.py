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



#################################################################################
# FPGA Mining LLC X6500 FPGA Miner Board out of process board access dispatcher #
#################################################################################



import time
import signal
import traceback
from threading import Thread, Condition, RLock
from multiprocessing import Process
from .util.ft232r import FT232R, FT232R_PyUSB, FT232R_D2XX, FT232R_PortList
from .util.jtag import JTAG
from .util.fpga import FPGA



class X6500BoardProxy(Process):
  

  def __init__(self, rxconn, txconn, serial, takeover, useftd2xx, pollinterval):
    super(X6500BoardProxy, self).__init__()
    self.rxconn = rxconn
    self.txconn = txconn
    self.serial = serial
    self.takeover = takeover
    self.useftd2xx = useftd2xx
    self.pollinterval = pollinterval


  def run(self):
    signal.signal(signal.SIGINT, signal.SIG_IGN)
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
      if self.useftd2xx: self.device = FT232R(FT232R_D2XX(self.serial))
      else: self.device = FT232R(FT232R_PyUSB(self.serial, self.takeover))
      self.fpgas = [FPGA(self, "FPGA0", self.device, 0), FPGA(self, "FPGA1", self.device, 1)]
      
      for id, fpga in enumerate(self.fpgas):
        fpga.id = id
        self.log("Discovering FPGA %d...\n" % id, 600)
        fpga.detect()
        for idcode in fpga.jtag.idcodes:
          self.log("FPGA %d: %s - Firmware: rev %d, build %d\n" % (id, JTAG.decodeIdcode(idcode), fpga.firmware_rev, fpga.firmware_build), 500)
        if fpga.jtag.deviceCount != 1: raise Exception("This module needs two JTAG buses with one FPGA each!")

      # Start polling thread
      self.pollingthread = Thread(None, self.polling_thread, "polling_thread")
      self.pollingthread.daemon = True
      self.pollingthread.start()
      
      self.send("started_up", self.fpgas[0].firmware_rev, self.fpgas[1].firmware_rev)

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
          self.fpgas[data[1]].writeJob(data[2])
          end = time.time()
          self.respond(start, end)
        
        elif data[0] == "shutdown_fpga":
          self.fpgas[data[1]].sleep()
        
        elif data[0] == "set_speed":
          self.fpgas[data[1]].setClockSpeed(data[2])
        
        elif data[0] == "get_speed":
          self.respond(self.fpgas[data[1]].readClockSpeed())
        
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
        for i in range(2):
          nonce = self.fpgas[i].readNonce()
          if nonce is not None: self.send("nonce_found", i, time.time(), nonce)
    
        counter += 1
        if counter >= 10:
          counter = 0
          # Read temperatures
          temps = self.device.read_temps()
          self.send("temperature_read", *temps)
        
        with self.wakeup: self.wakeup.wait(self.pollinterval)
        
    except Exception as e:
      self.error = e
      # Unblock main thread
      self.send("ping")
