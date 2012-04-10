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
import struct
import base64
import traceback
from binascii import hexlify, unhexlify
from threading import Thread, RLock
from core.actualworksource import ActualWorkSource
from core.job import Job
try: import http.client as http_client
except ImportError: import httplib as http_client



class BCJSONRPCWorkSource(ActualWorkSource):
  
  version = "theseven.bcjsonrpc work source v0.1.0beta"
  default_name = "Untitled BCJSONRPC work source"
  settings = dict(ActualWorkSource.settings, **{
    "getworktimeout": {"title": "Getwork timeout", "type": "float", "position": 19000},
    "sendsharetimeout": {"title": "Sendshare timeout", "type": "float", "position": 19100},
    "longpolltimeout": {"title": "Long poll connect timeout", "type": "float", "position": 19200},
    "longpollresponsetimeout": {"title": "Long poll response timeout", "type": "float", "position": 19200},
    "host": {"title": "Host", "type": "string", "position": 1000},
    "port": {"title": "Port", "type": "int", "position": 1010},
    "path": {"title": "Path", "type": "string", "position": 1020},
    "username": {"title": "User name", "type": "string", "position": 1100},
    "password": {"title": "Password", "type": "password", "position": 1120},
    "useragent": {"title": "User agent string", "type": "string", "position": 1200},
    "longpollconnections": {"title": "Long poll connnections", "type": "int", "position": 1300},
    "expirymargin": {"title": "Job expiry safety margin", "type": "int", "position": 1400},
  })
  

  def __init__(self, core, state = None):
    self.connlock = RLock()
    self.conn = None
    self.uploadconnlock = RLock()
    self.uploadconn = None
    super(BCJSONRPCWorkSource, self).__init__(core, state)
    self.extensions = "longpoll midstate rollntime"
    self.runcycle = 0
    
    
  def apply_settings(self):
    super(BCJSONRPCWorkSource, self).apply_settings()
    if not "getworktimeout" in self.settings or not self.settings.getworktimeout:
      self.settings.getworktimeout = 3
    if not "sendsharetimeout" in self.settings or not self.settings.sendsharetimeout:
      self.settings.sendsharetimeout = 5
    if not "longpolltimeout" in self.settings or not self.settings.longpolltimeout:
      self.settings.longpolltimeout = 10
    if not "longpollresponsetimeout" in self.settings or not self.settings.longpollresponsetimeout:
      self.settings.longpollresponsetimeout = 1800
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
    if not "expirymargin" in self.settings: self.settings.expirymargin = 5
    with self.connlock: self.conn = None
    with self.uploadconnlock: self.uploadconn = None

    
  def _reset(self):
    super(BCJSONRPCWorkSource, self)._reset()
    self.stats.supports_rollntime = None
    self.longpollurl = None
    
    
  def _stop(self):
    self.runcycle += 1
    super(BCJSONRPCWorkSource, self)._stop()
    
    
  def _get_statistics(self, stats, childstats):
    super(BCJSONRPCWorkSource, self)._get_statistics(stats, childstats)
    stats.supports_rollntime = self.stats.supports_rollntime
    

  def _get_job(self):
    if not self.settings.host: return []
    now = time.time()
    req = json.dumps({"method": "getwork", "params": [], "id": 0}).encode("utf_8")
    headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions,
               "Content-type": "application/json", "Content-Length": len(req), "Connection": "Keep-Alive"}
    if self.auth != None: headers["Authorization"] = self.auth
    with self.connlock:
      try:
        if not self.conn: self.conn = http_client.HTTPConnection(self.settings.host, self.settings.port, True, self.settings.getworktimeout)
        self.conn.request("POST", self.settings.path, req, headers)
        self.conn.sock.settimeout(self.settings.getworktimeout)
        response = self.conn.getresponse()
        data = response.read()
      except:
        self.conn = None
        raise
    with self.statelock:
      if not self.settings.longpollconnections: self.signals_new_block = False
      else:
        lpfound = False
        headers = response.getheaders()
        for h in headers:
          if h[0].lower() == "x-long-polling":
            lpfound = True
            url = h[1]
            if url == self.longpollurl: break
            self.longpollurl = url
            try:
              if url[0] == "/": url = "http://" + self.settings.host + ":" + str(self.settings.port) + url
              if url[:7] != "http://": raise Exception("Long poll URL isn't HTTP!")
              parts = url[7:].split("/", 1)
              if len(parts) == 2: path = "/" + parts[1]
              else: path = "/"
              parts = parts[0].split(":")
              if len(parts) != 2: raise Exception("Long poll URL contains host but no port!")
              host = parts[0]
              port = int(parts[1])
              self.core.log("Found long polling URL for %s: %s\n" % (self.settings.name, url), 500, "g")
              self.signals_new_block = True
              self.runcycle += 1
              for i in range(self.settings.longpollconnections):
                thread = Thread(None, self._longpollingworker, "%s_longpolling_%d" % (self.settings.name, i), (host, port, path))
                thread.daemon = True
                thread.start()
            except Exception as e:
              self.core.log("Invalid long polling URL for %s: %s (%s)\n" % (self.settings.name, url, str(e)), 200, "y")
            break
        if self.signals_new_block and not lpfound:
          self.runcycle += 1
          self.signals_new_block = False
    return self._build_jobs(response, data, now)
      
      
  def _nonce_found(self, job, data, nonce, noncediff):
    req = json.dumps({"method": "getwork", "params": [hexlify(data).decode("ascii")], "id": 0}).encode("utf_8")
    headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions,
               "Content-type": "application/json", "Content-Length": len(req)}
    if self.auth != None: headers["Authorization"] = self.auth
    with self.uploadconnlock:
      try:
        if not self.uploadconn: self.uploadconn = http_client.HTTPConnection(self.settings.host, self.settings.port, True, self.settings.sendsharetimeout)
        self.uploadconn.request("POST", self.settings.path, req, headers)
        response = self.uploadconn.getresponse()
        rdata = response.read()
      except:
        self.uploadconn = None
        raise
    rdata = json.loads(rdata.decode("utf_8"))
    if rdata["result"] == True: return True
    if rdata["error"] != None: return rdata["error"]
    headers = response.getheaders()
    for h in headers:
      if h[0].lower() == "x-reject-reason":
        return h[1]


  def _longpollingworker(self, host, port, path):
    runcycle = self.runcycle
    tries = 0
    starttime = time.time()
    conn = None
    while True:
      if self.runcycle > runcycle: return
      try:
        if not conn: conn = http_client.HTTPConnection(host, port, True, self.settings.longpolltimeout)
        elif conn.sock: conn.sock.settimeout(self.settings.longpolltimeout)
        headers = {"User-Agent": self.useragent, "X-Mining-Extensions": self.extensions, "Connection": "Keep-Alive"}
        if self.auth != None: headers["Authorization"] = self.auth
        conn.request("GET", path, None, headers)
        conn.sock.settimeout(self.settings.longpollresponsetimeout)
        response = conn.getresponse()
        if self.runcycle > runcycle: return
        data = response.read()
        jobs = self._build_jobs(response, data, time.time() - 1, True)
        if not jobs:
          self.core.log("%s: Got empty long poll response\n" % self.settings.name, 500)
          continue
        self._push_jobs(jobs)
        self.core.log("%s: Got %d jobs from long poll response\n" % (self.settings.name, len(jobs)), 500)
      except:
        conn = None
        self.core.log("%s long poll failed: %s\n" % (self.settings.name, traceback.format_exc()), 200, "y")
        tries += 1
        if time.time() - starttime >= 60: tries = 0
        if tries > 5: time.sleep(30)
        else: time.sleep(1)
        starttime = time.time()
        
        
  def _build_jobs(self, response, data, now, ignoreempty = False):
    roll_ntime = 1
    expiry = 60
    isp2pool = False
    headers = response.getheaders()
    for h in headers:
      if h[0].lower() == "x-is-p2pool" and h[1].lower() == "true": isp2pool = True
      elif h[0].lower() == "x-roll-ntime" and h[1] and h[1].lower() != "n":
        roll_ntime = 60
        parts = h[1].split("=", 1)
        if parts[0].strip().lower() == "expire":
          try: roll_ntime = int(parts[1])
          except: pass
        expiry = roll_ntime
    if isp2pool: expiry = 60
    self.stats.supports_rollntime = roll_ntime > 1
    response = data.decode("utf_8")
    if len(response) == 0 and ignoreempty: return
    response = json.loads(response)
    data = unhexlify(response["result"]["data"].encode("ascii"))
    target = unhexlify(response["result"]["target"].encode("ascii"))
    try: identifier = int(response["result"]["identifier"])
    except: identifier = None
    midstate = Job.calculate_midstate(data)
    prefix = data[:68]
    timebase = struct.unpack(">I", data[68:72])[0]
    suffix = data[72:]
    return [Job(self.core, self, now + expiry - self.settings.expirymargin, prefix + struct.pack(">I", timebase + i) + suffix, target, midstate, identifier) for i in range(roll_ntime)]
  