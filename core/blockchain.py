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
    "grouptime": {"title": "Block grouping time", "type": "float", "position": 1000},
  })

  
  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Startable.__init__(self)
    Inflatable.__init__(self, core, state)
    
    self.worksourcelock = RLock()
    self.epochlock = RLock()


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
    if not "grouptime" in self.settings: self.settings.grouptime = 30
    
    
  def _reset(self):    
    Startable._reset(self)
    self.epoch = 0
    self.groupend = 0
    self.jobs = []
    self.stats.starttime = time.time()
    self.stats.blocks = 0
    self.stats.lastblock = None

    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.blocks = self.stats.blocks
    stats.lastblock = self.stats.lastblock
    self.stats.jobsaccepted = childstats.calculatefieldsum("jobsaccepted")
    self.stats.jobscanceled = childstats.calculatefieldsum("jobscanceled")
    self.stats.sharesaccepted = childstats.calculatefieldsum("sharesaccepted")
    self.stats.sharesrejected = childstats.calculatefieldsum("sharesrejected")
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)


  def add_work_source(self, worksource):
    with self.worksourcelock:
      worksource.epoch = self.epoch
      if not worksource in self.children: self.children.append(worksource)
  

  def remove_work_source(self, worksource):
    with self.worksourcelock:
      while worksource in self.children: self.children.remove(worksource)


  def handle_block(self, worksource):
    now = time.time()
    with self.epochlock:
      if now > groupend or worksource.epoch == self.epoch:
        self.epoch += 1
        self.groupend = now + self.settings.grouptime
        with self.stats.lock:
          self.stats.blocks += 1
          self.stats.lastblock = now
        for job in self.jobs: job.cancel()
        self.jobs = []
        worksource.epoch = self.epoch
      else: worksource.epoch += 1
    self.core.log("%s indicates that a new block was found" % worksource.settings.name, 300, "B")

      
  def check_job(self, job):
    with self.epochlock:
      if job.epoch == self.epoch or time.time() > self.groupend: return True
      return False

      
  def check_work_source(self, worksource):
    with self.epochlock:
      if worksource.epoch == self.epoch or time.time() > self.groupend: return True
      return False
  
  
  
class DummyBlockchain(object):


  def __init__(self, core):
    # Initialize job list (protected by global job queue lock)
    self.jobs = []
    self.epochlock = RLock()
    
    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)
    
    
  def add_work_source(self, worksource):
    pass


  def remove_work_source(self, worksource):
    pass


  def handle_block(self):
    with self.epochlock:
      for job in self.jobs: job.cancel()
      self.jobs = []
      self.core.notify_job_canceled()
      worksource.epoch += 1
    self.core.log("%s indicates that a new block was found" % worksource.settings.name, 300, "B")
  
  
  def check_job(self, job):
    with self.epochlock:
      if job.epoch == self.epoch: return True
      return False

      
  def check_work_source(self, worksource):
    return True
  