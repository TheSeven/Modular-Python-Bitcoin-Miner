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
import traceback
from binascii import hexlify
from threading import Thread
from .sha256 import SHA256
from hashlib import sha256



class Job(object):

  
  def __init__(self, core, worksource, expiry, data, target, midstate = None, identifier = None):
    self.core = core
    self.worksource = worksource
    self.blockchain = worksource.blockchain
    self.expiry = expiry
    self.data = data
    self.target = target
    self.identifier = identifier
    self.prevhash = data[4:36]
    self.difficulty = 65535. * 2**48 / struct.unpack("<Q", self.target[-12:-4])[0]
    with self.worksource.stats.lock: self.worksource.stats.difficulty = self.difficulty
    if midstate: self.midstate = midstate
    else: self.midstate = Job.calculate_midstate(data)
    self.canceled = False
    self.destroyed = False
    self.worker = None
    self.starttime = None
    self.hashes_remaining = 2**32
    
    
  def register(self):
    self.worksource.add_job(self)
    self.blockchain.add_job(self)
    self.worksource.add_pending_mhashes(-self.hashes_remaining / 1000000.)
    self.core.event(500, self.worksource, "registerjob", None, None, None, self.worksource, self.blockchain, self)
    
    
  def destroy(self):
    if self.destroyed: return
    self.destroyed = True
    self.worksource.remove_job(self)
    self.blockchain.remove_job(self)
    self.core.workqueue.remove_job(self)
    self.worksource.add_pending_mhashes(self.hashes_remaining / 1000000.)
    self.core.event(700, self.worksource, "destroyjob", None, None, self.worker, self.worksource, self.blockchain, self)
    if self.worker:
      hashes = 2**32 - self.hashes_remaining
      self.core.event(400, self.worker, "hashes_calculated", hashes, None, self.worker, self.worksource, self.blockchain, self)
      ghashes = hashes / 1000000000.
      self.core.stats.ghashes += ghashes
      with self.worksource.stats.lock:
        self.worksource.stats.ghashes += ghashes
      with self.worker.stats.lock:
        self.worker.stats.ghashes += ghashes
    
    
  def hashes_processed(self, hashes):
    self.hashes_remaining -= hashes
    
    
  def set_worker(self, worker):
    self.worker = worker
    self.core.log(worker, "Mining %s:%s\n" % (self.worksource.settings.name, hexlify(self.data[:76]).decode("ascii")), 400)
    self.core.event(450, self.worker, "acquirejob", None, None, self.worker, self.worksource, self.blockchain, self)
    with self.worker.stats.lock: self.worker.stats.jobsaccepted += 1
    with self.worksource.stats.lock: self.worksource.stats.jobsaccepted += 1
    
    
  def nonce_found(self, nonce, ignore_invalid = False):
    nonceval = struct.unpack("<I", nonce)[0]
    self.core.event(400, self.worker, "noncefound", nonceval, None, self.worker, self.worksource, self.blockchain, self)
    data = self.data[:76] + nonce + self.data[80:]
    hash = Job.calculate_hash(data)
    if hash[-4:] != b"\0\0\0\0":
      if ignore_invalid: return False
      self.core.log(self.worker, "Got K-not-zero share %s\n" % (hexlify(nonce).decode("ascii")), 200, "yB")
      with self.worker.stats.lock: self.worker.stats.sharesinvalid += 1
      self.core.event(300, self.worker, "nonceinvalid", nonceval, None, self.worker, self.worksource, self.blockchain, self)
      return False
    self.core.log(self.worker, "Found share: %s:%s:%s\n" % (self.worksource.settings.name, hexlify(self.data[:76]).decode("ascii"), hexlify(nonce).decode("ascii")), 350, "g")
    noncediff = 65535. * 2**48 / struct.unpack("<Q", hash[-12:-4])[0]
    self.core.event(450, self.worker, "noncevalid", nonceval, str(noncediff), self.worker, self.worksource, self.blockchain, self)
    if hash[::-1] > self.target[::-1]:
      self.core.event(350, self.worksource, "noncefaileddiff", nonceval, str(self.difficulty), self.worker, self.worksource, self.blockchain, self)
      self.core.log(self.worker, "Share %s (difficulty %.5f) didn't meet difficulty %.5f\n" % (hexlify(nonce).decode("ascii"), noncediff, self.difficulty), 300, "g")
      return True
    self.worksource.nonce_found(self, data, nonce, noncediff)
    return True
    
    
  def nonce_handled_callback(self, nonce, noncediff, result):
    nonceval = struct.unpack("<I", nonce)[0]
    if result == True:
      self.core.log(self.worker, "%s accepted share %s (difficulty %.5f)\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff), 250, "gB")
      with self.worker.stats.lock: self.worker.stats.sharesaccepted += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesaccepted += self.difficulty
      self.core.event(350, self.worksource, "nonceaccepted", nonceval, None, self.worker, self.worksource, self.blockchain, self)
    else:
      if result == False or result == None or len(result) == 0: result = "Unknown reason"
      self.core.log(self.worker, "%s rejected share %s (difficulty %.5f): %s\n" % (self.worksource.settings.name, hexlify(nonce).decode("ascii"), noncediff, result), 200, "y")
      with self.worker.stats.lock: self.worker.stats.sharesrejected += self.difficulty
      with self.worksource.stats.lock: self.worksource.stats.sharesrejected += self.difficulty
      self.core.event(300, self.worksource, "noncerejected", nonceval, result, self.worker, self.worksource, self.blockchain, self)


  def cancel(self, graceful = False):
    self.canceled = True
    if not graceful:
      self.worksource.remove_job(self)
      self.blockchain.remove_job(self)
    self.core.workqueue.remove_job(self)
    if self.worker:
      self.core.event(450, self.worksource, "canceljob", None, None, self.worker, self.worksource, self.blockchain, self)
      try: self.worker.notify_canceled(self, graceful)
      except: self.core.log(self.worker, "Exception while canceling job: %s" % (traceback.format_exc()), 100, "r")
      with self.worker.stats.lock: self.worker.stats.jobscanceled += 1
      with self.worksource.stats.lock: self.worksource.stats.jobscanceled += 1
      
      
  @staticmethod
  def calculate_midstate(data):
    return struct.pack("<8I", *struct.unpack(">8I", SHA256.hash(struct.pack("<16I", *struct.unpack(">16I", data[:64])), False)))
      
      
  @staticmethod
  def calculate_hash(data):
    return sha256(sha256(struct.pack("<20I", *struct.unpack(">20I", data[:80]))).digest()).digest()

    
    
class ValidationJob(object):

  
  def __init__(self, core, data, midstate = None):
    self.core = core
    self.data = data
    if midstate: self.midstate = midstate
    else: self.midstate = Job.calculate_midstate(data)
    self.nonce = self.data[76:80]
    self.worker = None
    self.starttime = None
    
    
  def hashes_processed(self, hashes):
    pass
    
    
  def nonce_found(self, nonce, ignore_invalid = False):
    return Job.calculate_hash(self.data[:76] + nonce)[-4:] == b"\0\0\0\0"
   
   
  def destroy(self):
    pass