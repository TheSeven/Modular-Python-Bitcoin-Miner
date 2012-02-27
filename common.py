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


##################
# Common classes #
##################


import binascii
import struct
import hashlib

class Job(object):
  MAX_UPLOAD_RETRIES = 10
  
  def __init__(self, miner, pool, longpollepoch, state, data, target, check = None):
    self.miner = miner
    self.pool = pool
    self.longpollepoch = longpollepoch
    self.state = state
    self.data = data
    self.target = target
    self.check = check
    self.starttime = None
    self.uploadretries = 0

  def sendresult(self, nonce, worker):
    if self.pool == None: return
    self.miner.log(worker.name + " found share: %s:%s:%s:%s\n" % (self.pool.name, binascii.hexlify(self.state).decode("ascii"), binascii.hexlify(self.data[64:76]).decode("ascii"), binascii.hexlify(nonce).decode("ascii")), "g")
    data = self.data[:76] + nonce + self.data[80:]
    hash = hashlib.sha256(hashlib.sha256(struct.pack("<20I", *struct.unpack(">20I", data[:80]))).digest()).digest()
    if hash[-4:] != b"\0\0\0\0":
      self.miner.log("%s sent K-not-zero share %s\n" % (worker.name, binascii.hexlify(nonce).decode("ascii")), "rB")
      with worker.statlock: worker.invalid = worker.invalid + 1
      return
    self.difficulty = 65535. * 2**48 / struct.unpack("<Q", self.target[-12:-4])[0]
    self.realdiff = 65535. * 2**48 / struct.unpack("<Q", hash[-12:-4])[0]
    if hash[::-1] > self.target[::-1]:
      self.miner.log("Share %s (difficulty %.5f) didn't meet difficulty %.5f\n" % (binascii.hexlify(nonce).decode("ascii"), self.realdiff, self.difficulty), "g")
      return
    self.pool.sendresult(self, data, nonce, self.realdiff, worker)

  def uploadcallback(self, nonce, worker, result):
    if result == True:
      self.miner.log("%s accepted share %s (difficulty %.5f)\n" % (self.pool.name, binascii.hexlify(nonce).decode("ascii"), self.realdiff), "gB")
      with worker.statlock: worker.accepted = worker.accepted + self.difficulty
      with self.pool.statlock:
        self.pool.accepted = self.pool.accepted + 1
        self.pool.score = self.pool.score + self.miner.sharebias
    else:
      if result == False or result == None or len(result) == 0: result = "Unknown reason"
      self.miner.log("%s rejected share %s (difficulty %.5f): %s\n" % (self.pool.name, binascii.hexlify(nonce).decode("ascii"), self.realdiff, result), "rB")
      with worker.statlock: worker.rejected = worker.rejected + self.difficulty
      with self.pool.statlock:
        self.pool.rejected = self.pool.rejected + 1
        self.pool.score = self.pool.score + self.miner.stalebias

  def finish(self, mhashes, worker):
    with self.pool.statlock:
      self.pool.mhashes = self.pool.mhashes + mhashes
      self.pool.score = self.pool.score + self.miner.jobfinishbias
    with worker.statlock: worker.mhashes = worker.mhashes + mhashes
    