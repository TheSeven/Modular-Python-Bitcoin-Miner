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



#########################
# Worker validation job #
#########################



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
 