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



################
# Work fetcher #
################



import time
import traceback
from threading import RLock, Condition, Thread, current_thread
from .startable import Startable



class Fetcher(Startable):

  
  def __init__(self, core):
    super(Fetcher, self).__init__()
    self.core = core
    # Initialize global fetcher lock and wakeup condition
    self.lock = Condition()
    # Fetcher controller thread
    self.controllerthread = None
    
    
  def _reset(self):
    super(Fetcher, self)._reset()
    self.speedchanged = True
    self.queuetarget = 5
    self.fetchercount = 0
    self.threads = []
    

  def _start(self):
    super(Fetcher, self)._start()
    self.shutdown = False
    self.controllerthread = Thread(None, self.controllerloop, "fetcher_controller")
    self.controllerthread.daemon = True
    self.controllerthread.start()
  
  
  def _stop(self):
    self.shutdown = True
    self.wakeup()
    self.controllerthread.join(10)
    for thread in self.threads: thread.join(10)
    super(Fetcher, self)._stop()
      
      
  def wakeup(self):
    with self.lock: self.lock.notify()

    
  def notify_speed_changed(self, worker):
    with self.lock:
      self.speedchanged = True
      self.lock.notify()

    
  def controllerloop(self):
    with self.lock:
      while not self.shutdown:
        if self.speedchanged:
          self.speedchanged = False
          jobspersecond = 0
          paralleljobs = 0
          with self.core.workerlock:
            for worker in self.core.workers:
              jobspersecond += worker.get_jobs_per_second()
              paralleljobs += worker.get_parallel_jobs()
          self.queuetarget = max(2, paralleljobs, jobspersecond * 30)
        while self.core.workqueue.count + self.fetchercount < self.queuetarget:
          try:
            thread = Thread(None, self.fetcherthread, "fetcher_worker")
            thread.daemon = True
            thread.start()
            self.threads.append(thread)
            self.fetchercount += 1
          except:
            self.core.log("Fetcher: Error while starting fetcher thread: %s\n" % traceback.format_exc(), 100, "rB")
            time.sleep(1)
        self.lock.wait()

        
  def fetcherthread(self):
    try:
      jobs = self.core.get_root_work_source().get_job()
      if jobs: self.core.workqueue.add_jobs(jobs)
    except: self.core.log("Fetcher: Error while fetching job: %s\n" % traceback.format_exc(), 200, "r")
    with self.lock:
      self.threads.remove(current_thread())
      self.fetchercount -= 1
