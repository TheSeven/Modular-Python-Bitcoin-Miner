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



#################################
# Actual work source base class #
#################################



import time
from threading import RLock
from .baseworksource import BaseWorkSource



class ActualWorkSource(BaseWorkSource):


  def __init__(self, core, state = None):
    super().__init__(core, state)
    
    # Find block chain
    if not "blockchain" in self.state: self.state.blockchain = None
    self.blockchain = core.get_blockchain_by_name(self.state.blockchain)

    # Initialize work source state
    self.signals_new_block = None
    self.block_epoch = 0
    self.canceluntil = time.time()
    
      
  def deflate(self):
    # Save block chain name to state
    if self.blockchain: self.state.blockchain = self.blockchain.settings.name
    else: self.state.blockchain = None
    # Let BaseWorkSource handle own deflation
    return super().deflate()


  def apply_settings(self):
    super().apply_settings()
    if not "errorlimit" in self.settings or not self.settings.errorlimit:
      self.settings.errorlimit = 3
    if not "errorlockout_factor" in self.settings or not self.settings.errorlockout_factor:
      self.settings.errorlockout_factor = 10
    if not "lockout_max" in self.settings or not self.settings.errorlockout_max:
      self.settings.errorlockout_max = 500
    if not "stalelockout" in self.settings: self.settings.stalelockout = 25
    
  
  def set_blockchain(self, blockchain = None):
    self.blockchain = blockchain
