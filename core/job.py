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



#######################
# 4GH nonce range job #
#######################



from .sha256 import SHA256



class Job(object):

  
  def __init__(self, core, worksource, epoch, expiry, data, target, midstate = None):
    self.core = core
    self.worksource = worksource
    self.epoch = epoch
    self.expiry = expiry
    self.data = data
    self.target = target
    if midstate: self.midstate = midstate
    else: self.midstate = SHA256.hash(data[:64], False)
    self.canceled = False
    self.worker = None
    self.hashes_remaining = 2**32
    
    
  def register(self):
    self.worksource.blockchain.add_job(self)
    self.worksource.add_pending_mhashes(-self.hashes_remaining / 1000000.)
    
    
  def destroy(self):
    self.worksource.blockchain.remove_job(self)
    self.core.workqueue.remove_job(self)
    self.worksource.add_pending_mhashes(self.hashes_remaining / 1000000.)
    
    
  def hashes_processed(self, hashes):
    self.hashes_remaining -= hashes
    
    
  def set_worker(self, worker):
    self.worker = worker
    # TODO: Accounting
    
    
  def nonce_found(self, nonce):
    # TODO: Accounting
    pass
    
    
  def cancel(self):
    self.canceled = True
    self.core.workqueue.remove_job(self)
    if self.worker: self.worker.notify_canceled(self)
    # TODO: Accounting
    
    