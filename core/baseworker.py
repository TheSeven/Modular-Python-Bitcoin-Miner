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



#####################
# Worker base class #
#####################



import time
from threading import RLock, Thread
from .util import Bunch
from .statistics import StatisticsProvider
from .startable import Startable
from .inflatable import Inflatable



class BaseWorker(StatisticsProvider, Startable, Inflatable):

  can_autodetect = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
  })


  def __init__(self, core, state = None):
    StatisticsProvider.__init__(self)
    Startable.__init__(self)
    Inflatable.__init__(self, core, state)

    self.children = []
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled worker")

      
  def _reset(self):
    Startable._reset(self)
    self.job = None
    self.jobs_per_second = 0
    self.parallel_jobs = 0
    self.stats.starttime = time.time()
    self.stats.ghashes = 0
    self.stats.mhps = 0
    self.stats.jobsaccepted = 0
    self.stats.jobscanceled = 0
    self.stats.sharesaccepted = 0
    self.stats.sharesrejected = 0
    self.stats.sharesinvalid = 0
    
    
  def _get_statistics(self, stats, childstats):
    StatisticsProvider._get_statistics(self, stats, childstats)
    stats.starttime = self.stats.starttime
    stats.ghashes = self.stats.ghashes + childstats.calculatefieldsum("ghashes")
    stats.avgmhps = 1000. * self.stats.ghashes / (time.time() - stats.starttime) + childstats.calculatefieldsum("avgmhps")
    stats.mhps = self.stats.mhps + childstats.calculatefieldsum("mhps")
    stats.jobsaccepted = self.stats.jobsaccepted + childstats.calculatefieldsum("jobsaccepted")
    stats.jobscanceled = self.stats.jobscanceled + childstats.calculatefieldsum("jobscanceled")
    stats.sharesaccepted = self.stats.sharesaccepted + childstats.calculatefieldsum("sharesaccepted")
    stats.sharesrejected = self.stats.sharesrejected + childstats.calculatefieldsum("sharesrejected")
    stats.sharesinvalid = self.stats.sharesinvalid + childstats.calculatefieldsum("sharesinvalid")
    stats.parallel_jobs = self.parallel_jobs + childstats.calculatefieldsum("parallel_jobs")
    stats.current_job = self.job
    stats.current_work_source = getattr(stats.current_job, "worksource", None) if stats.current_job else None
    stats.current_work_source_id = stats.current_work_source.id if stats.current_work_source else None
    stats.current_work_source_name = stats.current_work_source.settings.name if stats.current_work_source else None
    
    
  def get_jobs_per_second(self):
    result = self.jobs_per_second
    for child in self.children: result += child.get_jobs_per_second()
    return result
      
  def get_parallel_jobs(self):
    result = self.parallel_jobs
    for child in self.children: result += child.get_parallel_jobs()
    return result
