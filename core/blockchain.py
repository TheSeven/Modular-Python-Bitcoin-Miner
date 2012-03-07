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
from .inflatable import Inflatable



class Blockchain(Inflatable):

  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
    "grouptime": {"title": "Block grouping time", "type": "float", "position": 1000},
  })

  
  def __init__(self, core, state = None):
    super(Blockchain, self).__init__(core, state)
    self.start_stop_lock = RLock()
    
    # Initialize blockchain state
    self.epoch = 0
    self.groupend = 0
    self.epochlock = RLock()
    # Initialize job list (protected by global job queue lock)
    self.jobs = []
    # Initialize work source list
    self.worksources = []
    self.worksourcelock = RLock()
    
    # Initialize blockchain statistics
    self.stats = Bunch()
    self.stats.lock = RLock()
    self.stats.starttime = None
    self.stats.blocks = 0
    self.stats.lastblock = None
    
    
  def apply_settings(self):
    super(Blockchain, self).apply_settings()
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
    
    
  def destroy(self):
    super(Blockchain, self).destroy()
    with self.worksourcelock:
      for worksource in self.worksources:
        worksource.set_blockchain(None)
    
    
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      with self.stats.lock:
        self.stats.starttime = time.time()
        self.stats.blocks = 0
        self.stats.lastblock = None
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self.started = False

    
  def add_job(self, job):
    if not job in self.jobs: self.jobs.append(job)
  

  def remove_job(self, job):
    while job in self.jobs: self.jobs.remove(job)


  def add_work_source(self, worksource):
    with self.worksourcelock:
      worksource.epoch = self.epoch
      if not worksource in self.worksources: self.worksources.append(worksource)
  

  def remove_work_source(self, worksource):
    with self.worksourcelock:
      while worksource in self.worksources: self.worksources.remove(worksource)


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

      
  def check_job(self, job):
    with self.epochlock:
      if job.epoch == self.epoch or time.time() > groupend: return True
      return False

      
  def check_work_source(self, worksource):
    with self.epochlock:
      if worksource.epoch == self.epoch or time.time() > groupend: return True
      return False
  