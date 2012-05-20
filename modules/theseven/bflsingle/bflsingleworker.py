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



###############################################################
# Butterfly Labs Inc. BitFORCE Single worker interface module #
###############################################################



import os
import serial
import time
import traceback
from threading import Condition, Thread
from binascii import unhexlify
from core.baseworker import BaseWorker



# Worker main class, referenced from __init__.py
class BFLSingleWorker(BaseWorker):
  
  version = "theseven.bflsingle worker v0.1.0beta"
  default_name = "Untitled BFL Single worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(BFLSingleWorker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyUSB0"
    # We can't change the port name on the fly, so trigger a restart if they changed.
    # self.port is a cached copy of self.settings.port.
    if self.started and self.settings.port != self.port: self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.stats.temperature = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobinterval = 2**32 / 800000000.
    self.jobs_per_second = 1 / self.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Shut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Wait for the main thread to terminate.
    self.mainthread.join(10)

      
  # This function should interrupt processing of the specified job if possible.
  # This is neccesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. Canceling a job is very expensive
  # for this module due to bad firmware design, so completely ignore graceful cancellation.
  def notify_canceled(self, job, graceful):
    if graceful: return
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.wakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.wakeup.notify()

        
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(BFLSingleWorker, self)._get_statistics(stats, childstats)
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

        # Open the serial port
        self.handle = serial.Serial(self.port, 115200, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        
        self.handle.write(b"ZGX")
        response = self.handle.readline()
        if response[:31] != b">>>ID: BitFORCE SHA256 Version " or response[-4:] != b">>>\n":
          raise Exception("Bad ZGX response: %s\n" % response.decode("ascii", "replace").strip())
        self.core.log(self, "Firmware: %s\n" % (response[7:-4].decode("ascii", "replace")), 400, "B")

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

          self._jobend()
          self.job = job
          self.handle.write(b"ZDX")
          response = self.handle.readline()
          if response != b"OK\n": raise Exception("Bad ZDX response: %s\n" % response.decode("ascii", "replace").strip())
          if self.shutdown: break
          self.handle.write(b">>>>>>>>" + job.midstate + job.data[64:76] + b">>>>>>>>")
          response = self.handle.readline()
          if response != b"OK\n": raise Exception("Bad job response: %s\n" % response.decode("ascii", "replace").strip())
          if self.shutdown: break

          # If a new block was found while we were sending that job, just discard it and get a new one.
          if job.canceled:
            self.job = None
            job.destroy()
            continue

          self.job.starttime = time.time()
          
          # Read device temperature
          self.handle.write(b"ZLX")
          response = self.handle.readline()
          if response[:23] != b"Temperature (celcius): " or response[-1:] != b"\n":
            raise Exception("Bad ZLX response: %s\n" % response.decode("ascii", "replace").strip())
          self.stats.temperature = float(response[23:-1])
          self.core.event(350, self, "temperature", self.stats.temperature * 1000, "%f \xc2\xb0C" % self.stats.temperature, worker = self)
          if self.shutdown: break

          # Wait while the device is processing the job. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          if self.shutdown: break
          
          # Poll the device for job results
          while True:
            now = time.time()
            if self.job.canceled: break
            self.handle.write(b"ZFX")
            response = self.handle.readline()
            if self.shutdown: break
            if response == b"BUSY\n": continue
            if response == b"NO-NONCE\n": break
            if response[:12] != "NONCE-FOUND:" or response[-1:] != "\n":
              raise Exception("Bad ZFX response: %s\n" % response.decode("ascii", "replace").strip())
            nonces = response[12:-1]
            while nonces:
              self.job.nonce_found(unhexlify(nonces[:8])[::-1])
              if len(nonces) != 8 and nonces[8] != b",":
                raise Exception("Bad ZFX response: %s\n" % response.decode("ascii", "replace").strip())
              nonces = nonces[9:]
            break
          if not self.job.canceled:
            delta = now - self.job.starttime
            self.stats.mhps = 2**32 / delta / 1000000.
            self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
            self.jobinterval = delta - 0.2
            self.jobspersecond = 1. / self.jobinterval
            self.core.notify_speed_changed(self)
          self._jobend(now)

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        try: self.handle.close()
        except: pass
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job:
      if self.job.starttime:
        self.job.hashes_processed((now - self.job.starttime) * self.stats.mhps * 1000000)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.job.destroy()
      self.job = None
