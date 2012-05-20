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



#######################
# Block chain manager #
#######################



import time
from threading import RLock
from .util import Bunch
from .statistics import StatisticsProvider, StatisticsList
from .startable import Startable
from .inflatable import Inflatable



class Blockchain(StatisticsProvider, Startable, Inflatable):

  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
    "timeout": {"title": "History timeout", "type": "float", "position": 1000},
  })

  
  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Inflatable.__init__(self, core, state)
    Startable.__init__(self)
    
    self.worksourcelock = RLock()
    self.blocklock = RLock()


  def destroy(self):
    with self.worksourcelock:
      for worksource in self.children:
        worksource.set_blockchain(None)
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = "Untitled blockchain"
    with self.core.blockchainlock:
      origname = self.settings.name
      self.settings.name = None
      name = origname
      i = 1
      while self.core.get_blockchain_by_name(name):
        i += 1
        name = origname + (" (%d)" % i)
      self.settings.name = name
    if not "timeout" in self.settings: self.settings.timeout = 60
    
    
  def _reset(self):    
    self.core.event(300, self, "reset", None, "Resetting blockchain state", blockchain = self)
    Startable._reset(self)
    self.currentprevhash = None
    self.knownprevhashes = []
    self.timeoutend = 0
    self.jobs = []
    self.stats.starttime = time.time()
    self.stats.blocks = 0
    self.stats.lastblock = None

    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.blocks = self.stats.blocks
    stats.lastblock = self.stats.lastblock
    stats.ghashes = childstats.calculatefieldsum("ghashes")
    stats.avgmhps = childstats.calculatefieldsum("avgmhps")
    stats.jobsreceived = childstats.calculatefieldsum("jobsreceived")
    stats.jobsaccepted = childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = childstats.calculatefieldsum("sharesrejected")
    stats.children = []
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)


  def add_work_source(self, worksource):
    with self.worksourcelock:
      if not worksource in self.children: self.children.append(worksource)
  

  def remove_work_source(self, worksource):
    with self.worksourcelock:
      while worksource in self.children: self.children.remove(worksource)


  def check_job(self, job):
    if self.currentprevhash == job.prevhash: return True
    cancel = []
    with self.blocklock:
      now = time.time()
      timeout_expired = now > self.timeoutend
      self.timeoutend = now + self.settings.timeout
      if job.prevhash in self.knownprevhashes: return False
      if timeout_expired: self.knownprevhashes = [self.currentprevhash]
      else: self.knownprevhashes.append(self.currentprevhash)
      self.currentprevhash = job.prevhash
      with self.core.workqueue.lock:
        while self.jobs:
          job = self.jobs.pop(0)
          if job.worker: cancel.append(job)
          else: job.destroy()
      self.jobs = []
      with self.stats.lock:
        self.stats.blocks += 1
        self.stats.lastblock = now
    self.core.log(self, "New block detected\n", 300, "B")
    self.core.workqueue.cancel_jobs(cancel)
    return True
 

 
class DummyBlockchain(object):


  def __init__(self, core):
    self.core = core
    self.id = 0
    self.settings = Bunch(name = "Dummy blockchain")
    
    # Initialize job list (protected by global job queue lock)
    self.jobs = []
    self.currentprevhash = None
    self.knownprevhashes = []
    self.timeoutend = 0
    self.blocklock = RLock()
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)
    
    
  def add_work_source(self, worksource):
    pass


  def remove_work_source(self, worksource):
    pass

  
  def check_job(self, job):
    if self.currentprevhash == job.prevhash: return True
    cancel = []
    with self.blocklock:
      now = time.time()
      timeout_expired = now > self.timeoutend
      self.timeoutend = now + 10
      if job.prevhash in self.knownprevhashes: return False
      if timeout_expired: self.knownprevhashes = [self.currentprevhash]
      else: self.knownprevhashes.append(self.currentprevhash)
      self.currentprevhash = job.prevhash
      with self.core.workqueue.lock:
        while self.jobs:
          job = self.jobs.pop(0)
          if job.worker: cancel.append(job)
          else: job.destroy()
      self.jobs = []
    self.core.log(self, "New block detected\n", 300, "B")
    self.core.workqueue.cancel_jobs(cancel)
    return True
