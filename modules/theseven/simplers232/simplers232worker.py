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



########################################
# Simple RS232 worker interface module #
########################################



import serial
import time
import struct
import traceback
from threading import RLock, Condition, Thread
from binascii import hexlify, unhexlify
from core.baseworker import BaseWorker
from core.validationjob import ValidationJob



class SimpleRS232Worker(BaseWorker):
  
  version = "theseven.simplers232 worker v0.1.0alpha"
  default_name = "Untitled SimpleRS232 worker"
  settings = dict(BaseWorker.settings, **{
    "port": {"title": "Port", "type": "string", "position": 1000},
    "baudrate": {"title": "Baud rate", "type": "int", "position": 1100},
    "jobinterval": {"title": "Job interval", "type": "float", "position": 1200},
  })
  

  def __init__(self, core, state = None):
    super(SimpleRS232Worker, self).__init__(core, state)
    self.wakeup = Condition()
    self.mainthread = None
    self.listenerthread = None
    
    
  def apply_settings(self):
    super(SimpleRS232Worker, self).apply_settings()
    if not "port" in self.settings or not self.settings.port: self.settings.port = "/dev/ttyS0"
    if not "baudrate" in self.settings or not self.settings.baudrate: self.settings.baudrate = 115200
    if not "jobinterval" in self.settings or not self.settings.jobinterval: self.settings.jobinterval = 60
    if self.settings.port != self.port or self.settings.baudrate != self.baudrate: self.async_restart()
    

  def _reset(self):
    super(SimpleRS232Worker, self)._reset()
    self.port = None
    self.baudrate = None

      
  def _start(self):
    super(SimpleRS232Worker, self)._start()
    self.port = self.settings.port
    self.baudrate = self.settings.baudrate
    self.jobs_per_second = 1. / self.settings.jobinterval
    self.parallel_jobs = 1
    self.shutdown = False
    self.mainthread = Thread(None, self.main, self.settings.name + "_main")
    self.mainthread.daemon = True
    self.mainthread.start()
  
  
  def _stop(self):
    super(SimpleRS232Worker, self)._stop()
    self.shutdown = True
    with self.wakeup: self.wakeup.notify()
    self.mainthread.join(10)

      
  def notify_canceled(self, job):
    with self.wakeup:
      if self.job == job or self.nextjob == job:
        self.wakeup.notify()

        
  def main(self):
    while not self.shutdown:
      try:
        self.error = None
        self.job = None
        self.nextjob = None
        self.speed = 0
        self.handle = serial.Serial(self.port, self.baudrate, serial.EIGHTBITS, serial.PARITY_NONE, serial.STOPBITS_ONE, 1, False, False, None, False, None)
        self.handle.write(struct.pack("45B", *([0] * 45)))
        data = self.handle.read(100)
        if len(data) == 0: raise Exception("Failed to sync with mining device: Device does not respond")
        if data[-1:] != b"\0": raise Exception("Failed to sync with mining device: Device sends garbage")
        self.wakeup.acquire()
        self.checksuccess = False
        self.listenerthread = Thread(None, self.listener, self.settings.name + "_listener")
        self.listenerthread.daemon = True
        self.listenerthread.start()
        job = ValidationJob(self.core, b"\0" * 64 + unhexlify(b"4c0afa494de837d81a269421"), unhexlify(b"7bc2b302"), unhexlify(b"1625cbf1a5bc6ba648d1218441389e00a9dc79768a2fc6f2b79c70cf576febd0"))
        self.sendjob(job)
        self.wakeup.wait(1)
        if self.error != None: raise self.error
        if self.nextjob != None: raise Exception("Timeout waiting for job ACK")
        self.wakeup.wait(60)
        if self.error != None: raise self.error
        if not self.checksuccess: raise Exception("Timeout waiting for validation job to finish")
        self.core.log(self.settings.name + ": Running at %f MH/s\n" % (self.speed / 1000000.), 300, "B")
        interval = min(60, 2**32 / self.speed)
        self.jobinterval = min(self.settings.jobinterval, max(0.5, interval * 0.8 - 1))
        self.core.log(self.settings.name + ": Job interval: %f seconds\n" % self.jobinterval, 400, "B")
        self.jobspersecond = 1. / self.jobinterval
        self.core.notify_speed_changed(self)
        while not self.shutdown:
          self.wakeup.release()
          job = self.core.get_job(self, self.jobinterval)
          self.wakeup.acquire()
          if job.canceled: continue
          if self.error != None: raise self.error
          self.sendjob(job)
          self.wakeup.wait(1)
          if self.error != None: raise self.error
          if self.nextjob != None: raise Exception("Timeout waiting for job ACK")
          if self.job.canceled: continue
          self.wakeup.wait(self.jobinterval)
          if self.error != None: raise self.error
      except Exception as e:
        self.core.log(self.settings.name + ": %s\n" % traceback.format_exc(), 100, "rB")
        self.error = e
      finally:
        self.speed = 0
        try: self.wakeup.release()
        except: pass
        try: self.handle.close()
        except: pass
        try: self.listenerthread.join(10)
        except: pass
        self.speed = 0
        if not self.shutdown: time.sleep(1)


  def listener(self):
    try:
      while True:
        if self.error != None: break
        data = self.handle.read(1)
        if len(data) == 0: continue
        result = struct.unpack("B", data)[0]
        if result == 1:
          if self.nextjob == None: raise Exception("Got spurious job ACK from mining device")
          now = time.time()
          if self.job != None and self.job.starttime != None:
            hashes = (now - self.job.starttime) * self.speed
            self.job.hashes_processed(hashes)
            self.job.starttime = None
          with self.wakeup:
            self.job = self.nextjob
            self.job.starttime = now
            self.nextjob = None
            self.wakeup.notify()
          continue
        elif result == 2:
          nonce = self.handle.read(4)[::-1]
          if self.job == None: raise Exception("Mining device sent a share before even getting a job")
          now = time.time()
          self.job.nonce_found(nonce)
          delta = (now - self.job.starttime) - 40. / self.baudrate
          self.speed = struct.unpack("<I", nonce)[0] / delta
          if isinstance(self.job, ValidationJob):
            if self.job.nonce != nonce:
              raise Exception("Mining device is not working correctly (returned %s instead of %s)" % (hexlify(nonce).decode("ascii"), hexlify(self.job.nonce).decode("ascii")))
            else:
              with self.wakeup:
                self.checksuccess = True
                self.wakeup.notify()
          continue

        if result == 3:
          self.core.log(self.settings.name + " exhausted keyspace!\n", 200, "y")
          if isinstance(self.job, ValidationJob): raise Exception("Validation job terminated without finding a share")
          if self.job != None and self.job.starttime != None:
            hashes = (time.time() - self.job.starttime) * self.speed
            self.job.hashes_processed(hashes)
            self.job.starttime = None
          with self.wakeup: self.wakeup.notify()
          continue
        raise Exception("Got bad message from mining device: %d" % result)
    except Exception as e:
      self.error = e
      with self.wakeup: self.wakeup.notify()


  def sendjob(self, job):
    self.nextjob = job
    self.handle.write(struct.pack("B", 1) + job.midstate[::-1] + job.data[75:63:-1])
