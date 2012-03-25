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



from .util import Bunch



class Inflatable(object):

  settings = {}

  
  def __init__(self, core, state = None):
    self.core = core
    self.started = False
    
    # Create and populate a new state dict if neccessary
    if not state:
      state = Bunch()
      state.settings = Bunch()
      self.is_new_instance = True
    else: self.is_new_instance = False
    self.state = state
      
    # Grab the settings from the state
    self.settings = state.settings
    self.apply_settings()
    
    # Register ourselves in the global object registry
    self.id = core.registry.register(self)
    
    
  def destroy(self):
    # Unregister ourselves from the global object registry
    self.core.registry.unregister(self.id)
    
    
  def apply_settings(self):
    pass
    
        
  def deflate(self):
    return (self.__class__, self.state)
  
  
  @staticmethod
  def inflate(core, state):
    if not state: return None
    return state[0](core, state[1])
