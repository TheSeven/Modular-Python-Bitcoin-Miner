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
import os
import pickle
import traceback
from datetime import datetime
from threading import RLock, Thread
from .inflatable import Inflatable
from .util import Bunch
try: from queue import Queue
except ImportError: from Queue import Queue



class Core(object):

  version = "Modular Python Bitcoin Miner v0.1.0alpha"

  
  def __init__(self, instance = "default", default_loglevel = 500):
    self.instance = instance
    self.started = False
    self.start_stop_lock = RLock()

    # Initialize log queue and hijack stdout/stderr
    self.default_loglevel = default_loglevel
    self.logger_thread = None
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
    
    # Initialize class lists
    self.frontendclasses = []
    self.workerclasses = []
    self.worksourceclasses = []

    # Load modules
    self.log("Core: Loading modules...\n", 500, "B")
    # Grrr. Python is just broken...
    import __main__
    basepath = os.path.dirname(__main__.__file__)
    basepath = (basepath if basepath else ".") + "/modules"
    for maintainer in os.listdir(basepath):
      maintainerpath = basepath + "/" + maintainer
      if os.path.isdir(maintainerpath) and os.path.isfile(maintainerpath + "/__init__.py"):
        for module in os.listdir(maintainerpath):
          modulepath = maintainerpath + "/" + module
          if os.path.isdir(modulepath) and os.path.isfile(modulepath + "/__init__.py"):
            try:
              self.log("Core: Loading modules.%s.%s...\n" % (maintainer, module), 800)
              module = getattr(__import__("modules.%s" % maintainer, globals(), locals(), [module], 0), module)
              self.frontendclasses.extend(getattr(module, "frontendclasses", []))
              self.workerclasses.extend(getattr(module, "workerclasses", []))
              self.worksourceclasses.extend(getattr(module, "worksourceclasses", []))
            except Exception as e:
              self.log("Core: Could not load module %s.%s: %s\n" % (maintainer, module, traceback.format_exc()), 300, "yB")

    # Initialize blockchain list
    self.blockchainlock = RLock()
    self.blockchains = []

    # Initialize frontend list
    self.frontendlock = RLock()
    self.frontends = []

    # Read saved instance state
    try:
      with open("config/%s.cfg" % instance, "rb") as f:
        data = f.read()
      state = pickle.loads(data)
      self.is_new_instance = False
      with self.frontendlock:
        for frontend in state.frontends:
          self.add_frontend(Inflatable.inflate(self, frontend))
      with self.blockchainlock:
        for blockchain in state.blockchains:
          self.add_blockchain(Inflatable.inflate(self, blockchain))
      self.root_work_source = Inflatable.inflate(self, state.root_work_source)
    except Exception as e:
      self.log("Core: Could not load instance configuration: %s\nLoading default configuration...\n" % traceback.format_exc(), 300, "yB")
      self.is_new_instance = True
      self.frontends = []
      self.blockchains = []
      self.root_work_source = None
    
    # Create a new root work source group if neccessary
    if not self.root_work_source:
      from .worksourcegroup import WorkSourceGroup
      self.root_work_source = WorkSourceGroup(self)
      self.root_work_source.settings.name = "Work sources"
    pass
    
    
  def save(self):
    self.log("Core: Saving instance configuration...\n", 500, "B")
    try:
      state = Bunch()
      state.blockchains = []
      for blockchain in self.blockchains:
        state.blockchains.append(blockchain.deflate())
      state.frontends = []
      for frontend in self.frontends:
        state.frontends.append(frontend.deflate())
      if not self.root_work_source: state.root_work_source = None
      else: state.root_work_source = self.root_work_source.deflate()
      data = pickle.dumps(state, pickle.HIGHEST_PROTOCOL)
      if not os.path.exists("config"): os.mkdir("config")
      with open("config/%s.cfg" % self.instance, "wb") as f:
        f.write(data)
    except Exception as e:
      self.log("Core: Could not save instance configuration: %s\n" % traceback.format_exc(), 100, "rB")
    
    
  def start(self):
    with self.start_stop_lock:
      if self.started: return
      self.log("Core: Starting up...\n", 100, "B")
      
      # Start up frontends
      have_logger = False
      have_configurator = False
      for frontend in self.frontends:
        try:
          frontend.start()
          if frontend.can_log: have_logger = True
          if frontend.can_configure: have_configurator = True
        except Exception as e:
          self.log("Core: Could not start frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "rB")
        
      # Warn if there is no logger frontend (needs to be fone before enabling logger thread)
      if not have_logger:
        self.log("Core: No working logger frontend module present!\n"
                 "Core: Run with --detect-frontends after ensuring that all neccessary modules are installed.\n", 10, "rB")

      # Start logger thread
      self.logger_thread = Thread(None, self.log_worker_thread, "Log worker thread")
      self.logger_thread.start()
      self.started = True

      # Warn if there is no configuration frontend
      if not have_configurator:
        self.log("Core: No working configuration frontend module present!\n"
                 "Core: Run with --detect-frontends after ensuring that all neccessary modules are installed.\n", 100, "yB")

      # Start up work source tree
      if self.root_work_source:
        try: self.root_work_source.start()
        except Exception as e:
          self.log("Core: Could not start root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")

      self.log("Core: Startup completed\n", 200, "")
  
  
  def stop(self):
    with self.start_stop_lock:
      if not self.started: return
      self.log("Core: Shutting down...\n", 100, "B")
      
      # Shut down work source tree
      if self.root_work_source:
        try: self.root_work_source.stop()
        except Exception as e:
          self.log("Core: Could not stop root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")
      
      # Save instance configuration
      self.save()
      
      # We are about to shut down the logging infrastructure, so switch back to builtin logging
      self.started = False
      
      # Shut down the log worker thread
      self.logqueue.put(None)
      self.logger_thread.join(10)
      
      # Shut down the frontends
      for frontend in self.frontends:
        try: frontend.stop()
        except Exception as e:
          self.log("Core: Could not stop frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "rB")

      self.log("Core: Shutdown completed\n", 200, "")
          
  
  def detect_frontends(self):
    self.log("Core: Autodetecting frontends...\n", 500, "B")
    for frontendclass in self.frontendclasses:
      if frontendclass.can_autodetect:
        try: frontendclass.autodetect(self)
        except Exception as e:
          name = "%s.%s" % (frontendclass.__module__, frontendclass.__name__)
          self.log("Core: %s autodetection failed: %s\n" % (name, traceback.format_exc()), 300, "yB")
  
  
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


  def add_frontend(self, frontend):
    with self.start_stop_lock:
      with self.frontendlock:
        if not frontend in self.frontends:
          if self.started:
            try: frontend.start()
            except Exception as e:
              self.log("Core: Could not start frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "yB")
          self.frontends.append(frontend)


  def remove_frontend(self, frontend):
    with self.start_stop_lock:
      with self.frontendlock:
        while frontend in self.frontends:
          if self.started:
            try: frontend.stop()
            except Exception as e:
              self.log("Core: Could not stop frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "yB")
          self.frontends.remove(frontend)


  def get_root_work_source(self):
    return self.root_work_source


  def set_root_work_source(self, worksource):
    with self.start_stop_lock:
      if self.started and self.root_work_source:
        try: self.root_work_source.stop()
        except Exception as e:
          self.log("Core: Could not stop root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "yB")
      self.root_work_source = worksource
      worksource.set_parent(None)
      if self.started:
        try: worksource.start()
        except Exception as e:
          self.log("Core: Could not start root work source %s: %s\n" % (worksource.settings.name, traceback.format_exc()), 100, "yB")
    
    
  def log(self, message, loglevel, format = ""):
    timestamp = datetime.now()
    
    # If the last message didn't end with a line feed, don't print a time stamp
    continuation = not self.loglf
    
    # Put message into the queue, will be pushed to listeners by a worker thread
    self.logqueue.put((timestamp, continuation, message, loglevel, format))
    
    # Update line feed state
    self.loglf = message[-1:] == "\n"
    
    # If the core hasn't fully started up yet, the logging subsystem might not
    # work yet. Print the message to stderr as well just in case.
    if not self.started and loglevel <= self.default_loglevel:
      prefix = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + " [%3d]: " % loglevel
      first = True
      for line in message.splitlines(True):
        self.stderr.write(line if first and continuation else prefix + line)
        first = False


  def log_worker_thread(self):
    while True:
      data = self.logqueue.get()
      
      # We'll get a None value in the queue if the core wants us to shut down
      if not data:
        self.logqueue.task_done()
        return
      
      (timestamp, continuation, message, loglevel, format) = data
      for frontend in self.frontends:
        if frontend.can_log:
          frontend.write_log_message(timestamp, continuation, message, loglevel, format)
          
      self.logqueue.task_done()
