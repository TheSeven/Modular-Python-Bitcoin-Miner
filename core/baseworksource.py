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



##########################
# Work source base class #
##########################



import time
from threading import RLock
from .util import Bunch
from .inflatable import Inflatable



class BaseWorkSource(Inflatable):


  def __init__(self, core, state = None):
    super(BaseWorkSource, self).__init__(core, state)
    
    # Initialize work source state
    self.start_stop_lock = RLock()
    self.parent = None
    self.stats = Bunch()
    self.stats.lock = RLock()
    self._zero_stats()
    
    
  def apply_settings(self):
    super(BaseWorkSource, self).apply_settings()
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled work source")
    if not "enabled" in self.settings: self.settings.enabled = True
    if not "hashrate" in self.settings: self.settings.hashrate = 0
    if not "priority" in self.settings: self.settings.priority = 1
    
    
  def _zero_stats(self):
    self.stats.starttime = None
    self.stats.ghashes = 0
    self.stats.lockout = 0
    self.stats.sequentialerrors = 0
    self.stats.jobrequests = 0
    self.stats.failedjobreqs = 0
    self.stats.uploadretries = 0
    self.stats.jobsaccepted = 0
    self.stats.jobscanceled = 0
    self.stats.sharesaccepted = 0
    self.stats.sharesrejected = 0
    self.stats.difficulty = 0
    
    
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      self.zero_stats()
      self.starttime = time.time()
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self.started = False

        
  def accepts_child_type(self, type):
    return False
    
    
  def set_parent(self, parent = None):
    self.parent = parent
    
    
  def get_parent(self):
    return self.parent
