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
# Statistics base classes #
###########################



from threading import RLock
from .util import Bunch



class Statistics(Bunch):


  def __init__(self, *args, **kwargs):
    super(Statistics, self).__init__(*args, **kwargs)
    

    
class StatisticsList(list):


  def __init__(self, *args, **kwargs):
    super(StatisticsList, self).__init__(*args, **kwargs)
    
    
  def calculatefieldsum(self, field):
    return sum(element[field] for element in self)

    
  def calculatefieldavg(self, field):
    if len(self) == 0: return 0
    return 1. * sum(element[field] in self) / len(self)
    
    
    
class StatisticsProvider(object):


  def __init__(self):
    self.stats = Bunch()
    self.stats.lock = RLock()
    self.children = []
    
    
  def _get_statistics(self, stats, childstats):
    stats.obj = self
    stats.id = self.id
    stats.name = self.settings.name
    stats.children = childstats

    
  def get_statistics(self):
    stats = Statistics()
    childstats = StatisticsList()
    for child in self.children: childstats.append(child.get_statistics())
    with self.stats.lock: self._get_statistics(stats, childstats)
    return stats
