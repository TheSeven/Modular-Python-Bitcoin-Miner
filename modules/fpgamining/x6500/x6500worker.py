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



###########################################################
# FPGA Mining LLC X6500 FPGA Miner Board interface module #
###########################################################



import time
import struct
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob
from .boardproxy import X6500BoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class X6500Worker(BaseWorker):
  
  version = "fpgamining.x6500 worker v0.1.0beta"
  default_name = "Untitled X6500 worker"
  settings = dict(BaseWorker.settings, **{
    "serial": {"title": "Board serial number", "type": "string", "position": 1000},
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
    "initialspeed": {"title": "Initial clock frequency", "type": "int", "position": 2000},
    "maximumspeed": {"title": "Maximum clock frequency", "type": "int", "position": 2100},
    "tempwarning": {"title": "Warning temperature", "type": "int", "position": 3000},
    "tempcritical": {"title": "Critical temperature", "type": "int", "position": 3100},
    "invalidwarning": {"title": "Warning invalids", "type": "int", "position": 3200},
    "invalidcritical": {"title": "Critical invalids", "type": "int", "position": 3300},
    "speedupthreshold": {"title": "Speedup threshold", "type": "int", "position": 3400},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
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

    # Let our superclass do some basic initialization and restore the state if neccessary
    super(X6500Worker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "useftd2xx" in self.settings:
      self.settings.useftd2xx = self.d2xx_available and not self.pyusb_available
    if self.settings.useftd2xx == "false": self.settings.useftd2xx = False
    else: self.settings.useftd2xx = not not self.settings.useftd2xx
    if not "takeover" in self.settings: self.settings.takeover = False
    if not "uploadfirmware" in self.settings: self.settings.uploadfirmware = True
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
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
    # We can't switch the device or driver on the fly, so trigger a restart if they changed.
    # self.serial/self.useftd2xx are cached copys of self.settings.serial/self.settings.useftd2xx
    if self.settings.serial != self.serial or self.settings.useftd2xx != self.useftd2xx: self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    for child in self.children: child.apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.serial = None
    self.useftd2xx = None
    self.pollinterval = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.serial = self.settings.serial
    self.useftd2xx = self.settings.useftd2xx
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500Worker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Main thread entry point
  # This thread is responsible for booting the individual FPGAs and spawning worker threads for them
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()
        
        # Check if we have a device serial number
        if not self.serial: raise Exception("Device serial number not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = X6500BoardProxy(proxy_rxconn, proxy_txconn, self.serial, self.useftd2xx,
                                     self.settings.takeover, self.settings.uploadfirmware,
                                     self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if data[0] == "log": self.core.log("%s: Proxy: %s" % (self.settings.name, data[1]), data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "temperature_read": self._notify_temperature_read(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self.settings.name + ": %s\n" % traceback.format_exc(), 100, "rB")
      finally:
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        while self.children:
          try:
            child = self.children.pop(0)
            child.stop()
            childstats = child.get_statistics()
            fields = ["ghashes", "jobsaccepted", "jobscanceled", "sharesaccepted", "sharesrejected", "sharesinvalid"]
            for field in fields: self.stats[field] += childstats[field]
            try: self.child.destroy()
            except: pass
          except: pass
        try: self._proxy_message("shutdown")
        except: pass
        try: self.proxy.join(4)
        except: pass
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)

        
  def _proxy_message(self, *args):
    with self.lock:
      self.txconn.send(args)


  def _proxy_transaction(self, *args):
    with self.transactionlock:
      with self.lock:
        self.txconn.send(args)
      return self.response_queue.get()
      
      
  def _notify_poll_interval_changed(self):
    self.pollinterval = self.settings.pollinterval
    try: self._proxy_message("set_pollinterval", self.pollinterval)
    except: pass
    
    
  def _notify_proxy_started_up(self, fpga0version, fpga1version):
    # The proxy is up and running, start up child workers
    self.children = [X6500FPGA(self.core, self, 0, fpga0version),
                     X6500FPGA(self.core, self, 1, fpga1version)]
    for child in self.children: child.start()

    
  def _notify_nonce_found(self, fpga, now, nonce):
    if self.children and fpga < len(self.children):
      try: self.children[fpga].notify_nonce_found(now, nonce)
      except Exception as e: self.children[fpga].error = e


  def _notify_temperature_read(self, fpga0, fpga1):
    if self.children:
      self.children[0].stats.temperature = fpga0
      self.children[1].stats.temperature = fpga1

      
  def send_job(self, fpga, job):
    return self._proxy_transaction("send_job", fpga, job.midstate + job.data[64:76])


  def clear_queue(self, fpga):
    self._proxy_message("clear_queue", fpga)


  def shutdown_fpga(self, fpga):
    self._proxy_message("shutdown_fpga", fpga)


  def set_speed(self, fpga, speed):
    self._proxy_message("set_speed", fpga, speed)


  def get_speed(self, fpga):
    return self._proxy_transaction("get_speed", fpga)[0]



# FPGA handler main class, child worker of X6500Worker
class X6500FPGA(BaseWorker):

  # Constructor, gets passed a reference to the miner core, the X6500Worker,
  # its FPGA id, and the bitstream version currently running on that FPGA
  def __init__(self, core, parent, fpga, bitstreamversion):
    self.parent = parent
    self.fpga = fpga
    self.firmware_rev = bitstreamversion

    # Let our superclass do some basic initialization
    super(X6500FPGA, self).__init__(core, None)
    
    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()


    
  # Validate settings, mostly coping them from our parent
  # Called from the constructor and after every settings change on the parent.
  def apply_settings(self):
    self.settings.name = "%s FPGA%d" % (self.parent.settings.name, self.fpga)
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self).apply_settings()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._reset()
    self.stats.temperature = None
    self.stats.speed = None


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._start()
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.parent.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(2)

      
  # This function should interrupt processing of the specified job if possible.
  # This is neccesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast.
  def notify_canceled(self, job):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(X6500FPGA, self)._get_statistics(stats, childstats)
    stats.temperature = self.stats.temperature


  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def main(self):
    # If we're currently shutting down, just die. If not, loop forever,
    # to recover from possible errors caught by the huge try statement inside this loop.
    # Count how often the except for that try was hit recently. This will be reset if
    # there was no exception for at least 5 minutes since the last one.
    tries = 0
    while not self.shutdown:
      try:
        # Record our starting timestamp, in order to back off if we repeatedly die
        starttime = time.time()

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Eat up leftover wakeups
        self.wakeup.wait(0)
        # Honor shutdown flag (in case it was a real wakeup)
        if self.shutdown: break
        # Set validation success flag to false
        self.checksuccess = False
        # Set validation job second iteration flag to false
        self.seconditeration = False
        
        # Initialize hash rate tracking data
        self.lasttime = None
        self.lastnonce = None

        # Initialize malfunction tracking data
        self.recentshares = 0
        self.recentinvalid = 0

        # Configure core clock, if the bitstream supports that
        if self.firmware_rev > 0: self._set_speed(self.parent.settings.initialspeed)
        
        # Clear FPGA's nonce queue
        self.parent.clear_queue(self.fpga)

        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 180 seconds should be sufficient for devices
        # down to about 50MH/s, for slower devices this timeout will need to be increased.
        if self.stats.speed: self.wakeup.wait((2**32 / 1000000. / self.stats.speed) * 1.1)
        else: self.wakeup.wait(180)
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.stats.mhps has now been populated by the listener thread
        self.core.log(self.settings.name + ": Running at %f MH/s\n" % self.stats.mhps, 300, "B")
        self._update_job_interval()

        # Main loop, continues until something goes wrong or we're shutting down.
        while not self.shutdown:

          # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
          # Blocks until one is available. Because of this we need to release the
          # wakeup lock temporarily in order to avoid possible deadlocks.
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval + 2)
          self.wakeup.acquire()
          
          # If a new block was found while we were fetching that job, just discard it and get a new one.
          if job.canceled:
            job.destroy()
            continue

          # Upload the job to the device
          self._sendjob(job)
          
          # Go through the safety checks and reduce the clock if necessary
          self.safetycheck()
          
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self.settings.name + ": %s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, restart the parent worker as well.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5:
              self.parent.async_restart()
              return
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  def notify_nonce_found(self, now, nonce):
    # Snapshot the current jobs to avoid race conditions
    oldjob = self.oldjob
    newjob = self.job
    # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
    # or reiterating the keyspace because we couldn't provide new work fast enough.
    # In both cases we can't make any use of that nonce, so just discard it.
    if not oldjob and not newjob: return
    # Pass the nonce that we found to the work source, if there is one.
    # Do this before calculating the hash rate as it is latency critical.
    job = None
    if newjob:
      if newjob.nonce_found(nonce, oldjob): job = newjob
    if not job and oldjob:
      if oldjob.nonce_found(nonce): job = oldjob
    self.recentshares += 1
    if not job: self.recentinvalid += 1
    nonceval = struct.unpack("<I", nonce)[0]
    if isinstance(newjob, ValidationJob):
      # This is a validation job. Validate that the nonce is correct, and complain if not.
      if newjob.nonce != nonce:
        raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
      else:
        # The nonce was correct
        if self.firmware_rev > 0:
          # The FPGA is running overclocker firmware, so we don't need to use this method to calculate the hashrate.
          # In fact, it will not work because the FPGA will go to sleep after working through all possible nonces.
          with self.wakeup:
            self.checksuccess = True
            self.wakeup.notify()
        else:
          if self.seconditeration == True:
            with self.wakeup:
              # This is the second iteration. We now know the actual nonce rotation time.
              delta = (now - newjob.starttime)
              # Calculate the hash rate based on the nonce rotation time.
              self.stats.mhps = 2**32 / 1000000. / delta
              # Update hash rate tracking information
              self.lasttime = now
              self.lastnonce = nonceval
              # Wake up the main thread
              self.checksuccess = True
              self.wakeup.notify()
          else:
            with self.wakeup:
              # This was the first iteration. Wait for another one to figure out nonce rotation time.
              newjob.starttime = now
              self.seconditeration = True
    else:
      if self.firmware_rev == 0:
        # Adjust hash rate tracking
        delta = (now - self.lasttime)
        estimatednonce = int(round(self.lastnonce + self.stats.mhps * 1000000 * delta))
        noncediff = nonceval - (estimatednonce & 0xffffffff)
        if noncediff < -0x80000000: noncediff = noncediff + 0x100000000
        elif noncediff > 0x7fffffff: noncediff = noncediff - 0x100000000
        estimatednonce = estimatednonce + noncediff
        # Calculate the hash rate based on adjusted tracking information
        currentmhps = (estimatednonce - self.lastnonce) / 1000000. / delta
        weight = min(0.5, delta / 100.)
        self.stats.mhps = (1 - weight) * self.stats.mhps + weight * currentmhps
        # Update hash rate tracking information
        self.lasttime = now
        self.lastnonce = nonceval
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the FPGA
    start, now = self.parent.send_job(self.fpga, job)
    # Calculate how long the old job was running
    if self.oldjob:
      if self.oldjob.starttime:
        self.oldjob.hashes_processed((now - self.oldjob.starttime) * self.stats.mhps * 1000000)
      self.oldjob.destroy()
    self.job.starttime = now

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job != None:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
  
  
  # Check the invalid rate and temperature, and reduce the FPGA clock if these exceed safe values
  def safetycheck(self):
    
    warning = False
    critical = False
    if self.recentinvalid > self.parent.settings.invalidwarning: warning = True
    if self.recentinvalid > self.parent.settings.invalidcritical: critical = True
    if self.stats.temperature:
      if self.stats.temperature > self.parent.settings.tempwarning: warning = True    
      if self.stats.temperature > self.parent.settings.tempcritical: critical = True    

    if warning: self.core.log(self.settings.name + ": Detected overload condition for the FPGA!\n", 200, "y")
    if critical: self.core.log(self.settings.name + ": Detected CRITICAL condition for the FPGA!\n", 100, "rB")

    if critical: speedstep = -20
    elif warning: speedstep = -2
    elif not self.recentinvalid and self.recentshares >= self.parent.settings.speedupthreshold:
      speedstep = 2
    else: speedstep = 0    

    if self.firmware_rev > 0:
      if speedstep: self._set_speed(self.stats.speed + speedstep)
    elif warning or critical:
      self.core.log(self.settings.name + ": Firmware too old, can not automatically reduce clock!\n", 200, "yB")
      if critical:
        self.core.log(self.settings.name + ": Shutting down FPGA to protect it!\n", 100, "rB")
        self.parent.shutdown_fpga(self.fpga)
        self.async_stop(2)

    if speedstep:
      self.recentinvalid = 0
      self.recentshares = 0
    
   
  def _set_speed(self, speed):
    speed = min(max(speed, 4), self.parent.settings.maximumspeed)
    if self.stats.speed == speed: return
    self.core.log(self.settings.name + ": Setting clock speed to %d MHz...\n" % speed, 500, "B")
    self.parent.set_speed(self.fpga, speed)
    self.stats.speed = self.parent.get_speed(self.fpga)
    self.stats.mhps = self.stats.speed
    self._update_job_interval()
    if self.stats.speed != speed:
      self.core.log(self.settings.name + ": Setting clock speed failed!\n", 100, "rB")
   
   
  def _update_job_interval(self):
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / 1000000. / self.stats.mhps)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.parent.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self.settings.name + ": Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)
  