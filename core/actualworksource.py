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



#################################
# Actual work source base class #
#################################



import time
import traceback
from binascii import hexlify
from threading import RLock, Thread
from .baseworksource import BaseWorkSource
from .blockchain import DummyBlockchain



class ActualWorkSource(BaseWorkSource):

  nonce_found_async = True
  settings = dict(BaseWorkSource.settings, **{
    "errorlimit": {"title": "Error limit", "type": "int", "position": 20000},
    "errorlockout_factor": {"title": "Error lockout factor", "type": "int", "position": 20100},
    "errorlockout_max": {"title": "Error lockout maximum", "type": "int", "position": 20200},
    "stalelockout": {"title": "Stale lockout", "type": "int", "position": 20500},
  })

  def __init__(self, core, state = None):
    super(ActualWorkSource, self).__init__(core, state)
    
    # Find block chain
    self.blockchain = None
    if not "blockchain" in self.state: self.state.blockchain = None
    self.set_blockchain(core.get_blockchain_by_name(self.state.blockchain))
    
    
  def _reset(self):
    super(ActualWorkSource, self)._reset()
    self.signals_new_block = None
    self.errors = 0
    self.lockoutend = 0
    self.estimated_jobs = 1
    self.estimated_expiry = 60
    
      
  def _get_statistics(self, stats, childstats):
    super(ActualWorkSource, self)._get_statistics(stats, childstats)
    stats.signals_new_block = self.signals_new_block
    lockout = self.lockoutend - time.time()
    stats.locked_out = lockout if lockout > 0 else 0
    stats.consecutive_errors = self.errors
    stats.jobs_per_request = self.estimated_jobs
    stats.job_expiry = self.estimated_expiry
    stats.blockchain = self.blockchain
    stats.blockchain_id = self.blockchain.id
    stats.blockchain_name = "None" if isinstance(self.blockchain, DummyBlockchain) else self.blockchain.settings.name


  def destroy(self):
    super(ActualWorkSource, self).destroy()
    if self.blockchain: self.blockchain.remove_work_source(self)
    
    
  def deflate(self):
    # Save block chain name to state
    blockchain = self.get_blockchain()
    if blockchain: self.state.blockchain = blockchain.settings.name
    else: self.state.blockchain = None
    # Let BaseWorkSource handle own deflation
    return super(ActualWorkSource, self).deflate()


  def apply_settings(self):
    super(ActualWorkSource, self).apply_settings()
    if not "errorlimit" in self.settings or not self.settings.errorlimit:
      self.settings.errorlimit = 3
    if not "errorlockout_factor" in self.settings or not self.settings.errorlockout_factor:
      self.settings.errorlockout_factor = 10
    if not "lockout_max" in self.settings or not self.settings.errorlockout_max:
      self.settings.errorlockout_max = 500
    if not "stalelockout" in self.settings: self.settings.stalelockout = 25
    
  
  def get_blockchain(self):
    if isinstance(self.blockchain, DummyBlockchain): return None
    return self.blockchain
    
  
  def set_blockchain(self, blockchain = None):
    if self.blockchain: self.blockchain.remove_work_source(self)
    self.blockchain = blockchain
    if not self.blockchain: self.blockchain = DummyBlockchain(self.core)
    if self.blockchain: self.blockchain.add_work_source(self)
    
    
  def _is_locked_out(self):
    return time.time() <= self.lockoutend
    
      
  def _handle_success(self, jobs = None):
    with self.statelock:
      self.errors = 0
      if jobs:
        jobcount = len(jobs)
        self.estimated_jobs = jobcount
        self.estimated_expiry = int(jobs[0].expiry - time.time())
        with self.stats.lock: self.stats.jobsreceived += jobcount

    
  def _handle_error(self, upload = False):
    with self.statelock:
      self.errors += 1
      if self.errors >= self.settings.errorlimit:
        lockout = min(self.settings.errorlockout_factor + self.errors, self.settings.errorlockout_max)
        self.lockoutend = max(self.lockoutend, time.time() + lockout)
    with self.stats.lock:
      if upload: self.stats.uploadretries += 1
      else: self.stats.failedjobreqs += 1

    
  def _handle_stale(self):
    with self.statelock:
      self.lockoutend = max(self.lockoutend, time.time() + self.settings.stalelockout)
      
      
  def _push_jobs(self, jobs):
    self._handle_success(jobs)
    if jobs: self.core.workqueue.add_jobs(jobs)
      
      
  def get_job(self):
    if not self.started or not self.settings.enabled or self._is_locked_out(): return []
    try:
      with self.stats.lock: self.stats.jobrequests += 1
      jobs = self._get_job()
      if jobs:
        self._handle_success(jobs)
        self.core.log("%s: Got %d jobs\n" % (self.settings.name, len(jobs)), 500)
      else: self._handle_error()
      return jobs
    except:
      self.core.log("%s: Error while fetching job: %s\n" % (self.settings.name, traceback.format_exc()), 200, "y")
      self._handle_error()
      return []
  

  def nonce_found(self, job, data, nonce, noncediff):
    if self.nonce_found_async:
      thread = Thread(None, self.nonce_found_thread, self.settings.name + "_nonce_found_" + hexlify(nonce).decode("ascii"), (job, data, nonce, noncediff))
      thread.daemon = True
      thread.start()
    else: self.none_found_thread(job, data, nonce, noncediff)

    
  def nonce_found_thread(self, job, data, nonce, noncediff):
    tries = 0
    while True:
      try:
        result = self._nonce_found(job, data, nonce, noncediff)
        self._handle_success()
        return job.nonce_handled_callback(nonce, noncediff, result)
      except:
        self.core.log("Error while sending share %s (difficulty %.5f) to %s: %s\n" % (hexlify(nonce).decode("ascii"), noncediff, self.settings.name, traceback.format_exc()), 200, "y")
        tries += 1
        self._handle_error(True)
        time.sleep(min(30, tries))
        