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



##############
# Work queue #
##############



import time
from threading import Condition, RLock, Thread
from .startable import Startable
try: from queue import Queue
except: from Queue import Queue



class WorkQueue(Startable):

  
  def __init__(self, core):
    super(WorkQueue, self).__init__()
    self.core = core
    # Initialize global work queue lock and wakeup condition
    self.lock = Condition()
    self.cancelqueue = Queue()
    
    
  def _reset(self):
    super(WorkQueue, self)._reset()
    # Initialize job list container and count
    self.lists = {}
    self.count = 0
    self.expirycutoff = 0
    # Initialize taken job list container
    self.takenlists = {}
    
    
  def add_job(self, job):
    with self.lock:
      if not job.blockchain.check_job(job):
        mhashes = job.hashes_remaining / 1000000.
        job.worksource.add_pending_mhashes(-mhashes)
        job.worksource.add_deferred_mhashes(mhashes)
        return
      expiry = int(job.expiry)
      if not expiry in self.lists: self.lists[expiry] = [job]
      else: self.lists[expiry].append(job)
      if expiry > self.expirycutoff: self.count += 1
      job.register()
      self.lock.notify_all()
    
    
  def add_jobs(self, jobs):
    with self.lock:
      seen = {}
      for job in jobs:
        if not job.blockchain.check_job(job):
          if not job.worksource in seen:
            mhashes = 2**32 / 1000000.
            job.worksource.add_pending_mhashes(-mhashes)
            job.worksource.add_deferred_mhashes(mhashes)
            seen[job.worksource] = True
        else:
          expiry = int(job.expiry)
          if not expiry in self.lists: self.lists[expiry] = [job]
          else: self.lists[expiry].append(job)
          if expiry > self.expirycutoff: self.count += 1
          job.register()
      self.lock.notify_all()
    
    
  def cancel_jobs(self, jobs):
    if not jobs: return
    self.cancelqueue.put(jobs)
    
    
  def remove_job(self, job):
    with self.lock:
      try:
        expiry = int(job.expiry)
        try:
          self.lists[expiry].remove(job)
          if expiry > self.expirycutoff: self.count -= 1
        except: pass
        try: self.takenlists[expiry].remove(job)
        except: pass
      except: pass
      
      
  def flush_all_of_work_source(self, worksource):
    cancel = []
    with self.lock:
      for list in self.lists:
        for job in list:
          if job.worksource == worksource:
            list.remove(job)
            if int(job.expiry) > self.expirycutoff: self.count -= 1
            job.destroy()
      for list in self.takenlists:
        for job in list:
          if job.worksource == worksource:
            list.remove(job)
            cancel.append(job)
    self.cancel_jobs(cancel)
    
    
  def get_job(self, worker, expiry_min_ahead, async = False):
    with self.lock:
      job = self._get_job_internal(expiry_min_ahead, async)
      if job:
        self.core.fetcher.wakeup()
        job.set_worker(worker)
        expiry = int(job.expiry)
        if int(job.expiry) <= self.expirycutoff: self.count += 1
        if not expiry in self.takenlists: self.takenlists[expiry] = [job]
        else: self.takenlists[expiry].append(job)
      return job


  def _get_job_internal(self, expiry_min_ahead, async = False):
    self.count -= 1
    while True:
      keys = sorted(self.lists.keys())
      min_expiry = time.time() + expiry_min_ahead
      # Look for a job that meets min_expiry as closely as possible
      for expiry in keys:
        if expiry <= min_expiry: continue
        list = self.lists[expiry]
        if not list: continue
        return list.pop(0)
      # If there was none, look for the job with the latest expiry
      keys.reverse()
      for expiry in keys:
        if expiry > min_expiry: continue
        list = self.lists[expiry]
        if not list: continue
        return list.pop(0)
      # There were no jobs at all => Wait for some to arrive
      self.core.fetcher.wakeup()
      if async: return None
      self.lock.wait()

        
  def _start(self):
    super(WorkQueue, self)._start()
    self.shutdown = False
    self.cleanupthread = Thread(None, self._cleanuploop, "workqueue_cleanup")
    self.cleanupthread.daemon = True
    self.cleanupthread.start()
    self.cancelthread = Thread(None, self._cancelloop, "workqueue_cancelworker")
    self.cancelthread.daemon = True
    self.cancelthread.start()
  
  
  def _stop(self):
    self.shutdown = True
    self.cleanupthread.join(5)
    self.cancelqueue.put(None)
    self.cancelthread.join(5)
    self._reset()
    super(WorkQueue, self)._stop()

    
  def _cleanuploop(self):
    while not self.shutdown:
      now = time.time()
      cancel = []
      with self.lock:
        keys = sorted(self.lists.keys())
        cutoff = now + 10
        for expiry in keys:
          if expiry > cutoff: break
          if expiry > self.expirycutoff and expiry <= cutoff: self.count -= len(self.lists[expiry])
          if expiry <= now:
            while self.lists[expiry]: self.lists[expiry].pop(0).destroy()
            del self.lists[expiry]
        self.expirycutoff = cutoff
        keys = sorted(self.takenlists.keys())
        for expiry in keys:
          if expiry <= now:
            while self.takenlists[expiry]: cancel.append(self.takenlists[expiry].pop(0))
            del self.takenlists[expiry]
      self.core.fetcher.wakeup()
      self.cancel_jobs(cancel)
      time.sleep(1)

  
  def _cancelloop(self):
    while True:
      jobs = self.cancelqueue.get()
      if not jobs: return
      for job in jobs:
        try: job.cancel()
        except: self.core.log("Fetcher: Error while canceling job: %s\n" % traceback.format_exc(), 100, "r")
