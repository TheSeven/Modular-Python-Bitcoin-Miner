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



#############################
# In-/Deflatable base class #
#############################



import time
from threading import RLock, Thread



class Startable(object):


  def __init__(self):
    self.start_stop_lock = RLock()
    self.started = False
    self._reset()
    
    
  def destroy(self):
    self.stop()
    super(Startable, self).destroy()
    
    
  def _reset(self):
    pass
    
    
  def _start(self):
    pass


  def _stop(self):
    pass
    
    
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      self._reset()
      self._start()
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self._stop()
      self.started = False

        
  def restart(self, delay = 0):
    time.sleep(delay)
    with self.start_stop_lock:
      if not self.started: return
      self.stop()
      self.start()
      
      
  def async_start(self, delay = 0):
    Thread(None, self.start, self.settings.name + "_start", (delay,)).start()

      
  def async_stop(self, delay = 0):
    Thread(None, self.stop, self.settings.name + "_stop", (delay,)).start()
      
      
  def async_restart(self, delay = 0):
    Thread(None, self.restart, self.settings.name + "_restart", (delay,)).start()
