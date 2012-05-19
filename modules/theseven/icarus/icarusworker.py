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



##################################
# Icarus worker interface module #
##################################



import serial
import time
import struct
import traceback
from threading import Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.job import ValidationJob



# Worker main class, referenced from __init__.py
class IcarusWorker(BaseWorker):
  
  version = "theseven.icarus worker v0.1.0beta"
  default_name = "Untitled Icarus worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(IcarusWorker, self).__init__(core, state)

    # Initialize wakeup flag for the main thread.
    # This serves as a lock at the same time.
    self.wakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self).apply_settings()
    # Pretty much self-explanatory...
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyUSB0"
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    # We can't change the port name or baud rate on the fly, so trigger a restart if they changed.
    # self.port/self.baudrate are cached copys of self.settings.port/self.settings.baudrate
    if self.started and self.settings.port != self.port or self.settings.baudrate != self.baudrate: self.async_restart()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.port = None
    self.baudrate = None
#    # Initialize custom statistics. This is not neccessary for this worker module,
#    # but might be interesting for other modules, so it is kept here for reference.
#    self.stats.field1 = 0
#    self.stats.field2 = 0
#    self.stats.field3 = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(IcarusWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.port = self.settings.port
    self.baudrate = self.settings.baudrate
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
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
    super(IcarusWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # The listener thread will hopefully die because the main thread closes the serial port handle.
    # Wait for the main thread to terminate, which in turn waits for the listener thread to die.
    self.mainthread.join(10)

      
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

        
#  # Report custom statistics. This is not neccessary for this worker module,
#  # but might be interesting for other modules, so it is kept here for reference.
#  def _get_statistics(self, stats, childstats):
#    # Let our superclass handle everything that isn't specific to this worker module
#    super(IcarusWorker, self)._get_statistics(stats, childstats)
#    stats.field1 = self.stats.field1
#    stats.field2 = self.stats.field2 + childstats.calculatefieldsum("field2")
#    stats.field3 = self.stats.field3 + childstats.calculatefieldavg("field3")
        
        
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
        # Exception container: If an exception occurs in the listener thread, the listener thread
        # will store it here and terminate, and the main thread will rethrow it and then restart.
        self.error = None
        self.hasheswithoutshare = 0

        # Initialize megahashes per second to zero, will be measured later.
        self.stats.mhps = 0

        # Job that the device is currently working on, or that is currently being uploaded.
        # This variable is used by BaseWorker to figure out the current work source for statistics.
        self.job = None
        # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
        self.oldjob = None

        # Open the serial port
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, 5, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Start device response listener thread
        self.listenerthread = Thread(None, self._listener, self.settings.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Send validation job to device
        job = ValidationJob(self.core, unhexlify(b"00000001c3bf95208a646ee98a58cf97c3a0c4b7bf5de4c89ca04495000005200000000024d1fff8d5d73ae11140e4e48032cd88ee01d48c67147f9a09cd41fdec2e25824f5c038d1a0b350c5eb01f04"))
        self._sendjob(job)

        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 60 seconds should be sufficient for devices
        # down to about 2.6MH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(60)
        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error
        # Honor shutdown flag
        if self.shutdown: break
        # We woke up, but the validation job hasn't succeeded in the mean time.
        # This usually means that the wakeup timeout has expired.
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        # self.stats.mhps has now been populated by the listener thread
        self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
        # Calculate the time that the device will need to process 2**32 nonces.
        # This is limited at 60 seconds in order to have some regular communication,
        # even with very slow devices (and e.g. detect if the device was unplugged).
        interval = min(60, 2**32 / 1000000. / self.stats.mhps)
        # Add some safety margin and take user's interval setting (if present) into account.
        self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
        self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.jobspersecond = 1. / self.jobinterval
        self.core.notify_speed_changed(self)

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

          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

          # Upload the job to the device
          self._sendjob(job)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error
          # If the job was already caught by a long poll while we were uploading it,
          # jump back to the beginning of the main loop in order to immediately fetch new work.
          # Don't check for the canceled flag before the job was accepted by the device,
          # otherwise we might get out of sync.
          if self.job.canceled: continue
          # Wait while the device is processing the job. If nonces are sent by the device, they
          # will be processed by the listener thread. If the job gets canceled, we will be woken up.
          self.wakeup.wait(self.jobinterval)
          # If an exception occurred in the listener thread, rethrow it
          if self.error != None: raise self.error

      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
        # Make sure that the listener thread realizes that something went wrong
        self.error = e
      finally:
        # We're not doing productive work any more, update stats and destroy current job
        self._jobend()
        self.stats.mhps = 0
        # Release the wake lock to allow the listener thread to move. Ignore it if that goes wrong.
        try: self.wakeup.release()
        except: pass
        # Close the serial port handle, otherwise we can't reopen it after restarting.
        # This should hopefully also make reads on that port from the listener thread fail,
        # so that the listener thread will realize that it's supposed to shut down.
        try: self.handle.close()
        except: pass
        # Wait for the listener thread to terminate.
        # If it doens't within 5 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(5)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.stats.mhps = 0
        # If we aren't shutting down, figure out if there have been many errors recently,
        # and if yes, wait a bit longer until restarting the worker.
        if not self.shutdown:
          tries += 1
          if time.time() - starttime >= 300: tries = 0
          with self.wakeup:
            if tries > 5: self.wakeup.wait(30)
            else: self.wakeup.wait(1)
        # Restart (handled by "while not self.shutdown:" loop above)


  # Device response listener thread
  def _listener(self):
    # Catch all exceptions and forward them to the main thread
    try:
      # Loop forever unless something goes wrong
      while True:
        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break
        
        # If there were suspiciously many hashes without even a single share,
        # assume that PL2303 did it's job (i.e. serial port locked up),
        # and restart the board worker.
        if self.hasheswithoutshare > 16 * 2**32:
          raise Exception("Watchdog triggered: %.6f MHashes without share" % (self.hasheswithoutshare / 1000000.))

        # Try to read a response from the device
        nonce = self.handle.read(4)
        # If no response was available, retry
        if len(nonce) != 4: continue
        nonce = nonce[::-1]
        # Snapshot the current jobs to avoid race conditions
        newjob = self.job
        oldjob = self.oldjob
        # If there is no job, this must be a leftover from somewhere, e.g. previous invocation
        # or reiterating the keyspace because we couldn't provide new work fast enough.
        # In both cases we can't make any use of that nonce, so just discard it.
        if not oldjob and not newjob: return
        # Stop time measurement
        now = time.time()
        self.hasheswithoutshare = 0
        # Pass the nonce that we found to the work source, if there is one.
        # Do this before calculating the hash rate as it is latency critical.
        job = None
        if newjob:
          if newjob.nonce_found(nonce, oldjob): job = newjob
        if not job and oldjob:
          if oldjob.nonce_found(nonce): job = oldjob
        # If the nonce is too low, the measurement may be inaccurate.
        nonceval = struct.unpack("<I", nonce)[0] & 0x7fffffff
        if job and job.starttime and nonceval >= 0x04000000:
          # Calculate actual on-device processing time (not including transfer times) of the job.
          delta = (now - job.starttime) - 40. / self.baudrate
          # Calculate the hash rate based on the processing time and number of neccessary MHashes.
          # This assumes that the device processes all nonces (starting at zero) sequentially.
          self.stats.mhps = nonceval / 500000. / delta
          self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
        # This needs self.stats.mhps to be set.
        if isinstance(newjob, ValidationJob):
          # This is a validation job. Validate that the nonce is correct, and complain if not.
          if newjob.nonce != nonce:
            raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(newjob.nonce).decode("ascii")))
          else:
            # The nonce was correct. Wake up the main thread.
            with self.wakeup:
              self.checksuccess = True
              self.wakeup.notify()
        else:
          with self.wakeup:
            self._jobend(now)
            self.wakeup.notify()

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...complain about it...
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.


  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the device
    now = time.time()
    self.handle.write(job.midstate[::-1] + b"\0" * 20 + job.data[75:63:-1])
    self.handle.flush()
    self.job.starttime = time.time()
    # Calculate how long the old job was running
    if self.oldjob and self.oldjob.starttime:
      if self.oldjob.starttime:
        hashes = (now - self.oldjob.starttime) * self.stats.mhps * 1000000
        self.hasheswithoutshare += hashes
        self.oldjob.hashes_processed(hashes)
      self.oldjob.destroy()

    
  # This function needs to be called whenever the device terminates working on a job.
  # It calculates how much work was actually done for the job and destroys it.
  def _jobend(self, now = None):
    # Hack to avoid a python bug, don't integrate this into the line above
    if not now: now = time.time()
    # Calculate how long the job was actually running and multiply that by the hash
    # rate to get the number of hashes calculated for that job and update statistics.
    if self.job:
      if self.job.starttime:
        hashes = (now - self.job.starttime) * self.stats.mhps * 1000000
        self.hasheswithoutshare += hashes
        self.job.hashes_processed(hashes)
      # Destroy the job, which is neccessary to actually account the calculated amount
      # of work to the worker and work source, and to remove the job from cancelation lists.
      self.oldjob = self.job
      self.job.destroy()
      self.job = None
