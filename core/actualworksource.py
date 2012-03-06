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
from threading import RLock
from .baseworksource import BaseWorkSource
from .dummyblockchain import DummyBlockchain



class ActualWorkSource(BaseWorkSource):

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

    # Initialize work source state
    self.signals_new_block = None
    self.epoch = 0
    self.errors = 0
    self.lockoutend = 0
    self.estimated_jobs = 1
    
      
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
    
  
  def start(self):
    with self.start_stop_lock:
      super(ActualWorkSource, self).start()
      self.epoch = 0
      self.errors = 0
      self.lockoutend = 0
      self.estimated_jobs = 1

  
  def get_blockchain(self):
    if isinstance(self.blockchain, DummyBlockchain): return None
    return self.blockchain
    
  
  def set_blockchain(self, blockchain = None):
    if self.blockchain: self.blockchain.remove_work_source(self)
    self.blockchain = blockchain
    if not self.blockchain: self.blockchain = DummyBlockchain(self.core)
    if self.blockchain: self.blockchain.add_work_source(self)
    
    
  def _is_locked_out(self):
    return time.clock() <= self.lockoutend
    
      
  def _handle_success(self):
    with self.statelock: self.errors = 0

    
  def _handle_error(self):
    with self.statelock:
      self.errors += 1
      if self.errors >= self.settings.errorlimit:
        lockout = min(self.settings.errorlockout_factor + self.errors, self.settings.errorlockout_max)
        self.lockoutend = max(self.lockoutend, time.clock() + lockout)

    
  def _handle_stale(self):
    with self.statelock:
      self.lockoutend = max(self.lockoutend, time.clock() + self.settings.stalelockout)
      