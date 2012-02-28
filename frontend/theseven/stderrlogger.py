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



########################
# Simple stderr logger #
########################



import os
from threading import RLock
from core.basefrontend import BaseFrontend



class StderrLogger(BaseFrontend):

  can_log = True


  def __init__(self, core, state = None):
    super(StderrLogger, self).__init__(core, state)
    self.start_stop_lock = RLock()
    
    
  def apply_settings(self):
    super(StderrLogger, self).apply_settings()
    if not "loglevel" in self.settings: self.settings.loglevel = 500
    if not "useansi" in self.settings: self.settings.useansi = "TERM" in os.environ
    
  
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      
      # Clear screen
      if self.settings.useansi: self.core.stderr.write("\x1b[2J")
      else: self.core.stderr.write("\n" * 100)
      
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self.started = False

      
  def write_log_message(self, timestamp, continuation, message, loglevel, format):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    prefix = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + " [%3d]: " % loglevel
    first = True
    for line in message.splitlines(True):
      if self.settings.useansi:
        modes = ""
        if "r" in format: modes += ";31"
        elif "y" in format: modes += ";33"
        elif "g" in format: modes += ";32"
        if "B" in format: modes += ";1"
        if modes: line = "\x1b[0%sm%s\x1b[0m" % (modes, line)
      self.core.stderr.write(line if first and continuation else prefix + line)
      first = False
    