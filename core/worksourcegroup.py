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



import traceback
from threading import RLock
from .baseworksource import BaseWorkSource



class WorkSourceGroup(BaseWorkSource):

  version = "core.worksourcegroup v0.1.0alpha"
  default_name = "Untitled work source group"


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

      
  def deflate(self):
    # Deflate children first
    self.state.children = []
    for child in self.children:
      self.state.children.append(child.deflate())
    # Let BaseWorkSource handle own deflation
    return super(WorkSourceGroup, self).deflate()


  def accepts_child_type(self, type):
    return type.isinstance(BaseWorkSource)
  
  
  def add_work_source(self, worksource):
    with self.start_stop_lock:
      old_parent = worksource.get_parent()
      if old_parent: old_parent.remove_work_source(worksource)
      worksource.set_parent(self)
      with self.childlock:
        if not worksource in self.children:
          if self.started:
            try: worksource.start()
            except Exception as e:
              self.log("Core: Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.append(worksource)

    
  def remove_work_source(self, worksource):
    with self.start_stop_lock:
      with self.childlock:
        while worksource in self.children:
          worksource.set_parent()
          if self.started:
            try: worksource.stop()
            except Exception as e:
              self.log("Core: Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
          self.children.remove(worksource)
        
        
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      with self.childlock:
        for worksource in self.children:
          try: worksource.start()
          except Exception as e:
            self.log("Core: Could not start work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      with self.childlock:
        for worksource in self.children:
          try: worksource.stop()
          except Exception as e:
            self.log("Core: Could not stop work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
      self.started = False
