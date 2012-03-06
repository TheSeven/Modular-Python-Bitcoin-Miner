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


###########################################################
# FPGA Mining LLC X6500 FPGA Miner Board interface module #
###########################################################

# Module configuration options:
#   name: Display name for this work source (default: "X6500 board " device id)
#   deviceid: Serial number of the device to be used (default: take first available device)
#   firmware: Path to the firmware file (default: "worker/fpgamining/firmware/x6500.bit")
#   jobinterval: New work is sent to the device at least every that many seconds (default: 30)
#   pollinterval: Nonce poll interval in seconds (default: 0.1)
#   useftd2xx: Use FTDI D2XX driver instead direct access via PyUSB (default: false)
#   takeover: Forcibly grab control over the USB device (default: false, not supported by D2XX)
#   uploadfirmware: Upload FPGA firmware during startup (default: false)


import sys
import common
import binascii
import threading
import time
import hashlib
import struct
import atexit
from .util.ft232r import FT232R, FT232R_PyUSB, FT232R_D2XX, FT232R_PortList
from .util.jtag import JTAG
from .util.BitstreamReader import BitFile, BitFileReadError
from .util.fpga import FPGA
from .util.format import formatNumber, formatTime


# Worker main class, referenced from config.py
class X6500Worker(object):

  # Constructor, gets passed a reference to the miner core and the config dict for this worker
  def __init__(self, miner, dict, hotplug = False):

    # Make config dict entries accessible via self.foo
    self.__dict__ = dict

    # Store reference to the miner core object
    self.miner = miner

    # Initialize child array
    self.children = []

    # Validate arguments, filling them with default values if not present
    self.hotplug = hotplug
    self.dead = False
    nameattr = getattr(self, "name", None)
    self.name = nameattr
    self.deviceid = getattr(self, "deviceid", "")
    if nameattr == None: self.name = "X6500 board " + self.deviceid if self.deviceid != "" else "X6500 driver"
    self.useftd2xx = getattr(self, "useftd2xx", False)
    self.takeover = getattr(self, "takeover", False)
    self.uploadfirmware = getattr(self, "uploadfirmware", False)
    try:
      if self.useftd2xx: self.device = FT232R(self.miner, self, FT232R_D2XX(self.deviceid))
      else: self.device = FT232R(self.miner, self, FT232R_PyUSB(self.deviceid, self.takeover))
    except Exception as e:
      self.device = None
      self.miner.log(self.name + ": %s\n" % e, "rB")
    if self.device != None: self.deviceid = self.device.serial
    if nameattr == None: self.name = "X6500 board " + self.deviceid if self.deviceid != "" else "X6500 driver"
    if self.device == None:
      self.name = self.name + " (disconnected)"
      self.dead = True
    self.firmware = getattr(self, "firmware", "worker/fpgamining/firmware/x6500.bit")
    self.jobinterval = getattr(self, "jobinterval", 30)
    self.pollinterval = getattr(self, "pollinterval", 0.1)
    self.jobspersecond = 0  # Used by work buffering algorithm, we don't ever process jobs ourself

    # Initialize object properties (for statistics)
    # Only children that have died are counted here, the others will report statistics themselves
    self.mhps = 0          # Current MH/s (always zero)
    self.mhashes = 0       # Total megahashes calculated since startup
    self.jobsaccepted = 0  # Total jobs accepted
    self.accepted = 0      # Number of accepted shares produced by this worker * difficulty
    self.rejected = 0      # Number of rejected shares produced by this worker * difficulty
    self.invalid = 0       # Number of invalid shares produced by this worker
    self.starttime = time.time()  # Start timestamp (to get average MH/s from MHashes)

    # Statistics lock, ensures that the UI can get a consistent statistics state
    # Needs to be acquired during all operations that affect the above values
    self.statlock = threading.RLock()

    if self.device != None:
      # Start main thread (boots the board and spawns FPGA manager threads)
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
        "currentpool": "Not applicable", \
      }
    # Return result
    return statistics

    
  # This function should interrupt processing of the current piece of work if possible.
  # If you can't, you'll likely get higher stale share rates.
  # This function is usually called when the work source gets a long poll response.
  # If we're currently doing work for a different blockchain, we don't need to care.
  def cancel(self, blockchain):
    # Check all running children
    for child in self.children:
      # Forward the request to the child
      child.cancel(blockchain)


  # Firmware upload progess indicator
  def progresshandler(self, start_time, now_time, written, total):
    try: percent_complete = 100. * written / total
    except ZeroDivisionError: percent_complete = 0
    try: speed = written / (1000 * (now_time - start_time))
    except ZeroDivisionError: speed = 0
    try: remaining_sec = 100 * (now_time - start_time) / percent_complete
    except ZeroDivisionError: remaining_sec = 0
    remaining_sec -= now_time - start_time
    self.miner.log(self.name + ": %.1f%% complete [%sB/s] [%s remaining]\n" % (percent_complete, formatNumber(speed), formatTime(remaining_sec)))
  

  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):

    try:
      fpga_list = [FPGA(self.miner, self.name + " FPGA 0", self.device, 0), FPGA(self.miner, self.name + " FPGA 1", self.device, 1)]
      channelmask = 0
      fpgacount = 0
      
      for id, fpga in enumerate(fpga_list):
        fpga.id = id
        self.miner.log(self.name + ": Discovering FPGA %d...\n" % id)
        fpga.jtag.detect()
        #self.miner.log(self.name + ": Found %i device%s\n" % (fpga.jtag.deviceCount, 's' if fpga.jtag.deviceCount != 1 else ''))
        for idcode in fpga.jtag.idcodes:
          self.miner.log(self.name + ": FPGA %d: %s\n" % (id, JTAG.decodeIdcode(idcode)))
        if fpga.jtag.deviceCount != 1:
          self.miner.log(self.name + ": Warning: This module needs two JTAG buses with one FPGA each!\n", "rB")
          self.dead = True
          return

      if self.uploadfirmware:
        self.miner.log(self.name + ": Programming FPGAs...\n")
        start_time = time.time()
        try:
          bitfile = BitFile.read(self.firmware)
        except BitFileReadError as e:
          self.miner.log(self.name + ": Error while reading firmware: %s\n" % e, "rB")
          self.dead = True
          return
        self.miner.log(self.name + ": Firmware file details:\n", "B")
        self.miner.log(self.name + ":   Design Name: %s\n" % bitfile.designname)
        self.miner.log(self.name + ":   Part Name: %s\n" % bitfile.part)
        self.miner.log(self.name + ":   Date: %s\n" % bitfile.date)
        self.miner.log(self.name + ":   Time: %s\n" % bitfile.time)
        self.miner.log(self.name + ":   Bitstream Length: %d\n" % len(bitfile.bitstream))
        jtag = JTAG(self.miner, self.name, self.device, 2)
        jtag.deviceCount = 1
        jtag.idcodes = [bitfile.idcode]
        jtag._processIdcodes()
        for fpga in fpga_list:
          for idcode in fpga.jtag.idcodes:
            if idcode & 0x0FFFFFFF != bitfile.idcode:
              self.miner.log(self.name + ": Device IDCode does not match bitfile IDCode! Was this bitstream built for this FPGA?\n", "r")
              self.dead = True
              return
        FPGA.programBitstream(self.miner, self.device, jtag, bitfile.bitstream, self.progresshandler)
        self.miner.log(self.name + ": Programmed FPGAs in %f seconds\n" % (time.time() - start_time))
        bitfile = None  # Free memory
      
      self.children.append(X6500FPGA(self.miner, self, fpga_list[0]))
      self.children.append(X6500FPGA(self.miner, self, fpga_list[1]))
    except Exception as e:
      import traceback
      self.miner.log(self.name + ": Error while booting board: %s\n" % traceback.format_exc(), "rB")
      self.dead = True
    
    # Read FPGA temperatures every second   
    try:    
      while True:
        time.sleep(3)
        (temp0, temp1) = self.device.read_temps()
        self.children[0].temperature = temp0
        self.children[1].temperature = temp1
    except Exception as e:
      self.miner.log(self.name + ": Reading FPGA temperatures failed: %s\n" % e, "y")
        
        
