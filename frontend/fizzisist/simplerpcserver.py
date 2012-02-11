# Modular Python Bitcoin Miner
# Copyright (C) 2011-2012 Michael Sparmann (TheSeven)
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


##############################
# Simple RPC stats interface #
##############################

# Module configuration options:
#   host: Hostname for the server (default "localhost")
#   port: Port to listen on (default 6500)

import threading
from SimpleXMLRPCServer import SimpleXMLRPCServer

class SimpleRPCServer(object):
  def __init__(self, miner, dict):
    self.__dict__ = dict
    self.miner = miner
    self.addr = getattr(self, "host", "localhost")
    self.port = getattr(self, "port", 6500)
    self.miner.log("Starting SimpleRPCServer at http://%s:%s/\n" % (self.addr, self.port))
    server = SimpleXMLRPCServer((self.addr, self.port), allow_none=True)
    server.register_introspection_functions()
    server.register_function(self.getWorkerStats)
    server.register_function(self.getPoolStats)
    thread = threading.Thread(target=server.serve_forever, name="SimpleRPCServer")
    thread.daemon = True
    thread.start()
  
  def message(self, date, str, format):
    pass
  
  def getWorkerStats(self):
    return self.miner.collectstatistics(self.miner.workers)
    
  def getPoolStats(self):
    return self.miner.collectstatistics(self.miner.pools)
    
