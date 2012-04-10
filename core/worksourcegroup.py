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



###########################
# Work source group class #
###########################



import time
import traceback
from threading import RLock
from .baseworksource import BaseWorkSource



class WorkSourceGroup(BaseWorkSource):

  version = "core.worksourcegroup v0.1.0beta"
  default_name = "Untitled work source group"
  is_group = True,
  settings = dict(BaseWorkSource.settings, **{
    "distribution_granularity": {"title": "Distribution granularity", "type": "float", "position": 20000},
  })


  def __init__(self, core, state = None):
    super(WorkSourceGroup, self).__init__(core, state)
    
    # Populate state dict if this is a new instance
    if self.is_new_instance:
      self.state.children = []
      
    # Instantiate child work sources
    self.childlock = RLock()
    self.children = []
    for childstate in self.state.children:
      self.add_work_source(BaseWorkSource.inflate(core, childstate))
      

  def _reset(self):
    super(WorkSourceGroup, self)._reset()
    self.last_index = 0
    self.last_time = time.time()

      
  def apply_settings(self):
    super(WorkSourceGroup, self).apply_settings()
    if not "distribution_granularity" in self.settings or not self.settings.distribution_granularity:
      self.settings.distribution_granularity = 16

      
  def deflate(self):
    # Deflate children first
    self.state.children = []
    for child in self.children:
      self.state.children.append(child.deflate())
    # Let BaseWorkSource handle own deflation
    return super(WorkSourceGroup, self).deflate()


  def add_work_source(self, worksource):
    with self.start_stop_lock:
      w = self
      while w:
        if w == worksource: raise Exception("Trying to move work source %s into itself or one of its descendants!" % worksource.settings.name)
        w = w.get_parent()
      old_parent = worksource.get_parent()
      if old_parent: old_parent.remove_work_source(worksource)
      worksource.set_parent(self)
      with self.childlock:
        if not worksource in self.children:
          if self.started:
            try:
              self.core.log("%s: Starting up work source %s...\n" % (self.settings.name, worksource.settings.name), 800)
              worksource.start()
            except Exception as e:
              self.core.log("Core: Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.append(worksource)

    
  def remove_work_source(self, worksource):
    with self.start_stop_lock:
      with self.childlock:
        while worksource in self.children:
          worksource.set_parent()
          if self.started:
            try:
              self.core.log("%s: Shutting down work source %s...\n" % (self.settings.name, worksource.settings.name), 800)
              worksource.stop()
            except Exception as e:
              self.core.log("Core: Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.remove(worksource)
        
        
  def _start(self):
    super(WorkSourceGroup, self)._start()
    with self.childlock:
      for worksource in self.children:
        try:
          self.core.log("%s: Starting up work source %s...\n" % (self.settings.name, worksource.settings.name), 800)
          worksource.start()
        except Exception as e:
          self.core.log("Core: Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
  
  
  def _stop(self):
    with self.childlock:
      for worksource in self.children:
        try:
          self.core.log("%s: Shutting down work source %s...\n" % (self.settings.name, worksource.settings.name), 800)
          worksource.stop()
        except Exception as e:
          self.core.log("Core: Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
    super(WorkSourceGroup, self)._stop()
      
      
  def _distribute_mhashes(self):
    with self.statelock:
      now = time.time()
      timestep = now - self.last_time
      self.last_time = now
      mhashes_remaining = 2**32 / 1000000. * self.settings.distribution_granularity
      total_priority = 0
      for child in self.children:
        if child.settings.enabled:
          with child.statelock:
            total_priority += child.settings.priority
            mhashes = timestep * child.settings.hashrate
            child.mhashes_pending += mhashes + child.mhashes_deferred * 0.1
            mhashes_remaining -= mhashes
            child.mhashes_deferred *= 0.9
      if mhashes_remaining > 0 and total_priority > 0:
        unit = mhashes_remaining / total_priority
        for child in self.children:
          if child.settings.enabled:
            with child.statelock:
              mhashes = unit * child.settings.priority
              child.mhashes_pending += mhashes
              mhashes_remaining -= mhashes


  def _get_start_index(self):
    with self.statelock:
      self.last_index += 1
      if self.last_index >= len(self.children): self.last_index = 0
      return self.last_index
      
      
  def _get_job_round(self, force = False):
    with self.childlock:
      children = [child for child in self.children]
      startindex = self._get_start_index()
    found = False
    while not found:
      index = startindex
      first = True
      while index != startindex or first:
        worksource = children[index]
        mhashes = 0
        if not worksource.is_group: mhashes = 2**32 / 1000000.
        if force or worksource.mhashes_pending >= mhashes:
          if mhashes: worksource.add_pending_mhashes(-mhashes)
          job = worksource.get_job()
          if job:
            if mhashes: worksource.add_pending_mhashes(mhashes)
            return job
          self.add_pending_mhashes(mhashes)
          found = True
        index += 1
        if index >= len(children): index = 0
        first = False
      if not found: self._distribute_mhashes()
    return []

    
  def get_job(self):
    if not self.started or not self.settings.enabled or not self.children: return []
    job = self._get_job_round()
    if job: return job
    job = self._get_job_round(True)
    if job: return job
    if self.parent:
      mhashes = 2**32 / 1000000.
      self.add_pending_mhashes(-mhashes)
      self.parent.add_pending_mhashes(mhashes)
    return []
