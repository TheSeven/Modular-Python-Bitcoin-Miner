#!/usr/bin/env python


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


#####################################
# Modular Python Bitcoin Miner Core #
#####################################

# Module configuration options:
#   bufferseconds: Work buffer size in seconds (default: 50)
#   getworktimeout: Work source response timeout in seconds (default: 2)
#   sendsharetimeout: Share upload timeout in seconds (default: 10)
#   longpolltimeout: Long poll connection inactivity timeout in seconds (default: 900)
#   longpollgrouptime: Long poll aggregation timeout in seconds (default: 30)
#   getworkbias: Bias (in MHashes) that is credited to the work source for every work
#                request (default: -1). This punishes work sources which cancel their
#                work very often, but the default value effectively disables this
#                behavior. This needs to be negative (non-zero) though, in order
#                to ensure that work requests are distributed evenly between work
#                sources during startup.
#   longpollkillbias: Bias (in MHashes) that is credited to the work source for every
#                     piece of work that was invalidated by a long poll (default: 0).
#                     This is used to compensate for anomalies caused by getworkbias.
#   getworkfailbias: Bias (in MHashes) that is credited to the work source for every
#                    failed work request (default: -3000). This punishes work source
#                    downtime in general.
#   jobstartbias: Bias (in MHashes) that is credited to the work source everytime
#                 a job of that work source starts being processed on a worker (default: 0).
#   jobfinishbias: Bias (in MHashes) that is credited to the work source everytime
#                  a job of that work source ends being processed on a worker (default: 0).
#   sharebias: Bias (in MHashes) that is multiplied with the difficulty and credited
#              to the work source for each found share (default: 4000). This rewards
#              work sources with high efficiency. Keep it near the default value to
#              ensure that work sources which produce junk work (that never yields
#              shares) can not consume much hashing power.
#   uploadfailbias: Bias (in MHashes) that is and credited to the work source for
#                   each share upload retry (default: -100). Because a huge bias
#                   doesn't keep a work source from retrying to upload the share,
#                   you should keep this relatively low to ensure that the work
#                   source will be used again when it pops back to life. Work source
#                   downtime should be punished using getjobfailbias instead.
#   stalebias: Bias (in MHashes) that is multiplied by the difficulty and credited
#              to the work source for each stale share (default: -15000). With the
#              default settings this will half the work source's hashing power at
#              a stale rate of about 2%.
#   biasdecay: Decay factor that is multiplied onto all work sources' bias on every
#              getwork on any work source (default: 0.9995). Helps ensuring that
#              work sources will be favored after they recover from temporary
#              failures until they have caught up with the configured priority.


import os
import sys
import time
import datetime
import threading
import traceback
import struct
import binascii
import traceback
try: import queue
except ImportError: import Queue as queue

class OutputRedirector(object):
  def __init__(self, miner, flags = ""):
    self.miner = miner
    self.flags = flags
    
  def write(self, data):
    self.miner.log(data, self.flags)
    
  def flush(self): pass
        
class Blockchain(object):
  def __init__(self, miner):
    self.miner = miner
    self.lastlongpoll = time.time() - self.miner.longpollgrouptime
    self.longpollepoch = 0

