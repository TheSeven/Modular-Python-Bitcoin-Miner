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


#######################################
# Bitcoin JSON RPC work source module #
#######################################

# Module configuration options:
#   name: Display name for this work source (default: host name)
#   host: Host name of the JSON RPC server (mandantory)
#   port: HTTP port number of the JSON RPC server (default: 8332)
#   path: HTTP path for getwork requests (default: "/")
#   username: HTTP authentication user name (default: no authentication)
#   password: HTTP authentication password (default: empty)
#   useragent: User agent string to be sent to the JSON RPC server
#              (default: "Modular Python Bitcoin Miner v0.0.2 (bcjsonrpc.JSONRPCPool v0.0.2)")
#   hashrate: Base hashrate for this pool (in MHash/s, default: 0)
#   priority: Priority of the work source (hashrate that's available in excess of the hashrate
#             options of all pools will be distributed proportionally to this value, default: 1)
#   getworktimeout: Timeout (in seconds) for getwork requests (default: global setting)
#   sendsharetimeout: Share upload timeout in seconds (default: global setting)
#   longpolltimeout: Long poll connection inactivity timeout (default: global setting)


import sys
import common
import base64
import datetime
import json
import threading
import curses
import binascii
import time
try: import http.client as http_client
except ImportError: import httplib as http_client

class JSONRPCPool(object):
  def __init__(self, miner, blockchain, dict):
    self.__dict__ = dict
    self.miner = miner
    self.blockchain = blockchain
    self.children = []
    if not hasattr(self, "host"): raise Exception("Missing attribute: host")
    self.useragent = self.miner.useragent + " (bcjsonrpc.JSONRPCPool v0.0.1)"
    self.getworktimeout = getattr(self, "getworktimeout", self.miner.getworktimeout)
    self.sendsharetimeout = getattr(self, "sendsharetimeout", self.miner.sendsharetimeout)
    self.longpolltimeout = getattr(self, "longpolltimeout", self.miner.longpolltimeout)
    self.priority = getattr(self, "priority", 1)
    self.hashrate = getattr(self, "hashrate", 0)
    self.username = getattr(self, "username", "")
    self.password = getattr(self, "password", "")
    if self.username == "" and self.password == "": self.auth = None
    else: self.auth = "Basic " + base64.b64encode((self.username + ":" + self.password).encode("utf_8")).decode("ascii")
    self.port = getattr(self, "port", 8332)
    self.path = getattr(self, "path", "/")
    self.name = getattr(self, "name", self.host)
    self.statlock = threading.RLock()
    self.longpolling = None
    self.longpollepoch = 0
    self.requests = 0
    self.failedreqs = 0
    self.uploadretries = 0
    self.longpollkilled = 0
    self.jobsaccepted = 0
    self.accepted = 0
    self.rejected = 0
    self.score = 0
    self.mhashes = 0
    self.starttime = datetime.datetime.utcnow()
    self.blockeduntil = datetime.datetime.utcnow()
    self.difficulty = 0

  def getstatistics(self, childstats):
    with self.statlock:
      statistics = { \
        "name": self.name, \
        "children": childstats, \
        "longpolling": self.longpolling, \
        "difficulty": self.difficulty, \
        "requests": self.requests, \
        "failedreqs": self.failedreqs, \
        "jobsaccepted": self.jobsaccepted, \
        "longpollkilled": self.longpollkilled, \
        "accepted": self.accepted, \
        "rejected": self.rejected, \
        "uploadretries": self.uploadretries, \
        "starttime": self.starttime, \
        "mhashes": self.mhashes, \
        "score": self.score, \
      }
    return statistics

  def sendresult(self, job, data, nonce, difficulty, worker):
    uploader = threading.Thread(None, self.uploadresult, self.name + "_uploadresult_" + binascii.hexlify(nonce).decode("ascii"), (job, data, nonce, difficulty, worker))
    uploader.daemon = True
    uploader.start()

  def uploadresult(self, job, data, nonce, difficulty, worker):
    while True:
      try:
        conn = http_client.HTTPConnection(self.host, self.port, True, self.sendsharetimeout)
        req = json.dumps({"method": "getwork", "params": [binascii.hexlify(data).decode("ascii")], "id": 0}).encode("utf_8")
        headers = {"User-Agent": self.useragent, "Content-type": "application/json", "Content-Length": len(req)}
        if self.auth != None: headers["Authorization"] = self.auth
        conn.request("POST", self.path, req, headers)
        response = conn.getresponse()
        rdata = json.loads(response.read().decode("utf_8"))
        if rdata["result"] == True: return job.uploadcallback(nonce, worker, True)
        if rdata["error"] != None: return job.uploadcallback(nonce, worker, rdata["error"])
        headers = response.getheaders()
        for h in headers:
          if h[0].lower() == "x-reject-reason":
            return job.uploadcallback(nonce, worker, h[1])
        return job.uploadcallback(nonce, worker, False)
      except Exception as e:
        self.miner.log("Error while uploading share %s (difficulty %.5f) to %s (%s:%d): %s\n" % (binascii.hexlify(nonce).decode("ascii"), difficulty, self.name, self.host, self.port, e), "rB")
        with self.statlock:
          self.uploadretries = self.uploadretries + 1
          self.score = self.score + self.miner.uploadfailbias
        time.sleep(1)

  def getwork(self):
    conn = http_client.HTTPConnection(self.host, self.port, True, self.getworktimeout)
    req = json.dumps({"method": "getwork", "params": [], "id": 0}).encode("utf_8")
    headers = {"User-Agent": self.useragent, "Content-type": "application/json", "Content-Length": len(req)}
    if self.auth != None: headers["Authorization"] = self.auth
    conn.request("POST", self.path, req, headers)
    response = conn.getresponse()
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
              path = "/" + parts[1]
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
    response = json.loads(response.read().decode("utf_8"))
    state = binascii.unhexlify(response["result"]["midstate"].encode("ascii"))
    data = binascii.unhexlify(response["result"]["data"].encode("ascii"))
    target = binascii.unhexlify(response["result"]["target"].encode("ascii"))
    return common.Job(self.miner, self, self.longpollepoch, state, data, target)

  def longpollingworker(self, host, port, path):
    while True:
      try:
        conn = http_client.HTTPConnection(host, port, True, self.longpolltimeout)
        headers = {"User-Agent": self.useragent}
        if self.auth != None: headers["Authorization"] = self.auth
        conn.request("GET", path, None, headers)
        data = conn.getresponse().read().decode("utf_8")
        response = json.loads(data)
        state = binascii.unhexlify(response["result"]["midstate"].encode("ascii"))
        data = binascii.unhexlify(response["result"]["data"].encode("ascii"))
        target = binascii.unhexlify(response["result"]["target"].encode("ascii"))
        job = common.Job(self.miner, self, self.longpollepoch, state, data, target)
        self.miner.newblock(job)
      except Exception as e:
        self.miner.log("%s long poll failed: %s\n" % (self.name, e), "y")
        time.sleep(3)
        pass
