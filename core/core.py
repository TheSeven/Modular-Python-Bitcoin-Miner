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



#####################################
# Modular Python Bitcoin Miner Core #
#####################################



import sys
import pickle
from datetime import datetime
from threading import RLock
from .inflatable import Inflatable
from .util import Bunch
try: from queue import Queue
except ImportError: from Queue import Queue



class Core(object):

  version = "Modular Python Bitcoin Miner v0.1.0alpha"

  
  def __init__(self, instance = "default"):
    self.instance = instance
    self.started = False

    # Initialize log queue and hijack stdout/stderr
    self.logqueue = Queue()
    self.loglf = True
    self.stdout = sys.stdout
    self.stderr = sys.stderr
    from .util import OutputRedirector
    sys.stdout = OutputRedirector(self, 500)
    sys.stderr = OutputRedirector(self, 100, "rB")

    # Print startup message
    self.log("%s, Copyright (C) 2012 Michael Sparmann (TheSeven)\n" % Core.version, 0, "B")
    self.log("Modular Python Bitcoin Miner comes with ABSOLUTELY NO WARRANTY.\n", 0)
    self.log("This is free software, and you are welcome to redistribute it under certain conditions.\n", 0)
    self.log("See included file COPYING_GPLv2.txt for details.\n", 0)
    self.log("Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh or,\n", 0, "y")
    self.log("even better, donating a small share of your hashing power if you want\n", 0, "y")
    self.log("to support further development of the Modular Python Bitcoin Miner.\n", 0, "y")
    
    # Set up object registry
    from .objectregistry import ObjectRegistry
    self.registry = ObjectRegistry(self)

    # Initialize blockchain list
    self.blockchainlock = RLock()
    self.blockchains = []

    # Read saved instance state
    try:
      with open("config/%s.cfg" % instance, "rb") as f:
        data = f.read()
      state = pickle.loads(data)
      self.is_new_instance = False
      with self.blockchainlock:
        for blockchain in state.blockchains:
          self.blockchains.append(Inflatable.inflate(self, blockchain))
      self.root_work_source = Inflatable.inflate(self, state.root_work_source)
    except Exception as e:
      self.log("Core: Could not load instance configuration: %s\nLoading default configuration...\n" % e, 300, "yB")
      self.is_new_instance = True
      self.blockchains = []
      self.root_work_source = None
    
    # Create a new root work source group if neccessary
    if not self.root_work_source:
      from .worksourcegroup import WorkSourceGroup
      self.root_work_source = WorkSourceGroup(self)
      self.root_work_source.settings.name = "Work sources"
    pass
    
    
  def save(self):
    self.log("Core: Saving instance configuration...\n", 500)
    try:
      state = Bunch()
      state.blockchains = []
      for blockchain in self.blockchains:
        state.blockchains.append(blockchain.deflate())
      if not self.root_work_source: state.root_work_source = None
      else: state.root_work_source = self.root_work_source.deflate()
      data = pickle.dumps(state, pickle.HIGHEST_PROTOCOL)
      with open("config/%s.cfg" % self.instance, "wb") as f:
        f.write(data)
    except Exception as e:
      self.log("Core: Could not save instance configuration: %s\n" % e, 100, "rB")
    
    
  def start(self):
    self.log("Core: Starting up...\n", 100, "B")
  
  
  def stop(self):
    self.log("Core: Shutting down...\n", 100, "B")
    self.save()
  
  
  def detect_frontends(self):
    # TODO: Stub
    pass
  
  
  def detect_workers(self):
    # TODO: Stub
    pass

    
  def get_blockchains(self):
    return self.blockchains


  def get_blockchain_by_name(self, name):
    for blockchain in self.blockchains:
      if blockchain.settings.name == name:
        return blockchain
    return None
    
  
  def add_blockchain(self, blockchain):
    with self.blockchainlock:
      if not blockchain in self.blockchains:
        self.blockchains.append(blockchain)


  def remove_blockchain(self, blockchain):
    with self.blockchainlock:
      while blockchain in self.blockchains:
        self.blockchains.remove(blockchain)


  def get_root_work_source(self):
    return self.root_work_source


  def set_root_work_source(self, worksource):
    self.root_work_source = worksource
    worksource.set_parent(None)
    
    
  def log(self, message, loglevel, format = ""):
    timestamp = datetime.now()
    continuation = not self.loglf
    # Put message into the queue, will be pushed to listeners by a worker thread
    self.logqueue.put((timestamp, continuation, message, loglevel, format))
    self.loglf = message[-1:] == "\n"
    # If the core hasn't fully started up yet, the logging subsystem might not
    # work yet. Print the message to stderr as well just in case.
    if not self.started:
      prefix = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + " [%3d]: " % loglevel
      first = True
      for line in message.splitlines(True):
        self.stderr.write(line if first and continuation else prefix + line)
        first = False
