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
# Simple log file logger #
##########################



import os
from threading import RLock
from core.basefrontend import BaseFrontend



class LogFileLogger(BaseFrontend):

  version = "theseven.basicloggers log file logger v0.1.0beta"
  default_name = "Untitled log file logger"
  can_log = True
  can_autodetect = False
  settings = dict(BaseFrontend.settings, **{
    "filename": {"title": "Log file name", "type": "string", "position": 1000},
    "loglevel": {"title": "Log level", "type": "int", "position": 2000},
    "useansi": {"title": "Use ANSI codes", "type": "boolean", "position": 3000},
  })


  def __init__(self, core, state = None):
    super(LogFileLogger, self).__init__(core, state)
    
    
  def apply_settings(self):
    super(LogFileLogger, self).apply_settings()
    if not "filename" in self.settings or not self.settings.filename: self.settings.filename = "mpbm.log"
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "useansi" in self.settings: self.settings.useansi = False
    if self.started and self.settings.filename != self.filename: self.async_restart()
    
  
  def _start(self):
    super(LogFileLogger, self)._start()
    self.filename = self.settings.filename
    self.handle = open(self.filename, "ab")
    self.handle.write(("\n" + "=" * 200 + "\n\n").encode("utf_8"))
  
  
  def _stop(self):
    self.handle.close()
    super(LogFileLogger, self)._stop()

      
  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    prefix = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + " [%3d]: " % loglevel
    newline = True
    for message, format in messages:
      for line in message.splitlines(True):
        if self.settings.useansi:
          modes = ""
          if "r" in format: modes += ";31"
          elif "y" in format: modes += ";33"
          elif "g" in format: modes += ";32"
          if "B" in format: modes += ";1"
          if modes: line = "\x1b[0%sm%s\x1b[0m" % (modes, line)
        self.handle.write((prefix + line if newline else line).encode("utf_8"))
        newline = line[-1:] == "\n"
    