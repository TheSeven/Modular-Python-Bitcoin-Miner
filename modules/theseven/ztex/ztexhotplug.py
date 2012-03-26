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



##################################################
# ZTEX USB FPGA Module hotplug controller module #
##################################################



import traceback
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .ztexworker import ZtexWorker



# Worker main class, referenced from __init__.py
class ZtexHotplugWorker(BaseWorker):
  
  version = "theseven.ztex hotplug manager v0.1.0beta"
  default_name = "ZTEX hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware file location", "type": "string", "position": 1400},
    "blacklist": {
      "title": "Board list type",
      "type": "enum",
      "values": [
        {"value": True, "title": "Blacklist"},
        {"value": False, "title": "Whitelist"},
      ],
      "position": 2000
    },
    "boards": {
      "title": "Board list",
      "type": "list",
      "element": {"title": "Serial number", "type": "string"},
      "position": 2100
    },
    "scaninterval": {"title": "Bus scan interval", "type": "float", "position": 2200},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 5100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 5200},
  })
  
  
  @classmethod
  def autodetect(self, core):
    try:
      found = False
      try:
        import usb
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
              try:
                handle = dev.open()
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                try:
                  configuration = dev.configurations[0]
                  interface = configuration.interfaces[0][0]
                  handle.setConfiguration(configuration.value)
                  handle.claimInterface(interface.interfaceNumber)
                  handle.releaseInterface()
                  handle.setConfiguration(0)
                  found = True
                  break
                except: pass
              except: pass
          if found: break
      except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(ZtexHotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/ztex/firmware/"
    if not "blacklist" in self.settings: self.settings.blacklist = True
    if self.settings.blacklist == "false": self.settings.blacklist = False
    else: self.settings.blacklist = not not self.settings.blacklist
    if not "boards" in self.settings: self.settings.boards = []
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # Push our settings down to our children
    fields = ["takeover", "firmware", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexHotplugWorker, self)._start()
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
    super(ZtexHotplugWorker, self)._stop()
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
        self.core.log("%s: Shutting down worker %s...\n" % (self.settings.name, child.settings.name), 800)
        child.stop()
      except Exception as e:
        self.core.log("%s: Could not stop worker %s: %s\n" % (self.settings.name, child.settings.name, traceback.format_exc()), 100, "rB")

      
  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):
    # Loop until we are shut down
    while not self.shutdown:
    
      import usb

      try:
        boards = {}
        for bus in usb.busses():
          for dev in bus.devices:
            if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
              try:
                handle = dev.open()
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                try:
                  configuration = dev.configurations[0]
                  interface = configuration.interfaces[0][0]
                  handle.setConfiguration(configuration.value)
                  handle.claimInterface(interface.interfaceNumber)
                  handle.releaseInterface()
                  handle.setConfiguration(0)
                  available = True
                except: available = False
                boards[serial] = available
              except: pass
                
        for serial in boards.keys():
          if self.settings.blacklist:
            if serial in self.settings.boards: del boards[serial]
          else:
            if serial not in self.settings.board: del boards[serial]
                
        for serial, child in self.childmap.items():
          if not serial in boards:
            try:
              self.core.log("%s: Shutting down worker %s...\n" % (self.settings.name, child.settings.name), 800)
              child.stop()
            except Exception as e:
              self.core.log("%s: Could not stop worker %s: %s\n" % (self.settings.name, child.settings.name, traceback.format_exc()), 100, "rB")
            childstats = child.get_statistics()
            fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
            for field in fields: self.stats[field] += childstats[field]
            try: self.child.destroy()
            except: pass
            del self.childmap[serial]
            try: self.children.remove(child)
            except: pass
                
        for serial, available in boards.items():
          if serial in self.childmap: continue
          if not available and self.settings.takeover:
            try:
              for bus in usb.busses():
                if available: break
                for dev in bus.devices:
                  if available: break
                  if dev.idVendor == 0x221a and dev.idProduct >= 0x100 and dev.idProduct <= 0x1ff:
                    handle = dev.open()
                    _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                    if _serial == serial:
                      handle.reset()
                      time.sleep(1)
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      handle.reset()
                      time.sleep(1)
                      available = True
            except: pass
          if available:
            child = ZtexWorker(self.core)
            child.settings.name = "Ztex board " + serial
            child.settings.serial = serial
            fields = ["takeover", "firmware", "jobinterval", "pollinterval"]
            for field in fields: child.settings[field] = self.settings[field]
            child.apply_settings()
            self.childmap[serial] = child
            self.children.append(child)
            try:
              self.core.log("%s: Starting up worker %s...\n" % (self.settings.name, child.settings.name), 800)
              child.start()
            except Exception as e:
              self.core.log("%s: Could not start worker %s: %s\n" % (self.settings.name, child.settings.name, traceback.format_exc()), 100, "rB")
              
      except: self.core.log("Caught exception: %s\n" % traceback.format_exc(), 100, "rB")
          
      with self.wakeup: self.wakeup.wait(self.settings.scaninterval)
