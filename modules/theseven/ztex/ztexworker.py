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



#########################################
# ZTEX USB FPGA Module interface module #
#########################################



import time
import traceback
from multiprocessing import Pipe
from threading import RLock, Condition, Thread
from core.baseworker import BaseWorker
from .boardproxy import ZtexBoardProxy
try: from queue import Queue
except: from Queue import Queue



# Worker main class, referenced from __init__.py
class ZtexWorker(BaseWorker):
  
  version = "theseven.ztex worker v0.1.0beta"
  default_name = "Untitled ZTEX worker"
  settings = dict(BaseWorker.settings, **{
    "serial": {"title": "Board serial number", "type": "string", "position": 1000},
    "takeover": {"title": "Reset board if it appears to be in use", "type": "boolean", "position": 1200},
    "firmware": {"title": "Firmware base path", "type": "string", "position": 1400},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 4100},
    "pollinterval": {"title": "Poll interval", "type": "float", "position": 4200},
  })
  
  
  # Constructor, gets passed a reference to the miner core and the saved worker state, if present
  def __init__(self, core, state = None):
    # Let our superclass do some basic initialization and restore the state if neccessary
    super(ZtexWorker, self).__init__(core, state)

    # Initialize proxy access locks and wakeup event
    self.lock = RLock()
    self.transactionlock = RLock()
    self.wakeup = Condition()
    self.workloopwakeup = Condition()

    
  # Validate settings, filling them with default values if neccessary.
  # Called from the constructor and after every settings change.
  def apply_settings(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self).apply_settings()
    if not "serial" in self.settings: self.settings.serial = None
    if not "takeover" in self.settings: self.settings.takeover = False
    if not "firmware" in self.settings or not self.settings.firmware:
      self.settings.firmware = "modules/fpgamining/x6500/firmware/x6500.bit"
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if not "pollinterval" in self.settings or not self.settings.pollinterval: self.settings.pollinterval = 0.1
    # We can't switch the device on the fly, so trigger a restart if they changed.
    # self.serial is a cached copy of self.settings.serial.
    if self.started and self.settings.serial != self.serial: self.async_restart()
    # We need to inform the proxy about a poll interval change
    if self.started and self.settings.pollinterval != self.pollinterval: self._notify_poll_interval_changed()
    

  # Reset our state. Called both from the constructor and from self.start().
  def _reset(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._reset()
    # These need to be set here in order to make the equality check in apply_settings() happy,
    # when it is run before starting the module for the first time. (It is called from the constructor.)
    self.serial = None
    self.pollinterval = None
    self.stats.mhps = 0
    self.stats.errorrate = 0


  # Start up the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _start(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._start()
    # Cache the port number and baud rate, as we don't like those to change on the fly
    self.serial = self.settings.serial
    # Reset the shutdown flag for our threads
    self.shutdown = False
    # Start up the main thread, which handles pushing work to the device.
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  # Stut down the worker module. This is protected against multiple calls and concurrency by a wrapper.
  def _stop(self):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._stop()
    # Set the shutdown flag for our threads, making them terminate ASAP.
    self.shutdown = True
    # Trigger the main thread's wakeup flag, to make it actually look at the shutdown flag.
    with self.wakeup: self.wakeup.notify()
    # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
    try: self._proxy_message("ping")
    except: pass
    # Wait for the main thread to terminate, which in turn kills the child workers.
    self.mainthread.join(10)

      
  # Report custom statistics.
  def _get_statistics(self, stats, childstats):
    # Let our superclass handle everything that isn't specific to this worker module
    super(ZtexWorker, self)._get_statistics(stats, childstats)
    stats.errorrate = self.stats.errorrate


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
        self.dead = False
        
        # Check if we have a device serial number
        if not self.serial: raise Exception("Device serial number not set!")
        
        # Try to start the board proxy
        proxy_rxconn, self.txconn = Pipe(False)
        self.rxconn, proxy_txconn = Pipe(False)
        self.pollinterval = self.settings.pollinterval
        self.proxy = ZtexBoardProxy(proxy_rxconn, proxy_txconn, self.serial,
                                    self.settings.takeover, self.settings.firmware, self.pollinterval)
        self.proxy.daemon = True
        self.proxy.start()
        proxy_txconn.close()
        self.response = None
        self.response_queue = Queue()
        
        # Tell the board proxy to connect to the board
        self._proxy_message("connect")
        
        while not self.shutdown:
          data = self.rxconn.recv()
          if self.dead: break
          if data[0] == "log": self.core.log(self, "Proxy: %s" % data[1], data[2], data[3])
          elif data[0] == "ping": self._proxy_message("pong")
          elif data[0] == "pong": pass
          elif data[0] == "dying": raise Exception("Proxy died!")
          elif data[0] == "response": self.response_queue.put(data[1:])
          elif data[0] == "started_up": self._notify_proxy_started_up(*data[1:])
          elif data[0] == "nonce_found": self._notify_nonce_found(*data[1:])
          elif data[0] == "speed_changed": self._notify_speed_changed(*data[1:])
          elif data[0] == "error_rate": self._notify_error_rate(*data[1:])
          elif data[0] == "keyspace_exhausted": self._notify_keyspace_exhausted(*data[1:])
          else: raise Exception("Proxy sent unknown message: %s" % str(data))
        
        
      # If something went wrong...
      except Exception as e:
        # ...complain about it!
        self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
      finally:
        with self.workloopwakeup: self.workloopwakeup.notify()
        try:
          for i in range(100): self.response_queue.put(None)
        except: pass
        try: self.workloopthread.join(2)
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
    
    
  def _notify_proxy_started_up(self):
    # Assume a default job interval to make the core start fetching work for us.
    # The actual hashrate will be measured (and this adjusted to the correct value) later.
    self.jobs_per_second = 1. / self.settings.jobinterval
    # This worker will only ever process one job at once. The work fetcher needs this information
    # to estimate how many jobs might be required at once in the worst case (after a block was found).
    self.parallel_jobs = 1
    # Start up the work loop thread, which handles pushing work to the device.
    self.workloopthread = Thread(None, self._workloop, self.settings.name + "_workloop")
    self.workloopthread.daemon = True
    self.workloopthread.start()

    
  def _notify_nonce_found(self, now, nonce):
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


  def _notify_speed_changed(self, speed):
    self.stats.mhps = speed / 1000000.
    self.core.event(350, self, "speed", self.stats.mhps * 1000, "%f MH/s" % self.stats.mhps, worker = self)
    self.core.log(self, "Running at %f MH/s\n" % self.stats.mhps, 300, "B")
    # Calculate the time that the device will need to process 2**32 nonces.
    # This is limited at 60 seconds in order to have some regular communication,
    # even with very slow devices (and e.g. detect if the device was unplugged).
    interval = min(60, 2**32 / speed)
    # Add some safety margin and take user's interval setting (if present) into account.
    self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
    self.core.log(self, "Job interval: %f seconds\n" % self.jobinterval, 400, "B")
    # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
    self.jobs_per_second = 1. / self.jobinterval
    self.core.notify_speed_changed(self)

      
  def _notify_error_rate(self, rate):
    self.stats.errorrate = rate

      
  def _notify_keyspace_exhausted(self):
    with self.workloopwakeup: self.workloopwakeup.notify()
    self.core.log(self, "Exhausted keyspace!\n", 200, "y")

      
  def _send_job(self, job):
    return self._proxy_transaction("send_job", job.data, job.midstate)


  # This function should interrupt processing of the specified job if possible.
  # This is necesary to avoid producing stale shares after a new block was found,
  # or if a job expires for some other reason. If we don't know about the job, just ignore it.
  # Never attempts to fetch a new job in here, always do that asynchronously!
  # This needs to be very lightweight and fast. We don't care whether it's a
  # graceful cancellation for this module because the work upload overhead is low. 
  def notify_canceled(self, job, graceful):
    # Acquire the wakeup lock to make sure that nobody modifies job/nextjob while we're looking at them.
    with self.workloopwakeup:
      # If the currently being processed, or currently being uploaded job are affected,
      # wake up the main thread so that it can request and upload a new job immediately.
      if self.job == job: self.workloopwakeup.notify()

        
  # Main thread entry point
  # This thread is responsible for fetching work and pushing it to the device.
  def _workloop(self):
    try:
      # Job that the device is currently working on, or that is currently being uploaded.
      # This variable is used by BaseWorker to figure out the current work source for statistics.
      self.job = None
      # Job that was previously being procesed. Has been destroyed, but there might be some late nonces.
      self.oldjob = None

      # We keep control of the wakeup lock at all times unless we're sleeping
      self.workloopwakeup.acquire()
      # Eat up leftover wakeups
      self.workloopwakeup.wait(0)

      # Main loop, continues until something goes wrong or we're shutting down.
      while not self.shutdown:

        # Fetch a job, add 2 seconds safety margin to the requested minimum expiration time.
        # Blocks until one is available. Because of this we need to release the
        # wakeup lock temporarily in order to avoid possible deadlocks.
        self.workloopwakeup.release()
        job = self.core.get_job(self, self.jobinterval + 2)
        self.workloopwakeup.acquire()
        
        # If a new block was found while we were fetching that job, just discard it and get a new one.
        if job.canceled:
          job.destroy()
          continue

        # Upload the job to the device
        self._sendjob(job)
        
        # If the job was already caught by a long poll while we were uploading it,
        # jump back to the beginning of the main loop in order to immediately fetch new work.
        if self.job.canceled: continue
        # Wait while the device is processing the job. If nonces are sent by the device, they
        # will be processed by the listener thread. If the job gets canceled, we will be woken up.
        self.workloopwakeup.wait(self.jobinterval)

    # If something went wrong...
    except Exception as e:
      # ...complain about it!
      self.core.log(self, "%s\n" % traceback.format_exc(), 100, "rB")
    finally:
      # We're not doing productive work any more, update stats and destroy current job
      self._jobend()
      self.stats.mhps = 0
      # Make the proxy and its listener thread restart
      self.dead = True
      try: self.workloopwakeup.release()
      except: pass
      # Ping the proxy, otherwise the main thread might be blocked and can't wake up.
      try: self._proxy_message("ping")
      except: pass
      

  # This function uploads a job to the device
  def _sendjob(self, job):
    # Move previous job to oldjob, and new one to job
    self.oldjob = self.job
    self.job = job
    # Send it to the FPGA
    start, now = self._send_job(job)
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