# FPGA handler main class, child worker of X6500Worker
class X6500FPGA(object):

  # Constructor, gets passed a reference to the miner core, parent worker, FPGA object
  def __init__(self, miner, parent, fpga):

    # Store reference to the miner core, parent worker and FPGA objects
    self.miner = miner
    self.parent = parent
    self.fpga = fpga
    
    # Fetch config information
    self.name = fpga.name
    self.jobinterval = parent.jobinterval
    self.pollinterval = parent.pollinterval
    self.jobspersecond = 0  # Used by work buffering algorithm, we don't ever process jobs ourself
    
    # Initialize child array (we won't ever have any)
    self.children = []

    # Initialize object properties (for statistics)
    self.mhps = 0          # Current MH/s
    self.mhashes = 0       # Total megahashes calculated since startup
    self.jobsaccepted = 0  # Total jobs accepted
    self.accepted = 0      # Number of accepted shares produced by this worker * difficulty
    self.rejected = 0      # Number of rejected shares produced by this worker * difficulty
    self.invalid = 0       # Number of invalid shares produced by this worker
    self.starttime = time.time()  # Start timestamp (to get average MH/s from MHashes)
    self.temperature = None

    # Statistics lock, ensures that the UI can get a consistent statistics state
    # Needs to be acquired during all operations that affect the above values
    self.statlock = threading.RLock()

    # Placeholder for device response listener thread (will be started after synchronization)
    self.listenerthread = None

    # Initialize wakeup flag for the main thread
    self.wakeup = threading.Condition()

    # Start main thread (fetches work and pushes it to the device)
    self.mainthread = threading.Thread(None, self.main, self.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()


  # Report statistics about this worker module and its (non-existant) children.
  def getstatistics(self, childstats):
    # Acquire the statistics lock to stop statistics from changing while we deal with them
    with self.statlock:
      # Calculate statistics
      statistics = { \
        "name": self.name, \
        "children": childstats, \
        "mhashes": self.mhashes, \
        "mhps": self.mhps, \
        "jobsaccepted": self.jobsaccepted, \
        "accepted": self.accepted, \
        "rejected": self.rejected, \
        "invalid": self.invalid, \
        "starttime": self.starttime, \
        "temperature": self.temperature, \
        "currentpool": self.job.pool.name if self.job != None and self.job.pool != None else None, \
      }
    # Return result
    return statistics


  # This function should interrupt processing of the current piece of work if possible.
  # If you can't, you'll likely get higher stale share rates.
  # This function is usually called when the work source gets a long poll response.
  # If we're currently doing work for a different blockchain, we don't need to care.
  def cancel(self, blockchain):
    # Get the wake lock to ensure that nobody else can change job/nextjob while we're checking.
    with self.wakeup:
      # Signal the main thread that it should get a new job if we're currently
      # processing work for the affected blockchain.
      if self.job != None and self.job.pool != None and self.job.pool.blockchain == blockchain:
        self.canceled = True
        self.wakeup.notify()
      # Check if an affected job is currently being uploaded.
      # If yes, it will be cancelled immediately after the upload.
      elif self.nextjob != None and self.nextjob.pool != None and self.nextjob.pool.blockchain == blockchain:
        self.canceled = True
        self.wakeup.notify()


  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):

    # Make sure the FPGA is put to sleep when MPBM exits
    atexit.register(self.fpga.sleep)
    
    # Loop forever. If anything fails, restart.
    while True:
      try:
      
        # Exception container: If an exception occurs in the listener thread, the listener thread
        # will store it here and terminate, and the main thread will rethrow it and then restart.
        self.error = None

        # Initialize megahashes per second to zero, will be measured later.
        self.mhps = 0

        # Job that the device is currently working on (found nonces are coming from this one).
        self.job = None

        # Job that is currently being uploaded to the device but not yet being processed.
        self.nextjob = None

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Set validation job second iteration flag to false
        self.seconditeration = False
        # Initialize job cancellation (long poll) flag to false
        self.canceled = False
        
        # Initialize hash rate tracking data
        self.lasttime = None
        self.lastnonce = None
        
        # Clear FPGA's nonce queue
        self.fpga.clearQueue()

        # Start device response listener thread
        self.listenerthread = threading.Thread(None, self.listener, self.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Send validation job to device
        self.miner.log(self.name + ": Verifying correct operation...\n", "B")
        job = common.Job(self.miner, None, None, binascii.unhexlify(b"5517a3f06a2469f73025b60444e018e61ff2c557ea403ccf3b9c5445dd353710"), b"\0" * 64 + binascii.unhexlify(b"42490d634f2c87761a0cd43f"), None, binascii.unhexlify(b"8fa95303"))
        self.sendjob(job)

        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 180 seconds should be sufficient for devices
        # down to about 50MH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(180)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.mhps has now been populated by the listener thread
        self.miner.log(self.name + ": Running at %f MH/s\n" % self.mhps, "B")
        # Calculate the time that the device will need to process 2**32 nonces.
        # This is limited at 30 seconds so that new transactions can be included into the block
        # by the work source. (Requirement of the bitcoin protocol and enforced by most pools.)
        interval = min(30, 2**32 / 1000000. / self.mhps)
        # Add some safety margin and take user's interval setting (if present) into account.
        self.jobinterval = min(self.jobinterval, max(0.5, interval * 0.8 - 1))
        self.miner.log(self.name + ": Job interval: %f seconds\n" % self.jobinterval, "B")
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.jobspersecond = 1. / self.jobinterval
        self.miner.updatehashrate(self)

        # Main loop, continues until something goes wrong.
        while True:

          # Fetch a job. Blocks until one is available. Because of this we need to release the
          # wake lock temporarily in order to avoid possible deadlocks.
          self.canceled = False;
          self.wakeup.release()
          job = self.miner.getjob(self)
          # Doesn't need acquisition of the statlock because we're the only one who modifies this.
          self.jobsaccepted = self.jobsaccepted + 1
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job,
          # check the long poll epoch to verify that the work that we got isn't stale.
          # If it is, just discard it and get a new one.
          if self.canceled == True:
            if job.longpollepoch != job.pool.blockchain.longpollepoch: continue
          self.canceled = False;

          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

          # Upload the piece of work to the device
          self.sendjob(job)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If a long poll comes in, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.miner.log(self.name + ": %s\n" % e, "rB")
        # Make sure that the listener thread realizes that something went wrong
        self.error = e
        # We're not doing productive work any more, update stats
        self.mhps = 0
        # Release the wake lock to allow the listener thread to move. Ignore it if that goes wrong.
        try: self.wakeup.release()
        except: pass
        if self.parent.hotplug:
          for child in self.parent.children:
            child.error = Exception("Sibling FPGA worker died, restarting board")
          try: self.parent.device.close()
          except: pass
        # Wait for the listener thread to terminate.
        # If it doens't within 10 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(10)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.mhps = 0
        # Notify the hotplug manager about our death, so that it can respawn as neccessary
        if self.parent.hotplug:
          self.parent.dead = True
          return
        # Wait for a second to avoid 100% CPU load if something fails reproducibly
        time.sleep(1)
        # Restart (handled by "while True:" loop above)


  # Device response listener thread (polls for nonces)
  def listener(self):

    # Catch all exceptions and forward them to the main thread
    try:

      # Loop forever unless something goes wrong
      while True:
      
        # Wait for a poll interval
        time.sleep(self.pollinterval)

        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break

        self.checknonces()

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.

      
  def checknonces(self):
    # Try to read a nonce from the device
    nonce = self.fpga.readNonce()
    # If we found a nonce, handle it
    if nonce is not None:
      # Snapshot the current jobs to avoid race conditions
      nextjob = self.nextjob
      oldjob = self.job
      # If there is no job, this must be a leftover from somewhere.
      # In that case, just restart things to clean up the situation.
      if oldjob == None: raise Exception("Mining device sent a share before even getting a job")
      # Stop time measurement
      now = time.time()
      # Pass the nonce that we found to the work source, if there is one.
      # Do this before calculating the hash rate as it is latency critical.
      if oldjob != None:
        if nextjob != None:
          data = oldjob.data[:76] + nonce + oldjob.data[80:]
          hash = hashlib.sha256(hashlib.sha256(struct.pack("<20I", *struct.unpack(">20I", data[:80]))).digest()).digest()
          if hash[-4:] != b"\0\0\0\0": nextjob.sendresult(nonce, self)
        else: oldjob.sendresult(nonce, self)
      else: oldjob.sendresult(nonce, self)
      if oldjob.check != None:
        # This is a validation job. Validate that the nonce is correct, and complain if not.
        if oldjob.check != nonce:
          raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (binascii.hexlify(nonce).decode("ascii"), binascii.hexlify(self.job.check).decode("ascii")))
        else:
          # The nonce was correct
          if self.seconditeration == True:
            with self.wakeup:
              # This is the second iteration. We now know the actual nonce rotation time.
              delta = (now - oldjob.starttime)
              # Calculate the hash rate based on the nonce rotation time.
              self.mhps = 2**32 / 1000000. / delta
              # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
              self.miner.updatehashrate(self)
              # Update hash rate tracking information
              self.lasttime = now
              self.lastnonce = struct.unpack("<I", nonce)[0]
              # Wake up the main thread
              self.checksuccess = True
              self.wakeup.notify()
          else:
            with self.wakeup:
              # This was the first iteration. Wait for another one to figure out nonce rotation time.
              oldjob.starttime = now
              self.seconditeration = True
      else:
        # Adjust hash rate tracking
        delta = (now - self.lasttime)
        nonce = struct.unpack("<I", nonce)[0]
        estimatednonce = int(round(self.lastnonce + self.mhps * 1000000 * delta))
        noncediff = nonce - (estimatednonce & 0xffffffff)
        if noncediff < -0x80000000: noncediff = noncediff + 0x100000000
        elif noncediff > 0x7fffffff: noncediff = noncediff - 0x100000000
        estimatednonce = estimatednonce + noncediff
        # Calculate the hash rate based on adjusted tracking information
        currentmhps = (estimatednonce - self.lastnonce) / 1000000. / delta
        weight = min(0.5, delta / 100.)
        self.mhps = (1 - weight) * self.mhps + weight * currentmhps
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.miner.updatehashrate(self)
        # Update hash rate tracking information
        self.lasttime = now
        self.lastnonce = nonce
      

  # This function uploads a job to the device
  def sendjob(self, job):
    # Put it into nextjob. It will be moved to job once we know it has reached the FPGA.
    self.nextjob = job
    # Send it to the FPGA
    self.fpga.writeJob(job)
    # Try to grab any leftover nonces from the previous job in time
    self.checknonces()
    now = time.time()
    if self.job != None and self.job.starttime != None and self.job.pool != None:
      mhashes = (now - self.job.starttime) * self.mhps
      self.job.finish(mhashes, self)
      self.job.starttime = None
    # Acknowledge the job by moving it from nextjob to job
    self.job = self.nextjob
    self.job.starttime = now
    self.nextjob = None
        
