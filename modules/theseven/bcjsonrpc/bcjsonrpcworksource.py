#!/usr/bin/env python


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



#######################################
# Bitcoin JSON RPC work source module #
#######################################



from threading import RLock
from core.actualworksource import ActualWorkSource



class BCJSONRPCWorkSource(ActualWorkSource):
  
  version = "worksource.theseven.bcjsonrpc.BCJSONRPCWorkSource v0.1.0alpha"
  

  def __init__(self, core, state = None):
    super().__init__(core, state)

    self.default_useragent = "%s (%s)" % (core.__class__.version, self.__class__.version)
    
    
    def apply_settings(self):
      super().apply_settings()
      if not "getworktimeout" in self.settings or not self.settings.getworktimeout:
        self.settings.getworktimeout = 3
      if not "sendsharetimeout" in self.settings or not self.settings.sendsharetimeout:
        self.settings.sendsharetimeout = 5
      if not "port" in self.settings or not self.settings.port:
        self.settings.port = 8332
      if not "path" in self.settings or not self.settings.path:
        self.settings.path = "/"
      if not "username" in self.settings: self.settings.username = ""
      if not "password" in self.settings: self.settings.password = ""
      if self.settings.username == "" and self.settings.password == "": self.auth = None
      else:
        credentials = self.settings.username + ":" + self.settings.password
        self.auth = "Basic " + base64.b64encode(credentials.encode("utf_8")).decode("ascii")
      if not "useragent" in self.settings: self.settings.useragent = None
      

    def start(self):
      if not "host" in self.settings: raise Exception("Missing attribute: host")
    
    
    def stop(self):
      pass