class Miner(object):
  def __init__(self, config):
    self.useragent = "Modular Python Bitcoin Miner v0.0.4alpha"
    self.config = config
    self.logqueue = queue.Queue()

  def log(self, str, format = ""):
    self.logqueue.put((datetime.datetime.now(), str, format))
    
  def logger(self):
    while True:
      (timestamp, str, format) = self.logqueue.get()
      datestr = ""
      if self.loglf: datestr = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + ": "
      with self.conlock:
        for i in self.interfaces:
          for line in str.splitlines(True):
            i.message(datestr, line, format)
        self.loglf = str[-1:] == "\n"
      self.logqueue.task_done()
      
  def uncaughthandler(self, type, value, traceback):
    self.log("Uncaught exception: %s\n" % traceback.format_exception(type, value, traceback), "rB")

  def run(self):
    self.conlock = threading.RLock()
    self.queuelock = threading.RLock()
    self.fetcherlock = threading.RLock()
    self.bufferseconds = getattr(self.config, "bufferseconds", 50)
    self.getworktimeout = getattr(self.config, "getworktimeout", 2)
    self.sendsharetimeout = getattr(self.config, "sendsharetimeout", 10)
    self.longpolltimeout = getattr(self.config, "longpolltimeout", 900)
    self.longpollgrouptime = getattr(self.config, "longpollgrouptime", 30)
    self.getworkbias = getattr(self.config, "getworkbias", -1)
    self.getworkfailbias = getattr(self.config, "getworkfailbias", -3000)
    self.longpollkillbias = getattr(self.config, "longpollkillbias", 0)
    self.jobstartbias = getattr(self.config, "jobstartbias", 0)
    self.jobfinishbias = getattr(self.config, "jobfinishbias", 0)
    self.sharebias = getattr(self.config, "sharebias", 4000)
    self.uploadfailbias = getattr(self.config, "uploadfailbias", -100)
    self.stalebias = getattr(self.config, "stalebias", -15000)
    self.biasdecay = getattr(self.config, "biasdecay", 0.9995)
    self.queue = queue.Queue()
    self.queuelength = 3
    self.jobspersecond = 0.1
    self.mhps = 0
    self.fetchersrunning = 0
    self.loglf = True
    self.interfaces = []
    self.pools = []
    self.workers = []
    for i in config.interfaces:
      self.interfaces.append(i["type"](miner, i))
    if len(self.interfaces) == 0: raise Exception("No user interfaces defined!")
    self.loggerthread = threading.Thread(None, self.logger, "logger")
    self.loggerthread.daemon = True
    self.loggerthread.start()
    self.log("%s, Copyright (C) 2011-2012 Michael Sparmann (TheSeven)\n" % self.useragent, "B")
    self.log("Modular Python Bitcoin Miner comes with ABSOLUTELY NO WARRANTY.\n")
    self.log("This is free software, and you are welcome to redistribute it under certain conditions.\n")
    self.log("See included file COPYING_GPLv2.txt for details.\n")
    self.log("Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh or,\n", "y")
    self.log("even better, donating a small share of your hashing power if you want\n", "y")
    self.log("to support further development of the Modular Python Bitcoin Miner.\n", "y")
    sys.stdout = OutputRedirector(self)
    sys.stderr = OutputRedirector(self, "rB")
    for b in config.blockchains:
      blockchain = Blockchain(self)
      for p in b["pools"]:
        self.pools.append(p["type"](miner, blockchain, p))
    if len(self.pools) == 0: raise Exception("No pools defined!")
    self.adjustfetchers()
    for w in config.workers:
      self.workers.append(w["type"](miner, w))
    if len(self.workers) == 0: raise Exception("No workers defined!")
    while True: time.sleep(100)

  def adjustfetchers(self, offset = 0):
    with self.fetcherlock:
      while self.queuelength + offset - self.queue.qsize() - self.fetchersrunning > 0:
        self.spawnfetcher()

  def spawnfetcher(self):
    with self.fetcherlock:
      self.fetchersrunning = self.fetchersrunning + 1
      queuedelay = self.queuelength / self.jobspersecond
      while True:
        now = time.time()
        best = None
        pool = None
        for p in self.pools:
          p.score = p.score * self.biasdecay
          excessmhashes = p.mhashes - ((now - p.starttime) + queuedelay) * p.hashrate
          score = excessmhashes - p.score
          if excessmhashes - max(0, p.score) >= 0:
            if p.priority > 0: score = max(0, score / p.priority)
            else: score = "inf"
          if now >= p.blockeduntil and (best == None or score < best):
            best = score
            pool = p
        if pool != None:
          pool.score = pool.score + self.getworkbias
          thread = threading.Thread(None, self.fetcher, pool.name + "_fetcher", kwargs = {"pool": pool})
          thread.daemon = True
          thread.start()
          break
        time.sleep(0.1)

  def fetcher(self, pool):
    with self.queuelock:
      if (time.time() - pool.blockchain.lastlongpoll) > self.longpollgrouptime:
        pool.longpollepoch = pool.blockchain.longpollepoch
      epoch = pool.longpollepoch
      if epoch < pool.blockchain.longpollepoch:
        pool.blockeduntil = pool.blockchain.lastlongpoll + self.longpollgrouptime
        with self.fetcherlock:
          self.fetchersrunning = self.fetchersrunning - 1
          self.adjustfetchers()
        with pool.statlock: pool.score = pool.score - self.getworkbias
        return
    job = None
    try:
      with pool.statlock: pool.requests = pool.requests + 1
      job = pool.getwork()
    except Exception as e:
      self.log("Error while requesting job from %s: %s\n" % (pool.name, e), "rB")
      with pool.statlock:
        pool.failedreqs = pool.failedreqs + 1
        pool.score = pool.score + self.getworkfailbias
      with self.queuelock:
        pool.blockeduntil = time.time() + 3
    if job != None:
      self.queuelock.acquire()
      if epoch == pool.blockchain.longpollepoch:
        self.queue.put(job)
        self.queuelock.release()
      else:
        self.queuelock.release()
        with pool.statlock:
          pool.longpollkilled = pool.longpollkilled + 1
          pool.score = pool.score + self.longpollkillbias
      pool.difficulty = 65535.0 * 2**48 / struct.unpack("<Q", job.target[-12:-4])[0]
    with self.fetcherlock:
      self.fetchersrunning = self.fetchersrunning - 1
      self.adjustfetchers()
    
  def calculatehashrate(self, children):
    mhps = 0
    jobspersec = 0
    for child in children:
      (childmhps, childjobspersec) = self.calculatehashrate(child.children)
      mhps = mhps + child.mhps + childmhps
      jobspersec = jobspersec + child.jobspersecond + childjobspersec
    return (mhps, jobspersec)

  def updatehashrate(self, worker):
    (mhps, jobspersec) = self.calculatehashrate(self.workers)
    self.mhps = mhps
    self.jobspersecond = jobspersec
    self.queuelength = max(1, round(jobspersec * self.bufferseconds))
    self.adjustfetchers()

  def getjob(self, worker):
    job = self.queue.get()
    self.adjustfetchers()
    with job.pool.statlock:
      job.pool.jobsaccepted = job.pool.jobsaccepted + 1
      job.pool.score = job.pool.score + self.jobstartbias
    self.log(worker.name + ": Mining %s:%s:%s\n" % (job.pool.name, binascii.hexlify(job.state).decode("ascii"), binascii.hexlify(job.data[64:76]).decode("ascii")))
    return job

  def newblock(self, job):
    with self.queuelock:
      job.pool.longpollepoch = job.pool.longpollepoch + 1
      if job.pool.longpollepoch >= job.pool.blockchain.longpollepoch:
        job.pool.blockeduntil = time.time()
      if job.pool.longpollepoch > job.pool.blockchain.longpollepoch:
        job.pool.blockchain.lastlongpoll = time.time()
        job.pool.blockchain.longpollepoch = job.pool.longpollepoch
        for w in self.workers:
          try: w.cancel(job.pool.blockchain)
          except: pass
        save = []
        while True:
          try:
            j = self.queue.get(False)
            if j.pool.blockchain != job.pool.blockchain: save.append(j)
            else:
              with j.pool.statlock:
                j.pool.longpollkilled = j.pool.longpollkilled + 1
                j.pool.score = j.pool.score + self.longpollkillbias
          except: break
        for j in save: self.queue.put(j)
        with job.pool.statlock:
          job.pool.requests = job.pool.requests + 1
          job.pool.score = job.pool.score + self.getworkbias
          if self.queue.qsize() <= self.queuelength * 1.5:
            self.queue.put(job)
          else:
            job.pool.longpollkilled = job.pool.longpollkilled + 1
            job.pool.score = job.pool.score + self.longpollkillbias
          job.pool.difficulty = 65535.0 * 2**48 / struct.unpack("<Q", job.target[-12:-4])[0]
    self.adjustfetchers()
    self.log("Long polling: %s indicates that a new block was found\n" % job.pool.name, "B")
    
  def collectstatistics(self, children):
    statistics = []
    for child in children:
      childstats = self.collectstatistics(child.children)
      statistics.append(child.getstatistics(childstats))
    return statistics

  def calculatefieldsum(self, children, field):
    sum = 0
    for child in children: sum = sum + child[field]
    return sum

  def calculatefieldavg(self, children, field):
    if len(children) == 0: return 0
    sum = 0
    count = 0
    for child in children:
      sum = sum + child[field]
      count = count + 1
    return 1. * sum / count

if __name__ == "__main__":
  configfile = "default_config"
  if os.path.isfile("config.py"): configfile = "config"
  if len(sys.argv) == 2 and sys.argv[1] != "": configfile = sys.argv[1]
  if configfile[-3:] == ".py": configfile = configfile[:-3]
  exec("import " + configfile + " as config")
  miner = Miner(config)
  try:
    miner.run()
  except KeyboardInterrupt:
    miner.log("Terminated by Ctrl+C\n", "rB")
    miner.logqueue.join()
    exit(0)
  except:
    miner.log(traceback.format_exc(), "rB")
    miner.logqueue.join()
    exit(1)

