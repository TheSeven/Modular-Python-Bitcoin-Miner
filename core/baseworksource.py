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
from .statistics import StatisticsProvider
from .startable import Startable
from .inflatable import Inflatable



class BaseWorkSource(StatisticsProvider, Startable, Inflatable):

  is_group = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
    "enabled": {"title": "Enabled", "type": "boolean", "position": 200},
    "hashrate": {"title": "Hashrate", "type": "float", "position": 10000},
    "priority": {"title": "Priority", "type": "float", "position": 10100},
  })


  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Startable.__init__(self)
    Inflatable.__init__(self, core, state)

    self.parent = None
    self.statelock = RLock()
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)
    
    
  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled work source")
    if not "enabled" in self.settings: self.settings.enabled = True
    if not "hashrate" in self.settings: self.settings.hashrate = 0
    if not "priority" in self.settings: self.settings.priority = 1
    
    
  def _reset(self):
    Startable._reset(self)
    self.mhashes_pending = 0
    self.mhashes_deferred = 0
    self.stats.starttime = time.time()
    self.stats.ghashes = 0
    self.stats.jobrequests = 0
    self.stats.failedjobreqs = 0
    self.stats.uploadretries = 0
    self.stats.jobsreceived = 0
    self.stats.jobsaccepted = 0
    self.stats.jobscanceled = 0
    self.stats.sharesaccepted = 0
    self.stats.sharesrejected = 0
    self.stats.difficulty = 0
    
    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.ghashes = self.stats.ghashes + childstats.calculatefieldsum("ghashes")
    stats.avgmhps = 1000. * self.stats.ghashes / (time.time() - stats.starttime) + childstats.calculatefieldsum("avgmhps")
    stats.jobrequests = self.stats.jobrequests + childstats.calculatefieldsum("jobrequests")
    stats.failedjobreqs = self.stats.failedjobreqs + childstats.calculatefieldsum("failedjobreqs")
    stats.uploadretries = self.stats.uploadretries + childstats.calculatefieldsum("uploadretries")
    stats.jobsreceived = self.stats.jobsreceived + childstats.calculatefieldsum("jobsreceived")
    stats.jobsaccepted = self.stats.jobsaccepted + childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = self.stats.jobscanceled + childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = self.stats.sharesaccepted + childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = self.stats.sharesrejected + childstats.calculatefieldsum("sharesrejected")
    stats.difficulty = self.stats.difficulty
    
    
  def set_parent(self, parent = None):
    self.parent = parent
    
    
  def get_parent(self):
    return self.parent

    
  def add_pending_mhashes(self, mhashes):
    with self.statelock: self.mhashes_pending += mhashes
    if self.parent: self.parent.add_pending_mhashes(mhashes)

    
  def add_deferred_mhashes(self, mhashes):
    with self.statelock: self.mhashes_deferred += mhashes
    if self.parent: self.parent.add_deferred_mhashes(mhashes)
