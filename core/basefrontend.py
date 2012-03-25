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
# Frontend base class #
#######################



from threading import RLock
from .util import Bunch
from .startable import Startable
from .inflatable import Inflatable



class BaseFrontend(Startable, Inflatable):

  can_log = False
  can_show_stats = False
  can_configure = False
  can_autodetect = False
  settings = dict(Inflatable.settings, **{
    "name": {"title": "Name", "type": "string", "position": 100},
  })


  def __init__(self, core, state = None):
    Startable.__init__(self)
    Inflatable.__init__(self, core, state)
    self.does_log = self.__class__.can_log
    self.does_show_stats = self.__class__.can_show_stats
    
    
  def destroy(self):
    Startable.destroy(self)
    Inflatable.destroy(self)


  def apply_settings(self):
    Inflatable.apply_settings(self)
    if not "name" in self.settings or not self.settings.name:
      self.settings.name = getattr(self.__class__, "default_name", "Untitled frontend")


  def _reset(self):
    Startable._reset(self)
    self.jobs_per_second = 0
    self.parallel_jobs = 0
