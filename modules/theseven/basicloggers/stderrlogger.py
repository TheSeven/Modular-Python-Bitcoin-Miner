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

  version = "theseven.basicloggers stderr logger v0.1.0beta"
  default_name = "stderr logger"
  can_log = True
  can_autodetect = True
  settings = dict(BaseFrontend.settings, **{
    "loglevel": {"title": "Log level", "type": "int", "position": 1000},
    "useansi": {"title": "Use ANSI codes", "type": "boolean", "position": 2000},
  })


  @classmethod
  def autodetect(self, core):
    core.add_frontend(self(core))
    
    
  def __init__(self, core, state = None):
    super(StderrLogger, self).__init__(core, state)
    
    
  def apply_settings(self):
    super(StderrLogger, self).apply_settings()
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "useansi" in self.settings: self.settings.useansi = "TERM" in os.environ
    
  
  def _start(self):
    super(StderrLogger, self)._start()

    # Clear screen
    if self.settings.useansi: self.core.stderr.write("\x1b[2J")
    else: self.core.stderr.write("\n" * 100)
  
  
  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    prefix = "%s [%3d] %s: " % (timestamp.strftime("%Y-%m-%d %H:%M:%S.%f"), loglevel, source.settings.name)
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
        self.core.stderr.write(prefix + line if newline else line)
        newline = line[-1:] == "\n"
    