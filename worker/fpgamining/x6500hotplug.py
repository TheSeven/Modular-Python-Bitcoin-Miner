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

# Module configuration options:
#   name: Display name for this work source (default: "X6500 hotplug controller")
#   firmware: Path to the firmware file (default: "worker/fpgamining/firmware/x6500.bit")
#   jobinterval: New work is sent to the device at least every that many seconds (default: 30)
#   useftd2xx: Use FTDI D2XX driver instead direct access via PyUSB (default: false)
#   takeover: Forcibly grab control over the USB device (default: true, requires PyUSB)
#   uploadfirmware: Upload FPGA firmware during startup (default: false)
#   scaninterval: Bus scan interval in seconds (default: 10)


import sys
import time
import datetime
import threading
import worker.fpgamining.x6500


# Worker main class, referenced from config.py
class X6500HotplugWorker(object):

  # Constructor, gets passed a reference to the miner core and the config dict for this worker
  def __init__(self, miner, dict):

    # Make config dict entries accessible via self.foo
    self.__dict__ = dict

    # Store reference to the miner core object
    self.miner = miner

    # Child lock, ensures that child array modifications don't interfere with iterators
    self.childlock = threading.RLock()
    # Initialize child array
    self.children = []

    # Validate arguments, filling them with default values if not present
    self.name = getattr(self, "name", "X6500 hotplug controller")
    self.useftd2xx = getattr(self, "useftd2xx", False)
    self.takeover = getattr(self, "takeover", True)
    self.uploadfirmware = getattr(self, "uploadfirmware", False)
    self.firmware = getattr(self, "firmware", "worker/fpgamining/firmware/x6500.bit")
    self.jobinterval = getattr(self, "jobinterval", 30)
    self.scaninterval = getattr(self, "scaninterval", 10)
    self.jobspersecond = 0  # Used by work buffering algorithm, we don't ever process jobs ourself

    # Initialize object properties (for statistics)
    # Only children that have died are counted here, the others will report statistics themselves
    self.mhps = 0          # Current MH/s (always zero)
    self.mhashes = 0       # Total megahashes calculated since startup
    self.jobsaccepted = 0  # Total jobs accepted
    self.accepted = 0      # Number of accepted shares produced by this worker * difficulty
    self.rejected = 0      # Number of rejected shares produced by this worker * difficulty
    self.invalid = 0       # Number of invalid shares produced by this worker
    self.starttime = datetime.datetime.utcnow()  # Start timestamp (to get average MH/s from MHashes)

    # Statistics lock, ensures that the UI can get a consistent statistics state
    # Needs to be acquired during all operations that affect the above values
    self.statlock = threading.RLock()
    
    # Start main thread (looks for boards and spawns X6500 worker modules)
    self.mainthread = threading.Thread(None, self.main, self.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()


  # Report statistics about this worker module and its children.
  def getstatistics(self, childstats):
    # Acquire the statistics lock to stop statistics from changing while we deal with them
    with self.statlock:
      # Calculate statistics
      statistics = { \
        "name": self.name, \
        "children": childstats, \
        "mhashes": self.mhashes + self.miner.calculatefieldsum(childstats, "mhashes"), \
        "mhps": self.miner.calculatefieldsum(childstats, "mhps"), \
        "jobsaccepted": self.jobsaccepted + self.miner.calculatefieldsum(childstats, "jobsaccepted"), \
        "accepted": self.accepted + self.miner.calculatefieldsum(childstats, "accepted"), \
        "rejected": self.rejected + self.miner.calculatefieldsum(childstats, "rejected"), \
        "invalid": self.invalid + self.miner.calculatefieldsum(childstats, "invalid"), \
        "starttime": self.starttime, \
      }
    # Return result
    return statistics

    
  # This function should interrupt processing of the current piece of work if possible.
  # If you can't, you'll likely get higher stale share rates.
  # This function is usually called when the work source gets a long poll response.
  # If we're currently doing work for a different blockchain, we don't need to care.
  def cancel(self, blockchain):
    # Lock the child lock to ensure that nobody creates/deletes children while we're processing them
    with self.childlock:
      # Check all running children
      for child in self.children:
        # Forward the request to the child
        child.cancel(blockchain)


  # Main thread entry point
  # This thread is responsible for scanning for boards and spawning worker modules for them
  def main(self):

    # Handle uncaught exceptions gracefully
    sys.excepthook = self.miner.uncaughthandler

    if self.useftd2xx: import d2xx
    if not self.useftd2xx or self.takeover: import usb

    while True:
      try:
        with self.childlock:
          for child in self.children:
            if child.dead:
              with self.statlock:
                with child.childlock:
                  stats = child.getstatistics(self.miner.collectstatistics(child.children))
                self.children.remove(child)
                self.mhashes = self.mhashes + stats["mhashes"]
                self.jobsaccepted = self.jobsaccepted + stats["jobsaccepted"]
                self.accepted = self.accepted + stats["accepted"]
                self.rejected = self.rejected + stats["rejected"]
                self.invalid = self.invalid + stats["invalid"]
              
        boards = []
        if self.useftd2xx:
          devices = d2xx.listDevices()
          for devicenum, serial in enumerate(devices):
            try:
              handle = d2xx.open(devicenum)
              handle.close()
              available = True
            except: availabale = False
            boards.append((serial, available))
        else:
          for bus in usb.busses():
            for dev in bus.devices:
              if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                try:
                  handle = dev.open()
                  manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                  product = handle.getString(dev.iProduct, 100).decode("latin1")
                  serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                  if manufacturer == "FTDI" and product == "FT232R USB UART":
                    try:
                      configuration = dev.configurations[0]
                      interface = configuration.interfaces[0][0]
                      handle.setConfiguration(configuration.value)
                      handle.claimInterface(interface.interfaceNumber)
                      handle.releaseInterface()
                      handle.setConfiguration(0)
                      available = True
                    except: available = False
                    boards.append((serial, available))
                except: pass
                
        with self.childlock:
          for deviceid, available in boards:
            found = False
            for child in self.children:
              if child.deviceid == deviceid:
                found = True
                break
            if found: continue
            if not available and self.takeover:
              try:
                for bus in usb.busses():
                  if available: break
                  for dev in bus.devices:
                    if available: break
                    if dev.idVendor == 0x0403 and dev.idProduct == 0x6001:
                      handle = dev.open()
                      manufacturer = handle.getString(dev.iManufacturer, 100).decode("latin1")
                      product = handle.getString(dev.iProduct, 100).decode("latin1")
                      serial = handle.getString(dev.iSerialNumber, 100).decode("latin1")
                      if manufacturer == "FTDI" and product == "FT232R USB UART" and serial == deviceid:
                        handle.reset()
                        configuration = dev.configurations[0]
                        interface = configuration.interfaces[0][0]
                        handle.setConfiguration(configuration.value)
                        handle.claimInterface(interface.interfaceNumber)
                        handle.releaseInterface()
                        handle.setConfiguration(0)
                        handle.reset()
                        available = True
              except: pass
            if available:
              config = { \
                "deviceid": deviceid, \
                "firmware": self.firmware, \
                "jobinterval": self.jobinterval, \
                "useftd2xx": self.useftd2xx, \
                "takeover": False, \
                "uploadfirmware": self.uploadfirmware, \
              }
              self.children.append(worker.fpgamining.x6500.X6500Worker(self.miner, config, True))
              
      except Exception as e:
        self.miner.log("Caught exception: %s\n" % e, "r")
      time.sleep(self.scaninterval)
