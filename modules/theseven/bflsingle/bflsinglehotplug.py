# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
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



#################################################################
# Butterfly Labs Inc. BitFORCE Single hotplug controller module #
#################################################################



import traceback
from glob import glob
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .bflsingleworker import BFLSingleWorker



# Worker main class, referenced from __init__.py
class BFLSingleHotplugWorker(BaseWorker):
  
  version = "theseven.bflsingle hotplug manager v0.1.0beta"
  default_name = "BFL Single hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    try:
      import serial
      found = False
      for port in glob("/dev/serial/by-id/usb-Butterfly_Labs_Inc._BitFORCE_SHA256*"):
        try:
          handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
          handle.close()
          found = True
          break
        except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(BFLSingleHotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self).apply_settings()
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._start()
    # Initialize child map
    self.childmap = {}
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleHotplugWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)
    # Shut down child workers
    while self.children:
      child = self.children.pop(0)
      try:
        self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    number = 0
  
    # Loop until we are shut down
    while not self.shutdown:
    
      import serial

      try:
        boards = {}
        for port in glob("/dev/serial/by-id/usb-Butterfly_Labs_Inc._BitFORCE_SHA256*"):
          available = False
          try:
            handle = serial.Serial(port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)
            handle.close()
            available = True
          except: pass
          boards[port] = available
                
        kill = []
        for serial, child in self.childmap.items():
          if not serial in boards:
            kill.append((serial, child))
            
        for serial, child in kill:
          try:
            self.core.log(self, "Shutting down worker %s...\n" % (child.settings.name), 800)
            child.stop()
          except Exception as e:
            self.core.log(self, "Could not stop worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
          childstats = child.get_statistics()
          fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
          for field in fields: self.stats[field] += childstats[field]
          try: self.child.destroy()
          except: pass
          del self.childmap[port]
          try: self.children.remove(child)
          except: pass
              
        for port, available in boards.items():
          if port in self.childmap or not available: continue
          number += 1
          child = BFLSingleWorker(self.core)
          child.settings.name = "Autodetected BFL Single %d" % number
          child.settings.port = port
          child.apply_settings()
          self.childmap[port] = child
          self.children.append(child)
          try:
            self.core.log(self, "Starting up worker %s...\n" % (child.settings.name), 800)
            child.start()
          except Exception as e:
            self.core.log(self, "Could not start worker %s: %s\n" % (child.settings.name, traceback.format_exc()), 100, "rB")
              
      except: self.core.log(self, "Caught exception: %s\n" % traceback.format_exc(), 100, "rB")
          
      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)
