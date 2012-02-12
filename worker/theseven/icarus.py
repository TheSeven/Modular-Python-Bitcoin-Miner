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


##################################
# Icarus worker interface module #
##################################

# Module configuration options:
#   name: Display name for this work source (default: "Icarus board on " port name)
#   port: Name (Windows) or device node (*nix) of the RS232 interface to use (default: "/dev/ttyUSBS0")
#   baudrate: Baud rate that should be used (default: 115200)
#   jobinterval: New work is sent to the device at least every that many seconds (default: 30)


import sys
import common
import serial
import binascii
import threading
import time
import struct


# Worker main class, referenced from config.py
class IcarusWorker(object):

  # Constructor, gets passed a reference to the miner core and the config dict for this worker
  def __init__(self, miner, dict):

    # Make config dict entries accessible via self.foo
    self.__dict__ = dict

    # Store reference to the miner core object
    self.miner = miner
    
    # Initialize child array (we won't ever have any)
    self.children = []

    # Validate arguments, filling them with default values if not present
    self.port = getattr(self, "port", "/dev/ttyUSBS0")
    self.baudrate = getattr(self, "baudrate", 115200)
    self.name = getattr(self, "name", "Icarus board on " + self.port)
    self.jobinterval = getattr(self, "jobinterval", 30)
    self.jobspersecond = 1. / self.jobinterval  # Used by work buffering algorithm

    # Initialize object properties (for statistics)
    self.mhps = 0          # Current MH/s
    self.mhashes = 0       # Total megahashes calculated since startup
    self.jobsaccepted = 0  # Total jobs accepted
    self.accepted = 0      # Number of accepted shares produced by this worker * difficulty
    self.rejected = 0      # Number of rejected shares produced by this worker * difficulty
    self.invalid = 0       # Number of invalid shares produced by this worker
    self.starttime = time.time()  # Start timestamp (to get average MH/s from MHashes)

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
  
    # Loop forever. If anything fails, restart threads.
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

        # Get handle for the serial port
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, None, False, None)

        # We keep control of the wakeup lock at all times unless we're sleeping
        self.wakeup.acquire()
        # Set validation success flag to false
        self.checksuccess = False
        # Initialize job cancellation (long poll) flag to false
        self.canceled = False

        # Start device response listener thread
        self.listenerthread = threading.Thread(None, self.listener, self.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()

        # Send validation job to device
        job = common.Job(self.miner, None, None, binascii.unhexlify(b"1625cbf1a5bc6ba648d1218441389e00a9dc79768a2fc6f2b79c70cf576febd0"), b"\0" * 64 + binascii.unhexlify(b"4c0afa494de837d81a269421"), None, binascii.unhexlify(b"7bc2b302"))
        self.sendjob(job)

        # If an exception occurred in the listener thread, rethrow it
        if self.error != None: raise self.error

        # Wait for the validation job to complete. The wakeup flag will be set by the listener
        # thread when the validation job completes. 60 seconds should be sufficient for devices
        # down to about 1520KH/s, for slower devices this timeout will need to be increased.
        self.wakeup.wait(60)
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
          # If the job that was send above has not been moved from nextjob to job by the listener
          # thread yet, something went wrong. Throw an exception to make everything restart.
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
        # Wait for the listener thread to terminate.
        # If it doens't within 10 seconds, continue anyway. We can't do much about that.
        try: self.listenerthread.join(10)
        except: pass
        # Set MH/s to zero again, the listener thread might have overwritten that.
        self.mhps = 0
        # Make sure that the RS232 interface handle is closed,
        # otherwise we can't reopen it after restarting.
        try: self.handle.close()
        except: pass
        # Wait for a second to avoid 100% CPU load if something fails reproducibly
        time.sleep(1)
        # Restart (handled by "while True:" loop above)


  # Device response listener thread
  def listener(self):

    # Catch all exceptions and forward them to the main thread
    try:

      # Loop forever unless something goes wrong
      while True:

        # If the main thread has a problem, make sure we die before it restarts
        if self.error != None: break

        # Try to read a response from the device
        nonce = self.handle.read(4)
        # If no response was available, retry
        if len(nonce) != 4: continue
        nonce = nonce[::-1]
        # If there is no job, this must be a leftover from somewhere.
        # In that case, just restart things to clean up the situation.
        if self.job == None: raise Exception("Mining device sent a share before even getting a job")
        # Stop time measurement
        now = time.time()
        # Pass the nonce that we found to the work source, if there is one.
        # Do this before calculating the hash rate as it is latency critical.
        self.job.sendresult(nonce, self)
        # Calculate actual on-device processing time (not including transfer times) of the job.
        delta = (now - self.job.starttime) - 40. / self.baudrate
        # Calculate the hash rate based on the processing time and number of neccessary MHashes.
        self.mhps = (struct.unpack("<I", nonce)[0] & 0x7fffffff) / 500000. / delta
        # Tell the MPBM core that our hash rate has changed, so that it can adjust its work buffer.
        self.miner.updatehashrate(self)
        # This needs self.mhps to be set, don't merge it with the inverse if above!
        # Otherwise a race condition between the main and listener threads may be the result.
        if self.job.check != None:
          # This is a validation job. Validate that the nonce is correct, and complain if not.
          if self.job.check != nonce:
            raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (binascii.hexlify(nonce).decode("ascii"), binascii.hexlify(self.job.check).decode("ascii")))
          else:
            # The nonce was correct. Wake up the main thread.
            with self.wakeup:
              self.checksuccess = True
              self.wakeup.notify()
        else:
          with self.wakeup:
            self.canceled = True
            self.wakeup.notify()
        continue

    # If an exception is thrown in the listener thread...
    except Exception as e:
      # ...put it into the exception container...
      self.error = e
      # ...wake up the main thread...
      with self.wakeup: self.wakeup.notify()
      # ...and terminate the listener thread.


  # This function uploads a job to the device
  def sendjob(self, job):
    # Put it into nextjob. It will be moved to job by the listener
    # thread as soon as it gets acknowledged by the device.
    self.nextjob = job
    # Send it to the device
    self.handle.write(job.state[::-1] + b"\0" * 20 + job.data[75:63:-1])
    now = time.time()
    if self.job != None and self.job.starttime != None and self.job.pool != None:
      mhashes = (now - self.job.starttime) * self.mhps
      self.job.finish(mhashes, self)
      self.job.starttime = None
    self.job = self.nextjob
    self.job.starttime = now
    self.nextjob = None
    