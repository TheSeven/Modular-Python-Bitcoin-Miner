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



###################
# Object registry #
###################



from threading import RLock



class ObjectRegistry(object):


  def __init__(self, core):
    self.core = core
    self.lock = RLock()
    self.current_id = 0
    self.objects = {}


  def register(self, obj):
    with self.lock:
      self.current_id += 1
      self.objects[self.current_id] = obj
      return self.current_id
      
    
  def unregister(self, id):
    try: del self.objects[id]
    except: pass
  
  
  def get(self, id):
    return self.objects[id]
