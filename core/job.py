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



import struct
from binascii import hexlify
from threading import Thread
from .sha256 import SHA256



class Job(object):

  
  def __init__(self, core, worksource, epoch, expiry, data, target, midstate = None):
    self.core = core
    self.worksource = worksource
    self.epoch = epoch
    self.expiry = expiry
    self.data = data
    self.target = target
    self.difficulty = 65535. * 2**48 / struct.unpack("<Q", self.target[-12:-4])[0]
    with self.worksource.stats.lock: self.worksource.stats.difficulty = self.difficulty
    if midstate: self.midstate = midstate
    else: self.midstate = Job.calculate_midstate(data)
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
    if self.worker:
      with self.worksource.stats.lock:
        self.worksource.stats.ghashes += (2**32 - self.hashes_remaining) / 1000000000.
      with self.worker.stats.lock:
        self.worker.stats.ghashes += (2**32 - self.hashes_remaining) / 1000000000.
    
    
  def hashes_processed(self, hashes):
    self.hashes_remaining -= hashes
    
    
  def set_worker(self, worker):
    self.worker = worker
    self.core.log("Mining %s:%s on %s\n" % (self.worksource.settings.name, hexlify(self.data[:76]), worker.settings.name), 400)
    with self.worker.stats.lock: self.worker.stats.jobsaccepted += 1
    with self.worksource.stats.lock: self.worksource.stats.jobsaccepted += 1
    
    
  def nonce_found(self, nonce):
    self.core.log("%s found share: %s:%s:%s\n" % (self.worker.settings.name, self.worksource.settings.name, hexlify(self.data[:76]).decode("ascii"), hexlify(nonce).decode("ascii")), 350, "g")
    data = self.data[:76] + nonce + self.data[80:]
    hash = Job.calculate_hash(data)
    if hash[-4:] != b"\0\0\0\0":
      self.core.log("%s sent K-not-zero share %s\n" % (self.worker.settings.name, hexlify(nonce).decode("ascii")), 200, "yB")
      with self.worker.stats.lock: self.worker.stats.sharesinvalid += 1
      return
    noncediff = 65535. * 2**48 / struct.unpack("<Q", hash[-12:-4])[0]
    if hash[::-1] > self.target[::-1]:
      self.core.log("Share %s (difficulty %.5f) didn't meet difficulty %.5f\n" % (hexlify(nonce).decode("ascii"), noncediff, self.difficulty), 300, "g")
      return
    self.worksource.nonce_found(self, data, nonce, noncediff)
    pass
    
    
  def nonce_handled_callback(self, nonce, noncediff, result):
    if result == True:
      self.core.log("%s accepted share %s (difficulty %.5f)\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff), 250, "gB")
      with self.worker.stats.lock: self.worker.stats.sharesaccepted += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesaccepted += self.difficulty
    else:
      if result == False or result == None or len(result) == 0: result = "Unknown reason"
      self.core.log("%s rejected share %s (difficulty %.5f): %s\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff, result), 200, "y")
      with self.worker.stats.lock: self.worker.stats.sharesrejected += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesrejected += self.difficulty


  def cancel(self):
    self.canceled = True
    self.core.workqueue.remove_job(self)
    if self.worker:
      self.worker.notify_canceled(self)
      with self.worker.stats.lock: self.worker.stats.jobscanceled += 1
      with self.worksource.stats.lock: self.worksource.stats.jobscanceled += 1
      
      
  @staticmethod
  def calculate_midstate(data):
    return struct.pack("<8I", *struct.unpack(">8I", SHA256.hash(struct.pack("<16I", *struct.unpack(">16I", data[:64])), False)))
      
      
  @staticmethod
  def calculate_hash(data):
    return SHA256.hash(SHA256.hash(struct.pack("<20I", *struct.unpack(">20I", data[:80]))))

    
    
class ValidationJob(object):

  
  def __init__(self, core, data, nonce, midstate = None):
    self.core = core
    self.data = data
    if midstate: self.midstate = midstate
    else: self.midstate = SHA256.hash(data[:64], False)
    self.nonce = nonce
    self.worker = None
    
    
  def hashes_processed(self, hashes):
    pass
    
    
  def nonce_found(self, nonce):
    pass
   
   
  def destroy(self):
    pass
