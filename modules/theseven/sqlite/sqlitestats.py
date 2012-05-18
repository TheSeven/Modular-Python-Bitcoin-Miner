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
# SQLite Statistics Logger Frontend #
#####################################



import os
import time
import numbers
import sqlite3
from threading import RLock, Condition, Thread
from core.basefrontend import BaseFrontend
from core.statistics import Statistics



class SQLiteStats(BaseFrontend):

  version = "theseven.sqlite statistics logger v0.1.0beta"
  default_name = "Untitled SQLite statistics logger"
  can_log = True
  can_handle_events = True
  can_autodetect = False
  settings = dict(BaseFrontend.settings, **{
    "filename": {"title": "Database file name", "type": "string", "position": 1000},
    "loglevel": {"title": "Log level", "type": "int", "position": 2000},
    "eventlevel": {"title": "Event filter level", "type": "int", "position": 2100},
    "statinterval": {"title": "Statistics logging interval", "type": "int", "position": 3000},
  })


  def __init__(self, core, state = None):
    super(SQLiteStats, self).__init__(core, state)
    self.lock = RLock()
    self.conn = None
    self.statwakeup = Condition()


  def apply_settings(self):
    super(SQLiteStats, self).apply_settings()
    if not "filename" in self.settings or not self.settings.filename: self.settings.filename = "stats.db"
    if not "loglevel" in self.settings: self.settings.loglevel = self.core.default_loglevel
    if not "eventlevel" in self.settings: self.settings.eventlevel = self.core.default_loglevel
    if not "statinterval" in self.settings: self.settings.statinterval = 60
    if not "worksourceinterval" in self.settings: self.settings.worksourceinterval = 60
    if not "blockchaininterval" in self.settings: self.settings.blockchaininterval = 60
    if self.started:
      if self.settings.filename != self.filename: self.async_restart()
      else:
        with self.statwakeup: self.statwakeup.notify()


  def _start(self):
    super(SQLiteStats, self)._start()
    with self.lock:
      self.shutdown = False
      self.filename = self.settings.filename
      self.db = sqlite3.connect(self.filename, check_same_thread = False)
      self.db.text_factory = str
      self.cursor = self.db.cursor()
      self._check_schema()
      self.eventtypes = {}
      self.statcolumns = {}
      self.statthread = Thread(None, self._statloop, "%s_statthread" % self.settings.name)
      self.statthread.daemon = True
      self.statthread.start()


  def _stop(self):
    self.shutdown = True
    with self.statwakeup: self.statwakeup.notify()
    self.statthread.join(5)
    with self.lock:
      self.cursor.close()
      self.cursor = None
      self.db.commit()
      self.db.close()
      self.db = None
    super(SQLiteStats, self)._stop()


  def write_log_message(self, source, timestamp, loglevel, messages):
    if not self.started: return
    if loglevel > self.settings.loglevel: return
    timestamp = time.mktime(timestamp.timetuple()) + timestamp.microsecond / 1000000.
    with self.lock:
      source = self._get_object_id(source)
      self.cursor.execute("INSERT INTO [log]([level], [timestamp], [source]) VALUES(:level, :timestamp, :source)",
                          {"level": loglevel, "timestamp": timestamp, "source": source})
      parent = self.cursor.lastrowid
      self.cursor.executemany("INSERT INTO [logfragment]([parent], [message], [format]) VALUES(:parent, :message, :format)",
                              [{"parent": parent, "message": message, "format": format} for message, format in messages])


  def handle_stats_event(self, level, source, event, arg, message, worker, worksource, blockchain, job, timestamp):
    if not self.started: return
    if level > self.settings.eventlevel: return
    timestamp = time.mktime(timestamp.timetuple()) + timestamp.microsecond / 1000000.
    with self.lock:
      source = self._get_object_id(source)
      worker = self._get_object_id(worker)
      worksource = self._get_object_id(worksource)
      blockchain = self._get_object_id(blockchain)
      job = self._get_job_id(job)
      eventtype = self._get_eventtype_id(event)
      self.cursor.execute("INSERT INTO [event]([level], [timestamp], [source], [type], [argument], "
                                              "[message], [worker], [worksource], [blockchain], [job]) "
                                      "VALUES(:level, :timestamp, :source, :type, :argument, "
                                             ":message, :worker, :worksource, :blockchain, :job)",
                          {"level": level, "timestamp": timestamp, "source": source, "type": eventtype, "argument": arg,
                           "message": message, "worker": worker, "worksource": worksource, "blockchain": blockchain, "job": job})
      
      
  def _statloop(self):
    while not self.shutdown:
      with self.statwakeup:
        if self.settings.statinterval <= 0: self.statwakeup.wait()
        else:
          now = time.time()
          stats = Statistics(obj = self.core, ghashes = self.core.stats.ghashes, starttime = self.core.stats.starttime)
          stats.avgmhps =  1000. * stats.ghashes / (now - stats.starttime)
          stats.children = self.core.get_worker_statistics() \
                         + self.core.get_work_source_statistics() \
                         + self.core.get_blockchain_statistics()
          with self.lock:
            self._insert_stats(now, stats)
            self.db.commit()
          self.statwakeup.wait(self.settings.statinterval)
          
          
  def _insert_stats(self, timestamp, stats, parent = None):
    self.cursor.execute("INSERT INTO [statrow]([timestamp], [subject], [parent]) VALUES(:timestamp, :subject, :parent)",
                        {"timestamp": timestamp, "subject": self._get_object_id(stats.obj), "parent": parent})
    row = self.cursor.lastrowid
    for key, value in stats.items():
      if isinstance(value, numbers.Number):
        self.cursor.execute("INSERT INTO [statfield]([row], [column], [value]) VALUES(:row, :column, :value)",
                            {"row": row, "column": self._get_statcolumn_id(key), "value": value})
    for child in stats.children: self._insert_stats(timestamp, child, row)
        
    
  def _get_objecttype_id(self, objtype):
    if hasattr(objtype, "_ext_theseven_sqlite_objtypeid"): return objtype._ext_theseven_sqlite_objtypeid
    name = objtype.__module__ + "." + objtype.__name__
    try:
      self.cursor.execute("SELECT [id] FROM [objecttype] WHERE [name] = :name", {"name": name})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [objecttype]([name]) VALUES(:name)", {"name": name})
      id = self.cursor.lastrowid
    objtype._ext_theseven_sqlite_objtypeid = id
    return id


  def _get_object_id(self, obj):
    if obj is None: return None
    if hasattr(obj, "_ext_theseven_sqlite_objid"): return obj._ext_theseven_sqlite_objid
    type = self._get_objecttype_id(obj.__class__)
    try:
      self.cursor.execute("SELECT [id] FROM [object] WHERE [type] = :type AND [name] = :name",
                          {"type": type, "name": obj.settings.name})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [object]([type], [name]) VALUES(:type, :name)",
                          {"type": type, "name": obj.settings.name})
      id = self.cursor.lastrowid
    obj._ext_theseven_sqlite_objid = id
    return id


  def _get_job_id(self, job):
    if job is None: return None
    if hasattr(job, "_ext_theseven_sqlite_jobid"): return job._ext_theseven_sqlite_jobid
    worksource = self._get_object_id(job.worksource)
    self.cursor.execute("INSERT INTO [job]([worksource], [data]) VALUES(:worksource, :data)",
                        {"worksource": worksource, "data": job.data[:76]})
    job._ext_theseven_sqlite_jobid = self.cursor.lastrowid
    return self.cursor.lastrowid


  def _get_eventtype_id(self, eventtype):
    if eventtype in self.eventtypes: return self.eventtypes[eventtype]
    try:
      self.cursor.execute("SELECT [id] FROM [eventtype] WHERE [name] = :name", {"name": eventtype})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [eventtype]([name]) VALUES(:name)", {"name": eventtype})
      id = self.cursor.lastrowid
    self.eventtypes[eventtype] = id
    return id


  def _get_statcolumn_id(self, column):
    if column in self.statcolumns: return self.statcolumns[column]
    try:
      self.cursor.execute("SELECT [id] FROM [statcolumn] WHERE [name] = :name", {"name": column})
      id = int(self.cursor.fetchone()[0])
    except:
      self.cursor.execute("INSERT INTO [statcolumn]([name]) VALUES(:name)", {"name": column})
      id = self.cursor.lastrowid
    self.statcolumns[column] = id
    return id


  def _check_schema(self):
    try:
      self.cursor.execute("SELECT [value] FROM [dbinfo] WHERE [key] = 'version'")
      version = int(self.cursor.fetchone()[0])
    except: version = 0
    try:
      self.db.commit()
      if version == 0:
        self.cursor.execute("CREATE TABLE [dbinfo]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                  "[key] TEXT UNIQUE NOT NULL, "
                                                  "[value] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [objecttype]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                         "             [name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [object]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                  "[type] INTEGER NOT NULL REFERENCES [objecttype] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                  "[name] TEXT NOT NULL, "
                                                  "CONSTRAINT object_unique_type_name UNIQUE (type, name))")
        self.cursor.execute("CREATE TABLE [job]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                               "[worksource] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                               "[data] BLOB NOT NULL)")
        self.cursor.execute("CREATE TABLE [eventtype]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                     "[name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [event]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                 "[level] INTEGER NOT NULL, "
                                                 "[timestamp] REAL NOT NULL, "
                                                 "[source] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[type] INTEGER NOT NULL REFERENCES [eventtype] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[argument] INTEGER NULL, [message] TEXT NULL, "
                                                 "[worker] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[worksource] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[blockchain] INTEGER NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                 "[job] INTEGER NULL REFERENCES [job] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [log]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                               "[level] INTEGER NOT NULL, "
                                               "[timestamp] REAL NOT NULL, "
                                               "[source] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [logfragment]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                       "[parent] INTEGER NOT NULL REFERENCES [log] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                       "[message] TEXT NOT NULL, "
                                                       "[format] TEXT NOT NULL)")
        self.cursor.execute("INSERT INTO [dbinfo]([key], [value]) VALUES('version', :version)", {"version": version + 1})
        self.db.commit()
        version = 1
      if version == 1:
        self.cursor.execute("CREATE TABLE [statcolumn]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                      "[name] TEXT UNIQUE NOT NULL)")
        self.cursor.execute("CREATE TABLE [statrow]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                   "[timestamp] REAL NOT NULL, "
                                                   "[subject] INTEGER NOT NULL REFERENCES [object] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                   "[parent] INTEGER NULL REFERENCES [statrow] ON DELETE RESTRICT ON UPDATE RESTRICT)")
        self.cursor.execute("CREATE TABLE [statfield]([id] INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT, "
                                                     "[row] INTEGER NOT NULL REFERENCES [statrow] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                     "[column] INTEGER NOT NULL REFERENCES [statcolumn] ON DELETE RESTRICT ON UPDATE RESTRICT, "
                                                     "[value] REAL NOT NULL)")
        self.cursor.execute("UPDATE [dbinfo] SET [value] = :version WHERE [key] = 'version'", {"version": version + 1})
        self.db.commit()
        version = 2
    except: self.db.rollback()
