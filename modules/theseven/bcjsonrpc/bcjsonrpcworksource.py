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



import time
import json
import base64
import traceback
from binascii import unhexlify
from threading import RLock
from core.actualworksource import ActualWorkSource
from core.job import Job
try: import http.client as http_client
except ImportError: import httplib as http_client



class BCJSONRPCWorkSource(ActualWorkSource):
  
  version = "theseven.bcjsonrpc work source v0.1.0alpha"
  default_name = "Untitled BCJSONRPC work source"
  settings = dict(ActualWorkSource.settings, **{
    "getworktimeout": {"title": "Getwork timeout", "type": "float", "position": 19000},
    "sendsharetimeout": {"title": "Sendshare timeout", "type": "float", "position": 19100},
    "longpolltimeout": {"title": "Long poll timeout", "type": "float", "position": 19200},
    "host": {"title": "Host", "type": "string", "position": 1000},
    "port": {"title": "Port", "type": "int", "position": 1010},
    "path": {"title": "Path", "type": "string", "position": 1020},
    "username": {"title": "User name", "type": "string", "position": 1100},
    "password": {"title": "Password", "type": "password", "position": 1120},
    "useragent": {"title": "User agent string", "type": "string", "position": 1200},
    "longpollconnections": {"title": "Long poll connnections", "type": "int", "position": 1300},
  })
  

  def __init__(self, core, state = None):
    super(BCJSONRPCWorkSource, self).__init__(core, state)
    
    
  def apply_settings(self):
    super(BCJSONRPCWorkSource, self).apply_settings()
    if not "getworktimeout" in self.settings or not self.settings.getworktimeout:
      self.settings.getworktimeout = 3
    if not "sendsharetimeout" in self.settings or not self.settings.sendsharetimeout:
      self.settings.sendsharetimeout = 5
    if not "longpolltimeout" in self.settings or not self.settings.longpolltimeout:
      self.settings.longpolltimeout = 1200
    if not "host" in self.settings: self.settings.host = ""
    if not "port" in self.settings or not self.settings.port:
      self.settings.port = 8332
    if not "path" in self.settings or not self.settings.path:
      self.settings.path = "/"
    if not "username" in self.settings: self.settings.username = ""
    if not "password" in self.settings: self.settings.password = ""
    if not self.settings.username and not self.settings.password: self.auth = None
    else:
      credentials = self.settings.username + ":" + self.settings.password
      self.auth = "Basic " + base64.b64encode(credentials.encode("utf_8")).decode("ascii")
    if not "useragent" in self.settings: self.settings.useragent = ""
    if self.settings.useragent: self.useragent = self.settings.useragent
    else: self.useragent = "%s (%s)" % (self.core.__class__.version, self.__class__.version)
    if not "longpollconnections" in self.settings: self.settings.longpollconnections = 1
    

  def start(self):
    with self.start_stop_lock:
      if self.started: return
      if not self.settings.host: raise Exception("Host name may not be empty")
      self.started = True
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self.started = False

      
  def get_job(self):
    if self._is_locked_out(): return []
    try:
      now = time.clock()
      conn = http_client.HTTPConnection(self.settings.host, self.settings.port, True, self.settings.getworktimeout)
      req = json.dumps({"method": "getwork", "params": [], "id": 0}).encode("utf_8")
      headers = {"User-Agent": self.useragent, "Content-type": "application/json", "Content-Length": len(req)}
      if self.auth != None: headers["Authorization"] = self.auth
      conn.request("POST", self.settings.path, req, headers)
      response = conn.getresponse()
      """
      with self.statlock:
        if not self.longpolling:
          self.longpolling = False
          headers = response.getheaders()
          for h in headers:
            if h[0].lower() == "x-long-polling":
              url = h[1]
              try:
                if url[0] == "/": url = "http://" + self.host + ":" + str(self.port) + url
                if url[:7] != "http://": raise Exception("Long poll URL isn't HTTP!")
                parts = url[7:].split("/", 1)
                if len(parts) == 2: path = "/" + parts[1]
                else: path = "/"
                parts = parts[0].split(":")
                if len(parts) != 2: raise Exception("Long poll URL contains host but no port!")
                host = parts[0]
                port = parts[1]
                self.miner.log("Found long polling URL for %s: %s\n" % (self.name, url), "g")
                self.longpolling = True
                self.longpollingthread = threading.Thread(None, self.longpollingworker, self.name + "_longpolling", (host, port, path))
                self.longpollingthread.daemon = True
                self.longpollingthread.start()
              except:
                self.miner.log("Invalid long polling URL for %s: %s\n" % (self.name, url), "y")
              break
      """
      response = json.loads(response.read().decode("utf_8"))
      data = unhexlify(response["result"]["data"].encode("ascii"))
      target = unhexlify(response["result"]["target"].encode("ascii"))
      return [Job(self.core, self, self.epoch, now + 60, data[:88], target)]
    except: self.core.log("%s: Error while fetching job: %s\n" % (self.settings.name, traceback.format_exc()), 200, "r")
