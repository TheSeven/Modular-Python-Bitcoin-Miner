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
from .util import Bunch



class Fetcher(Startable):

  
  def __init__(self, core):
    self.core = core
    self.id = -2
    self.settings = Bunch(name = "Fetcher controller")
    super(Fetcher, self).__init__()
    # Initialize global fetcher lock and wakeup condition
    self.lock = Condition()
    # Fetcher controller thread
    self.controllerthread = None
    
    
  def _reset(self):
    self.core.event(300, self, "reset", None, "Resetting fetcher state")
    super(Fetcher, self)._reset()
    self.speedchanged = True
    self.queuetarget = 5
    

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
          self.queuetarget = max(5, paralleljobs * 2, jobspersecond * 30)
        
        worksource = self.core.get_root_work_source()
        queuecount = self.core.workqueue.count
        fetchercount = worksource.get_running_fetcher_count()
        startfetchers = min(5, (self.queuetarget - queuecount) // 2 - fetchercount)
        if startfetchers <= 0:
          self.lock.wait()
          continue
        try:
          started = worksource.start_fetchers(startfetchers if self.core.workqueue.count * 4 < self.queuetarget else 1)
          if not started:
            self.lock.wait(0.1)
            continue
          lockout = time.time() + min(5, 4 * self.core.workqueue.count / self.queuetarget - 1)
          while time.time() < lockout and self.core.workqueue.count > self.queuetarget / 4: self.lock.wait(0.1)
        except:
          self.core.log(self, "Error while starting fetcher thread: %s\n" % traceback.format_exc(), 100, "rB")
          time.sleep(1)
