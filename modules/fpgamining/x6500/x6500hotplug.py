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



####################################################################
# FPGA Mining LLC X6500 FPGA Miner Board hotplug controller module #
####################################################################



import traceback
from threading import Condition, Thread
from core.baseworker import BaseWorker
from .x6500worker import X6500Worker



# Worker main class, referenced from __init__.py
class X6500HotplugWorker(BaseWorker):
  
  version = "fpgamining.x6500 hotplug manager v0.1.0beta"
  default_name = "X6500 hotplug manager"
  can_autodetect = True
  settings = dict(BaseWorker.settings, **{
    "useftd2xx": {
      "title": "Driver",
      "type": "enum",
      "values": [
        {"value": False, "title": "PyUSB"},
        {"value": True, "title": "D2XX"},
      ],
      "position": 1100
    },
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "uploadfirmware": {"title": "Upload firmware", "type": "boolean", "position": 1300},
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
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 3000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 3100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 4000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 4100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 4200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 4300},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 4400},
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
            if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
              try:
                handle = dev.open()
                manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                product = handle.getString(dev.iProduct, 100).decode("latin1")
                serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
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
      if not found:
        try:
          import d2xx
          devices = d2xx.listDevices()
          for devicenum, serial in enumerate(devices):
            try:
              handle = d2xx.open(devicenum)
              handle.close()
              found = True
              break
            except: pass
        except: pass
      if found: core.add_worker(self(core))
    except: pass
    
    
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Check if pyusb is installed
    self.pyusb_available = False
    try:
      import usb
      self.pyusb_available = True
    except: pass
    self.d2xx_available = False
    try:
      import d2xx
      self.d2xx_available = True
    except: pass

    # Initialize bus scanner wakeup event
    self.wakeup = Condition()

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(X6500HotplugWorker, self).__init__(core, state)

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "useftd2xx" in self.settings:
      self.settings.useftd2xx = self.d2xx_available and not self.pyusb_available
    if self.settings.useftd2xx == "false": self.settings.useftd2xx = False
    else: self.settings.useftd2xx = not not self.settings.useftd2xx
    if not "takeover" in self.settings: self.settings.takeover = self.pyusb_available
    if not "uploadfirmware" in self.settings: self.settings.uploadfirmware = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
    if not "blacklist" in self.settings: self.settings.blacklist = True
    if self.settings.blacklist == "false": self.settings.blacklist = False
    else: self.settings.blacklist = not not self.settings.blacklist
    if not "boards" in self.settings: self.settings.boards = []
    if not "initialspeed" in self.settings: self.settings.initialspeed = 150
    self.settings.initialspeed = min(max(self.settings.initialspeed, 4), 250)
    if not "maximumspeed" in self.settings: self.settings.maximumspeed = 200
    self.settings.maximumspeed = min(max(self.settings.maximumspeed, 4), 300)
    if not "tempwarning" in self.settings: self.settings.tempwarning = 45
    self.settings.tempwarning = min(max(self.settings.tempwarning, 0), 60)
    if not "tempcritical" in self.settings: self.settings.tempcritical = 55
    self.settings.tempcritical = min(max(self.settings.tempcritical, 0), 80)
    if not "invalidwarning" in self.settings: self.settings.invalidwarning = 2
    self.settings.invalidwarning = min(max(self.settings.invalidwarning, 1), 10)
    if not "invalidcritical" in self.settings: self.settings.invalidcritical = 10
    self.settings.invalidcritical = min(max(self.settings.invalidcritical, 1), 50)
    if not "speedupthreshold" in self.settings: self.settings.speedupthreshold = 100
    self.settings.speedupthreshold = min(max(self.settings.speedupthreshold, 50), 10000)
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    if not "scaninterval" in self.settings or not self.settings.scaninterval: self.settings.scaninterval = 10
    # We can't switch the driver on the fly, so trigger a restart if it changed.
    # self.useftd2xx is a cached copy of self.settings.useftd2xx
    if self.settings.useftd2xx != self.useftd2xx: self.async_restart()
    # Push our settings down to our children
    fields = ["takeover", "uploadfirmware", "firmware", "initialspeed", "maximumspeed", "tempwarning", "tempcritical",
              "invalidwarning", "invalidcritical", "speedupthreshold", "jobinterval", "pollinterval"]
    for child in self.children:
      for field in fields: child.settings[field] = self.settings[field]
      child.apply_settings()
    # Rescan the bus immediately to apply the new settings
    with self.wakeup: self.wakeup.notify()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.useftd2xx = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500HotplugWorker, self)._start()
    # Cache the driver, as we don't like that to change on the fly
    self.useftd2xx = self.settings.useftd2xx
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
    super(X6500HotplugWorker, self)._stop()
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
    
      if self.useftd2xx: import d2xx
      if not self.useftd2xx or self.settings.takeover: import usb

      try:
        boards = {}
        if self.useftd2xx:
          devices = d2xx.listDevices()
          for devicenum, serial in enumerate(devices):
            try:
              handle = d2xx.open(devicenum)
              handle.close()
              available = True
            except: availabale = False
            boards[serial] = available
        else:
          for bus in usb.busses():
            for dev in bus.devices:
              if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                try:
                  handle = dev.open()
                  manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                  product = handle.getString(dev.iProduct, 100).decode("latin1")
                  serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                  if (manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner"):
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
                  if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                    handle = dev.open()
                    manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                    product = handle.getString(dev.iProduct, 100).decode("latin1")
                    _serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                    if ((manufacturer == "FTDI" and product == "FT232R USB UART") or (manufacturer == "FPGA Mining LLC" and product == "X6500 FPGA Miner")) and _serial == serial:
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
            child = X6500Worker(self.core)
            child.settings.name = "X6500 board " + serial
            child.settings.serial = serial
            fields = ["takeover", "useftd2xx", "uploadfirmware", "firmware", "initialspeed", "maximumspeed", "tempwarning",
                      "tempcritical", "invalidwarning", "invalidcritical", "speedupthreshold", "jobinterval", "pollinterval"]
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
