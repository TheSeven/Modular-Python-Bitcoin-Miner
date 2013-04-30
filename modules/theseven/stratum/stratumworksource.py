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



##############################
# Stratum work source module #
##############################



import sys
import socket
import time
import json
import struct
import traceback
from binascii import hexlify, unhexlify
from threading import Thread, RLock, Condition
from hashlib import sha256
from core.actualworksource import ActualWorkSource
from core.job import Job



class StratumWorkSource(ActualWorkSource):
  
  version = "theseven.stratum work source v0.1.0"
  default_name = "Untitled Stratum work source"
  settings = dict(ActualWorkSource.settings, **{
    "connecttimeout": {"title": "Connect timeout", "type": "float", "position": 19000},
    "responsetimeout": {"title": "Response timeout", "type": "float", "position": 19100},
    "host": {"title": "Host", "type": "string", "position": 1000},
    "port": {"title": "Port", "type": "int", "position": 1010},
    "username": {"title": "User name", "type": "string", "position": 1100},
    "password": {"title": "Password", "type": "password", "position": 1120},
  })
  

  def __init__(self, core, state = None):
    super(StratumWorkSource, self).__init__(core, state)
    self.datalock = RLock()
    self.txnlock = RLock()
    self.wakeup = Condition()
    self.tail = unhexlify(b"00000000000000800000000000000000000000000000000000000000000000000000000000000000000000000000000080020000")
    
    
  def apply_settings(self):
    super(StratumWorkSource, self).apply_settings()
    if not "connecttimeout" in self.settings or not self.settings.connecttimeout:
      self.settings.connecttimeout = 5
    if not "responsetimeout" in self.settings or not self.settings.responsetimeout:
      self.settings.responsetimeout = 5
    if not "host" in self.settings: self.settings.host = ""
    if not "port" in self.settings or not self.settings.port: self.settings.port = 3333
    if not "username" in self.settings: self.settings.username = ""
    if not "password" in self.settings: self.settings.password = ""
    if self.started and (self.settings.host != self.host or self.settings.port != self.port or self.settings.username != self.username or self.settings.password != self.password): self.async_restart()

    
  def _reset(self):
    super(StratumWorkSource, self)._reset()
    self.timeoutthread = None
    self.listenerthread = None
    self.data = None
    self.txns = {}
    self.txnid = 1
    self.difficulty = 1
    self._calculate_target()
    
    
  def _start(self):
    super(StratumWorkSource, self)._start()
    self.host = self.settings.host
    self.port = self.settings.port
    self.username = self.settings.username
    self.password = self.settings.password
    if not self.settings.host or not self.settings.port: return
    self.shutdown = False
    self.listenerthread = Thread(None, self._listener, "%s_listener" % self.settings.name)
    self.listenerthread.daemon = True
    self.listenerthread.start()
    self.timeoutthread = Thread(None, self._timeout, "%s_timeout" % self.settings.name)
    self.timeoutthread.daemon = True
    self.timeoutthread.start()
    
    
  def _stop(self):
    self.shutdown = True
    with self.wakeup: self.wakeup.notify()
    if self.timeoutthread: self.timeoutthread.join(3)
    if self.listenerthread: self.listenerthread.join(3)
    super(StratumWorkSource, self)._stop()
    
    
  def _calculate_target(self):
    target = int(0xffff0000000000000000000000000000000000000000000000000000 / self.difficulty)
    self.target = b""
    for i in range(8):
      self.target += struct.pack("<I", target & 0xffffffff)
      target >>= 32    
    
    
  def _get_running_fetcher_count(self):
    return 0, 0
  
  
  def _start_fetcher(self):
    with self.datalock:
      if not self.data or self.shutdown: return False, 0
      extranonce2 = unhexlify((("%%0%dx" % (2 * self.data["extranonce2len"])) % self.data["extranonce2"]).encode("ascii"))
      self.data["extranonce2"] += 1
      coinbase = self.data["coinb1"] + self.data["extranonce1"] + extranonce2 + self.data["coinb2"]
      merkle = sha256(sha256(coinbase).digest()).digest()
      for branch in self.data["merkle_branch"]: merkle = sha256(sha256(merkle + branch).digest()).digest()
      merkle = struct.pack("<8I", *struct.unpack(">8I", merkle))
      ntime = struct.pack(">I", self.data["ntime"] + int(time.time()))
      data = self.data["version"] + self.data["prevhash"] + merkle + ntime + self.data["nbits"] + self.tail
      target = self.data["target"]
      job_id = self.data["job_id"]
    job = Job(self.core, self, time.time() + 60, data, target)
    job._stratum_job_id = job_id
    job._stratum_extranonce2 = hexlify(extranonce2).decode("ascii")
    job._stratum_ntime = hexlify(ntime).decode("ascii")
    self._push_jobs([job], "stratum generator")
    return 1, 1
  
  
  def _txn(self, method, params = None, callback = None, errorcallback = None, timeoutcallback = None, timeout = None):
    if not timeout: timeout = self.settings.responsetimeout
    with self.txnlock:
      if not self.conn: raise Exception("Connection is not active")
      txn = self.txnid
      self.txnid += 1
      self.txns[txn] = {
        "method": method,
        "params": params,
        "timeout": time.time() + timeout,
        "callback": callback,
        "errorcallback": errorcallback,
        "timeoutcallback": timeoutcallback,
      }
      self.connw.write(json.dumps({"id": txn, "method": method, "params": params}) + "\n")
      self.connw.flush()


  def _close_connection(self):
    with self.txnlock:
      try: self.connw.close()
      except: pass
      try: self.connr.close()
      except: pass
      try: self.conn.shutdown()
      except: pass
      try: self.conn.close()
      except: pass
      self.conn = None
    self._cancel_jobs()
      
  
  def _listener(self):
    tries = 0
    starttime = time.time()
    while not self.shutdown:
      try:
        with self.txnlock:
          self.conn = socket.create_connection((self.host, self.port), self.settings.connecttimeout)
          self.conn.settimeout(None)
          if sys.version_info[0] < 3:
            self.connr = self.conn.makefile("r", 1)
            self.connw = self.conn.makefile("w", 1)
          else:
            self.connr = self.conn.makefile("r", buffering = 1, encoding = "utf_8", newline = "\n")
            self.connw = self.conn.makefile("w", buffering = 1, encoding = "utf_8", newline = "\n")
          self._txn("mining.authorize", [self.username, self.password], self._authorized, self._setup_failed, self._setup_timeout)
        while not self.shutdown:
          msgs = json.loads(self.connr.readline())
          if not isinstance(msgs, list): msgs = [msgs]
          for msg in msgs: 
            if "id" in msg and msg["id"]:
              with self.txnlock:
                if not msg["id"] in self.txns:
                  self.core.log(self, "Received unexpected Stratum response: %s\n" % msg, 200, "y")
                  continue
                txn = self.txns[msg["id"]]
                if "error" in msg and msg["error"]:
                  if txn["errorcallback"]: txn["errorcallback"](txn, msg["error"])
                  else: self._default_error_handler(txn, msg["error"])
                elif txn["callback"]: txn["callback"](txn, msg["result"])
                del self.txns[msg["id"]]
            elif msg["method"] == "mining.notify":
              with self.datalock:
                self.data = {
                  "job_id": msg["params"][0],
                  "prevhash": unhexlify(msg["params"][1].encode("ascii")),
                  "coinb1": unhexlify(msg["params"][2].encode("ascii")),
                  "coinb2": unhexlify(msg["params"][3].encode("ascii")),
                  "merkle_branch": [unhexlify(branch.encode("ascii")) for branch in msg["params"][4]],
                  "version": unhexlify(msg["params"][5].encode("ascii")),
                  "nbits": unhexlify(msg["params"][6].encode("ascii")),
                  "ntime": struct.unpack(">I", unhexlify(msg["params"][7].encode("ascii")))[0] - int(time.time()),
                  "extranonce1": self.extranonce1,
                  "extranonce2len": self.extranonce2len,
                  "extranonce2": 0,
                  "difficulty": self.difficulty,
                  "target": self.target,
                }
              self.core.log(self, "Received new job generation data (%sflushing old jobs)\n" % ("" if msg["params"][8] else "not "), 500)
              if msg["params"][8]: self._cancel_jobs()
              self.blockchain.check_job(Job(self.core, self, 0, self.data["version"] + self.data["prevhash"] + b"\0" * 68 + self.data["nbits"] + self.tail, self.target, True))
            elif msg["method"] == "mining.set_difficulty":
              self.difficulty = float(msg["params"][0])
              self._calculate_target()
              self.core.log(self, "Received new job difficulty: %f\n" % self.difficulty, 500)
              self._cancel_jobs()
            else: self.core.log(self, "Received unknown Stratum notification: %s\n" % msg, 300, "y")
      except:
        with self.datalock: self.data = None
        self.core.log(self, "Stratum connection died: %s\n" % (traceback.format_exc()), 200, "r")
        self._close_connection()
        tries += 1
        if time.time() - starttime >= 60: tries = 0
        if tries > 5: time.sleep(30)
        else: time.sleep(1)
        starttime = time.time()


  def _timeout(self):
    with self.wakeup:
      while not self.shutdown:
        with self.txnlock:
          now = time.time()
          for txn in list(self.txns):
            if self.txns[txn]["timeout"] < now:
              if self.txns[txn]["timeoutcallback"]: self.txns[txn]["timeoutcallback"](self.txns[txn], False)
              else: self._default_timeout_handler(self.txns[txn], False)
              del self.txns[txn]
        self.wakeup.wait(1)
      for txn in list(self.txns):
        if self.txns[txn]["timeoutcallback"]: self.txns[txn]["timeoutcallback"](self.txns[txn], True)
        else: self._default_timeout_handler(self.txns[txn], True)
    self._close_connection()
    
    
  def _default_error_handler(txn, error):
    self.core.log(self, "Stratum transaction failed: method=%s, params=%s, error=%s\n" % (txn["method"], txn["params"], error), 200, "y")
    
    
  def _default_timeout_handler(txn, shutdown):
    if shutdown: return
    self.core.log(self, "Stratum transaction timed out: method=%s, params=%s\n" % (txn["method"], txn["params"]), 200, "y")
    
    
  def _subscribed(self, txn, response):
    self.extranonce1 = unhexlify(response[1].encode("ascii"))
    self.extranonce2len = int(response[2])
    self.core.log(self, "Successfully subscribed to Stratum service\n", 400, "g")

  
  def _authorized(self, txn, response):
    self._txn("mining.subscribe", [], self._subscribed, self._setup_failed, self._setup_timeout)
    self.core.log(self, "Successfully authorized Stratum worker %s\n" % self.settings.username, 400, "g")
    
    
  def _setup_failed(self, txn, error):
    self.core.log(self, "Stratum worker authorization failed: %s\n" % error, 200, "r")
    self._close_connection()
    
    
  def _setup_timeout(self, txn, shutdown):
    if shutdown: return
    self.core.log(self, "Stratum worker authorization timed out\n", 200, "r")
    self._close_connection()
    
    
  def _nonce_timeout_err(self, shutdown):
    if shutdown: return "shutting down"
    self._close_connection()
    return "timed out"
        
        
  def nonce_found(self, job, data, nonce, noncediff):
    data = [self.username, job._stratum_job_id, job._stratum_extranonce2, job._stratum_ntime, hexlify(nonce).decode("ascii")]
    submitted = lambda txn, result: job.nonce_handled_callback(nonce, noncediff, result)
    submit_failed = lambda txn, error: job.nonce_handled_callback(nonce, noncediff, error)
    submit_timeout = lambda txn, shutdown: job.nonce_handled_callback(nonce, noncediff, self._nonce_timeout_err(shutdown))
    try: self._txn("mining.submit", data, submitted, submit_failed, submit_timeout)
    except Exception as e: job.nonce_handled_callback(nonce, noncediff, str(e))
