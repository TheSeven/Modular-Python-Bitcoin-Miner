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
import time
import pickle
import traceback
from datetime import datetime
from threading import RLock, Thread, current_thread
from .statistics import StatisticsList
from .inflatable import Inflatable
from .startable import Startable
from .util import Bunch
try: from queue import Queue
except ImportError: from Queue import Queue



class Core(Startable):

  version = "Modular Python Bitcoin Miner v0.1.0beta"

  
  def __init__(self, instance = "default", default_loglevel = 500):
    super(Core, self).__init__()
    self.instance = instance

    # Initialize log queue and hijack stdout/stderr
    self.default_loglevel = default_loglevel
    self.logger_thread = None
    self.logqueue = Queue()
    self.logbuf = {}
    self.printlock = RLock()
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
    from .worksourcegroup import WorkSourceGroup
    self.frontendclasses = []
    self.workerclasses = []
    self.worksourceclasses = [WorkSourceGroup]

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
              
    # Register the detected classes in the global object registry
    for frontendclass in self.frontendclasses: frontendclass.id = self.registry.register(frontendclass)
    for workerclass in self.workerclasses: workerclass.id = self.registry.register(workerclass)
    for worksourceclass in self.worksourceclasses: worksourceclass.id = self.registry.register(worksourceclass)

    # Initialize blockchain list
    self.blockchainlock = RLock()
    self.blockchains = []

    # Initialize frontend list
    self.frontendlock = RLock()
    self.frontends = []

    # Initialize worker list
    self.workerlock = RLock()
    self.workers = []
    
    # Initialize work queue
    from .workqueue import WorkQueue
    self.workqueue = WorkQueue(self)

    # Initialize work fetcher
    from .fetcher import Fetcher
    self.fetcher = Fetcher(self)

    # Read saved instance state
    try:
      with open("config/%s.cfg" % instance, "rb") as f:
        data = f.read()
      state = pickle.loads(data)
      self.is_new_instance = False
      with self.frontendlock:
        for frontend in state.frontends:
          self.add_frontend(Inflatable.inflate(self, frontend))
      with self.workerlock:
        for worker in state.workers:
          self.add_worker(Inflatable.inflate(self, worker))
      with self.blockchainlock:
        for blockchain in state.blockchains:
          self.add_blockchain(Inflatable.inflate(self, blockchain))
      self.root_work_source = Inflatable.inflate(self, state.root_work_source)
    except Exception as e:
      self.log("Core: Could not load instance configuration: %s\nLoading default configuration...\n" % traceback.format_exc(), 300, "yB")
      self.is_new_instance = True
      self.frontends = []
      self.workers = []
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
      state.workers = []
      for worker in self.workers:
        state.workers.append(worker.deflate())
      if not self.root_work_source: state.root_work_source = None
      else: state.root_work_source = self.root_work_source.deflate()
      data = pickle.dumps(state, pickle.HIGHEST_PROTOCOL)
      if not os.path.exists("config"): os.mkdir("config")
      with open("config/%s.cfg" % self.instance, "wb") as f:
        f.write(data)
    except Exception as e:
      self.log("Core: Could not save instance configuration: %s\n" % traceback.format_exc(), 100, "rB")
    
    
  def _start(self):
    self.log("Core: Starting up...\n", 100, "B")
    super(Core, self)._start()
    
    # Start up frontends
    self.log("Core: Starting up frontends...\n", 700)
    have_logger = False
    have_configurator = False
    for frontend in self.frontends:
      try:
        self.log("Core: Starting up frontend %s...\n" % frontend.settings.name, 800)
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
    self.log("Core: Starting up logging thread...\n", 700)
    self.logger_thread = Thread(None, self.log_worker_thread, "core_log_worker")
    self.logger_thread.start()
    self.started = True

    # Warn if there is no configuration frontend
    if not have_configurator:
      self.log("Core: No working configuration frontend module present!\n"
               "Core: Run with --detect-frontends after ensuring that all neccessary modules are installed.\n", 100, "yB")

    # Start up work queue
    self.log("Core: Starting up work queue...\n", 700)
    try: self.workqueue.start()
    except Exception as e: self.log("Core: Could not start work queue: %s\n" % traceback.format_exc(), 100, "rB")

    # Start up blockchains
    self.log("Core: Starting up blockchains...\n", 700)
    for blockchain in self.blockchains:
      try:
        self.log("Core: Starting up blockchain %s...\n" % blockchain.settings.name, 800)
        blockchain.start()
      except Exception as e:
        self.log("Core: Could not start blockchain %s: %s\n" % (blockchain.settings.name, traceback.format_exc()), 100, "rB")

    # Start up work source tree
    self.log("Core: Starting up work source tree...\n", 700)
    if self.root_work_source:
      try:
        self.log("Core: Starting up work source %s...\n" % self.root_work_source.settings.name, 800)
        self.root_work_source.start()
      except Exception as e:
        self.log("Core: Could not start root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")

    # Start up work fetcher
    self.log("Core: Starting up work fetcher...\n", 700)
    try: self.fetcher.start()
    except Exception as e: self.log("Core: Could not start work fetcher: %s\n" % traceback.format_exc(), 100, "rB")

    # Start up workers
    self.log("Core: Starting up workers...\n", 700)
    for worker in self.workers:
      try:
        self.log("Core: Starting up worker %s...\n" % worker.settings.name, 800)
        worker.start()
      except Exception as e:
        self.log("Core: Could not start worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "rB")

    self.log("Core: Startup completed\n", 200, "")
  
  
  def _stop(self):
    self.log("Core: Shutting down...\n", 100, "B")
    
    # Shut down workers
    self.log("Core: Shutting down workers...\n", 700)
    for worker in self.workers:
      try:
        self.log("Core: Shutting down worker %s...\n" % worker.settings.name, 800)
        worker.stop()
      except Exception as e:
        self.log("Core: Could not stop worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "rB")

    # Shut down work fetcher
    self.log("Core: Shutting down work fetcher...\n", 700)
    try: self.fetcher.stop()
    except Exception as e: self.log("Core: Could not stop work fetcher: %s\n" % traceback.format_exc(), 100, "rB")

    # Shut down work source tree
    self.log("Core: Shutting down work source tree...\n", 700)
    if self.root_work_source:
      try:
        self.log("Core: Shutting down work source %s...\n" % self.root_work_source.settings.name, 800)
        self.root_work_source.stop()
      except Exception as e:
        self.log("Core: Could not stop root work source %s: %s\n" % (self.root_work_source.settings.name, traceback.format_exc()), 100, "rB")
    
    # Shut down blockchains
    self.log("Core: Shutting down blockchains...\n", 700)
    for blockchain in self.blockchains:
      try:
        self.log("Core: Shutting down blockchain %s...\n" % blockchain.settings.name, 800)
        blockchain.stop()
      except Exception as e:
        self.log("Core: Could not stop blockchain %s: %s\n" % (blockchain.settings.name, traceback.format_exc()), 100, "rB")

    # Shut down work queue
    self.log("Core: Shutting down work queue...\n", 700)
    try: self.workqueue.stop()
    except Exception as e: self.log("Core: Could not stop work queue: %s\n" % traceback.format_exc(), 100, "rB")

    # Save instance configuration
    self.save()
    
    # We are about to shut down the logging infrastructure, so switch back to builtin logging
    self.log("Core: Shutting down logging thread...\n", 700)
    self.started = False
    
    # Shut down the log worker thread
    self.logqueue.put(None)
    self.logger_thread.join(10)
    
    # Shut down the frontends
    self.log("Core: Shutting down frontends...\n", 700)
    for frontend in self.frontends:
      try:
        self.log("Core: Shutting down frontend %s...\n" % frontend.settings.name, 800)
        frontend.stop()
      except Exception as e:
        self.log("Core: Could not stop frontend %s: %s\n" % (frontend.settings.name, traceback.format_exc()), 100, "rB")

    super(Core, self)._stop()
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
    self.log("Core: Autodetecting workers...\n", 500, "B")
    for workerclass in self.workerclasses:
      if workerclass.can_autodetect:
        try: workerclass.autodetect(self)
        except Exception as e:
          name = "%s.%s" % (workerclass.__module__, workerclass.__name__)
          self.log("Core: %s autodetection failed: %s\n" % (name, traceback.format_exc()), 300, "yB")

    
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


  def add_worker(self, worker):
    with self.start_stop_lock:
      with self.workerlock:
        if not worker in self.workers:
          if self.started:
            try: worker.start()
            except Exception as e:
              self.log("Core: Could not start worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "yB")
          self.workers.append(worker)


  def remove_worker(self, worker):
    with self.start_stop_lock:
      with self.workerlock:
        while worker in self.workers:
          if self.started:
            try: worker.stop()
            except Exception as e:
              self.log("Core: Could not stop worker %s: %s\n" % (worker.settings.name, traceback.format_exc()), 100, "yB")
          self.workers.remove(worker)


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
          
          
  def get_job(self, worker, expiry_min_ahead, async = False):
    return self.workqueue.get_job(worker, expiry_min_ahead, async)
    
    
  def get_blockchain_statistics(self):
    stats = StatisticsList()
    for blockchain in self.blockchains: stats.append(blockchain.get_statistics())
    return stats
    
    
  def get_work_source_statistics(self):
    stats = StatisticsList()
    if self.root_work_source: stats.append(self.root_work_source.get_statistics())
    return stats
    
    
  def get_worker_statistics(self):
    stats = StatisticsList()
    for worker in self.workers: stats.append(worker.get_statistics())
    return stats
    
    
  def notify_speed_changed(self, worker):
    return self.fetcher.notify_speed_changed(worker)
    
    
  def log(self, message, loglevel, format = ""):
    # Concatenate messages until there is a linefeed
    thread = current_thread()
    if not thread in self.logbuf: self.logbuf[thread] = {"time": datetime.now(), "data": []}
    self.logbuf[thread]["data"].append((message, format))
    if message[-1:] != "\n": return
    self.log_multi(loglevel, self.logbuf[thread]["data"], self.logbuf[thread]["time"])
    del self.logbuf[thread]

    
  def log_multi(self, loglevel, messages, timestamp = datetime.now()):
    # Put message into the queue, will be pushed to listeners by a worker thread
    self.logqueue.put((timestamp, loglevel, messages))
    
    # If the core hasn't fully started up yet, the logging subsystem might not
    # work yet. Print the message to stderr as well just in case.
    if not self.started and loglevel <= self.default_loglevel:
      message = ""
      for string, format in messages: message += string
      prefix = timestamp.strftime("%Y-%m-%d %H:%M:%S.%f") + " [%3d]: " % loglevel
      with self.printlock:
        for line in string.splitlines(True): self.stderr.write(prefix + line)


  def log_worker_thread(self):
    while True:
      data = self.logqueue.get()
      
      # We'll get a None value in the queue if the core wants us to shut down
      if not data:
        self.logqueue.task_done()
        return
      
      for frontend in self.frontends:
        if frontend.can_log:
          frontend.write_log_message(*data)
          
      self.logqueue.task_done()
