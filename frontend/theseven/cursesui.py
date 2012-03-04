# -*- coding: utf-8 -*-
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


####################
# Curses UI module #
####################

# Module configuration options:
#   updateinterval: Statistics update interval in seconds (default: 1)


import sys
import curses
import threading
import traceback
import atexit
import time
import datetime

class CursesUI(object):
  def __init__(self, miner, dict):
    self.__dict__ = dict
    self.miner = miner
    self.updateinterval = getattr(self, "updateinterval", 1)
    self.ysplit = 10 + len(self.miner.pools) + self.countchildren(self.miner.workers)
    atexit.register(self.shutdown)
    self.mainwin = curses.initscr()
    curses.start_color()
    curses.curs_set(0)
    curses.init_pair(1, curses.COLOR_RED, 0)
    curses.init_pair(2, curses.COLOR_YELLOW, 0)
    curses.init_pair(3, curses.COLOR_GREEN, 0)
    self.red = curses.color_pair(1)
    self.yellow = curses.color_pair(2)
    self.green = curses.color_pair(3)
    self.mainwin.idlok(True)
    self.mainwin.scrollok(True)
    self.mainwin.erase()
    self.mainwin.refresh()
    self.logwin = curses.newpad(500, 500)
    self.logwin.scrollok(True)
    self.logwin.move(499, 0)
    self.loglf = True
    thread = threading.Thread(None, self.mainloop, "Curses UI")
    thread.daemon = True
    thread.start()
    
  def shutdown(self):
    self.message("", "\n", "")
    self.miner.logqueue.join()
    curses.endwin()
    
  def countchildren(self, children):
    childcount = len(children)
    for child in children:
      childcount = childcount + self.countchildren(child.children)
    return childcount
    
  def calculatemaxfieldlen(self, children, field, indent = 0):
    maxlen = 0
    for child in children:
      length = len(child[field][0])
      if length > maxlen: maxlen = length
    return maxlen
  
  def translatepooldata(self, pools, poolstats, indent = 0):
    for pool in pools:
      bold = "B" if len(pool["children"]) > 0 else ""
      uptime = 1
      try: uptime = (time.time() - pool["starttime"])
      except: pass
      try: failedpercent = 100. * pool["failedreqs"] / pool["requests"]
      except: failedpercent = 0
      try: stalepercent = 100. * pool["rejected"] / (pool["accepted"] + pool["rejected"])
      except: stalepercent = 0
      try: retrypercent = 100. * pool["uploadretries"] / (pool["accepted"] + pool["rejected"])
      except: retrypercent = 0
      try: efficiency = pool["accepted"] * pool["difficulty"] / pool["mhashes"] * 429503.2833
      except: efficiency = 0
      poolstats.append({ \
        "name": (" " * indent + pool["name"], bold, "l"), \
        "longpolling": ("Yes", "g" + bold, "c") if pool["longpolling"] == True else ("No", "r" + bold, "c") if pool["longpolling"] == False else ("Unkn", "y" + bold, "c"), \
        "difficulty": ("%.5f" % pool["difficulty"], bold, "r"), \
        "requests": ("%d" % pool["requests"], bold, "r"), \
        "failedreqs": ("%d (%.1f%%)" % (pool["failedreqs"], failedpercent), "r" + bold if failedpercent > 5 else "g" + bold if failedpercent < 1 else "y" + bold, "r"), \
        "jobsaccepted": ("%d" % pool["jobsaccepted"], bold, "r"), \
        "longpollkilled": ("%d" % pool["longpollkilled"], bold, "r"), \
        "accepted": ("%d" % pool["accepted"], bold, "r"), \
        "rejected": ("%d (%.1f%%)" % (pool["rejected"], stalepercent), "r" + bold if stalepercent > 5 else "g" + bold if stalepercent < 1 else "y" + bold, "r"), \
        "uploadretries": ("%d (%.1f%%)" % (pool["uploadretries"], retrypercent), "r" + bold if retrypercent > 5 else "g" + bold if retrypercent < 1 else "y" + bold, "r"), \
        "avgmhps": ("%.2f" % (pool["mhashes"] / uptime), bold, "r"), \
        "efficiency": ("%.1f%%" % efficiency, "r" + bold if efficiency < 80 else "g" + bold if efficiency > 95 else "y" + bold, "r"), \
        "score": ("%.0f" % pool["score"], bold, "r"), \
      })
      self.translatepooldata(pool["children"], poolstats, indent + 2)
    
  def translateworkerdata(self, workers, workerstats, indent = 0):
    for worker in workers:
      bold = "B" if len(worker["children"]) > 0 else ""
      uptime = 1
      try: uptime = (time.time() - worker["starttime"])
      except: pass
      try: stalepercent = 100. * worker["rejected"] / (worker["accepted"] + worker["rejected"])
      except: stalepercent = 0
      try: invalidpercent = 100. * worker["invalid"] / (worker["accepted"] + worker["rejected"] + worker["invalid"])
      except: invalidpercent = 0
      try: efficiency = worker["accepted"] / worker["mhashes"] * 429503.2833
      except: efficiency = 0
      try: invalidwarning = worker['invalidwarning']
      except: invalidwarning = 1
      try: invalidcritical = worker['invalidcritical']
      except: invalidcritical = 10
      try: tempwarning = worker['tempwarning']
      except: tempwarning = 40
      try: tempcritical = worker['tempcritical']
      except: tempcritical = 50
      if invalidpercent > invalidcritical or ("temperature" in worker and worker['temperature'] != None and worker['temperature'] > tempcritical):
        namecolor = "r" if len(worker["children"]) == 0 else ""
      elif invalidpercent > invalidwarning or ("temperature" in worker and worker['temperature'] != None and worker['temperature'] > tempwarning):
        namecolor = "y" if len(worker["children"]) == 0 else ""
      else:
        namecolor = ""
      workerstats.append({ \
        "name": (" " * indent + worker["name"], namecolor + bold, "l"), \
        "jobsaccepted": ("%d" % worker["jobsaccepted"], bold, "r"), \
        "accepted": ("%.0f" % worker["accepted"], bold, "r"), \
        "rejected": ("%.0f (%.1f%%)" % (worker["rejected"], stalepercent), "r" + bold if stalepercent > 5 else "g" + bold if stalepercent < 1 else "y" + bold, "r"), \
        "invalid": ("%.0f (%.1f%%)" % (worker["invalid"], invalidpercent), "r" + bold if invalidpercent > invalidcritical else "g" + bold if invalidpercent < invalidwarning else "y" + bold, "r"), \
        "mhps": ("%.2f" % worker["mhps"], bold, "r"), \
        "avgmhps": ("%.2f" % (worker["mhashes"] / uptime), bold, "r"), \
        "efficiency": ("%.1f%%" % efficiency, "r" + bold if efficiency < 80 else "g" + bold if efficiency > 95 else "y" + bold, "r"), \
        "temperature": ("%.1f" % worker["temperature"], "r" + bold if worker["temperature"] > tempcritical else "y" + bold if worker["temperature"] > tempwarning else "g" + bold, "c") if "temperature" in worker and worker["temperature"] != None else ("", bold, "c"), \
        "currentpool": (worker["currentpool"] if "currentpool" in worker and worker["currentpool"] != None else "Unknown", bold, "c"), \
      })
      self.translateworkerdata(worker["children"], workerstats, indent + 2)
      
  def drawtable(self, y, columns, stats):
    for column in columns:
      self.mainwin.addstr(y, column["x"], column["title1"].center(column["width"]))
      self.mainwin.addstr(y + 1, column["x"], column["title2"].center(column["width"]), curses.A_UNDERLINE)
      if column["x"] > 0: self.mainwin.vline(y, column["x"] - 1, curses.ACS_VLINE, len(stats) + 2)
      cy = y + 2
      last = cy + len(stats) - 1
      for row in stats:
        data = row[column["field"]]
        if data[2] == "r": text = data[0].rjust(column["width"])
        elif data[2] == "c": text = data[0].center(column["width"])
        else: text = data[0].ljust(column["width"])
        attr = 0 if cy == last else curses.A_UNDERLINE
        if "r" in data[1]: attr = attr | self.red
        elif "y" in data[1]: attr = attr | self.yellow
        elif "g" in data[1]: attr = attr | self.green
        if "B" in data[1]: attr = attr | curses.A_BOLD
        if "U" in data[1]: attr = attr | curses.A_UNDERLINE
        self.mainwin.addstr(cy, column["x"], text, attr)
        cy = cy + 1

  def mainloop(self):
    while True:
      try:
        pooldata = self.miner.collectstatistics(self.miner.pools)
        workerdata = self.miner.collectstatistics(self.miner.workers)
        poolstats = []
        self.translatepooldata(pooldata, poolstats)
        poolcolumns = []
        x = 0
        width = max(4, self.calculatemaxfieldlen(poolstats, "name", 2))
        poolcolumns.append({"title1": "Pool", "title2": "name", "field": "name", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "longpolling"))
        poolcolumns.append({"title1": "Long", "title2": "poll", "field": "longpolling", "x": x, "width": width})
        x = x + 1 + width
        width = max(5, self.calculatemaxfieldlen(poolstats, "difficulty"))
        poolcolumns.append({"title1": "", "title2": "Diff.", "field": "difficulty", "x": x, "width": width})
        x = x + 1 + width
        width = max(8, self.calculatemaxfieldlen(poolstats, "requests"))
        poolcolumns.append({"title1": "Job", "title2": "requests", "field": "requests", "x": x, "width": width})
        x = x + 1 + width
        width = max(10, self.calculatemaxfieldlen(poolstats, "failedreqs"))
        poolcolumns.append({"title1": "Failed job", "title2": "requests", "field": "failedreqs", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "jobsaccepted"))
        poolcolumns.append({"title1": "Acc.", "title2": "jobs", "field": "jobsaccepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(poolstats, "longpollkilled"))
        poolcolumns.append({"title1": "Rej.", "title2": "jobs", "field": "longpollkilled", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(poolstats, "accepted"))
        poolcolumns.append({"title1": "Acc.", "title2": "shares", "field": "accepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(poolstats, "rejected"))
        poolcolumns.append({"title1": "Stale shares", "title2": "(rejected)", "field": "rejected", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(poolstats, "uploadretries"))
        poolcolumns.append({"title1": "Share upload", "title2": "retries", "field": "uploadretries", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(poolstats, "avgmhps"))
        poolcolumns.append({"title1": "Average", "title2": "MHash/s", "field": "avgmhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(poolstats, "efficiency"))
        poolcolumns.append({"title1": "Effi-", "title2": "ciency", "field": "efficiency", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(poolstats, "score"))
        poolcolumns.append({"title1": "Current", "title2": "bias", "field": "score", "x": x, "width": width})
        workerstats = []
        self.translateworkerdata(workerdata, workerstats)
        workercolumns = []
        x = 0
        width = max(6, self.calculatemaxfieldlen(workerstats, "name", 2))
        workercolumns.append({"title1": "Worker", "title2": "name", "field": "name", "x": x, "width": width})
        x = x + 1 + width
        width = max(4, self.calculatemaxfieldlen(workerstats, "jobsaccepted"))
        workercolumns.append({"title1": "Acc.", "title2": "jobs", "field": "jobsaccepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(workerstats, "accepted"))
        workercolumns.append({"title1": "Acc.", "title2": "shares", "field": "accepted", "x": x, "width": width})
        x = x + 1 + width
        width = max(10, self.calculatemaxfieldlen(workerstats, "rejected"))
        workercolumns.append({"title1": "Stales", "title2": "(rejected)", "field": "rejected", "x": x, "width": width})
        x = x + 1 + width
        width = max(12, self.calculatemaxfieldlen(workerstats, "invalid"))
        workercolumns.append({"title1": "Invalids", "title2": "(K not zero)", "field": "invalid", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "mhps"))
        workercolumns.append({"title1": "Current", "title2": "MHash/s", "field": "mhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "avgmhps"))
        workercolumns.append({"title1": "Average", "title2": "MHash/s", "field": "avgmhps", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "temperature"))
        workercolumns.append({"title1": "Temp.", "title2": "(deg C)", "field": "temperature", "x": x, "width": width})
        x = x + 1 + width
        width = max(6, self.calculatemaxfieldlen(workerstats, "efficiency"))
        workercolumns.append({"title1": "Effi-", "title2": "ciency", "field": "efficiency", "x": x, "width": width})
        x = x + 1 + width
        width = max(7, self.calculatemaxfieldlen(workerstats, "currentpool"))
        workercolumns.append({"title1": "Current", "title2": "pool", "field": "currentpool", "x": x, "width": width})
        with self.miner.conlock:
          try:
            self.ysplit = 10 + len(poolstats) + len(workerstats)
            (my, mx) = self.mainwin.getmaxyx()
            self.mainwin.erase()
            self.mainwin.hline(1, 0, curses.ACS_HLINE, mx)
            self.mainwin.hline(self.ysplit - 1, 0, curses.ACS_HLINE, mx)
            self.mainwin.addstr(0, (mx - len(self.miner.useragent)) // 2, self.miner.useragent, curses.A_BOLD)
            inqueue = self.miner.queue.qsize()
            try: queueseconds = (inqueue / self.miner.jobspersecond)
            except: queueseconds = 0
            color = self.red if inqueue <= self.miner.queuelength * 1 / 10 else self.green if inqueue >= self.miner.queuelength * 9 / 10 - 1 else self.yellow
            self.mainwin.addstr(2, 0, "Total speed: ")
            self.mainwin.addstr(("%.1f MH/s" % self.miner.mhps).rjust(11), curses.A_BOLD)
            self.mainwin.addstr(" - Buffer: ")
            self.mainwin.addstr(("%d" % inqueue).ljust(2), color | curses.A_BOLD)
            self.mainwin.addstr("/", color)
            self.mainwin.addstr(("%d" % self.miner.queuelength).rjust(2), color | curses.A_BOLD)
            self.mainwin.addstr(" (", color)
            self.mainwin.addstr(("%.2f" % queueseconds), color | curses.A_BOLD)
            self.mainwin.addstr(" seconds)", color)
            self.drawtable(4, poolcolumns, poolstats)
            self.drawtable(7 + len(poolstats), workercolumns, workerstats)
            self.mainwin.noutrefresh()
            (my, mx) = self.mainwin.getmaxyx()
            (ly, lx) = self.logwin.getmaxyx()
            self.logwin.refresh(ly - my + self.ysplit - 1, 0, self.ysplit, 0, min(my, ly - 1 + self.ysplit) - 1, min(mx, lx) - 1)
          except:
            try:
              self.mainwin.erase()
              self.mainwin.addstr(0, 0, "Failed to display stats!\nWindow is probably too small.", self.red | curses.A_BOLD)
              self.mainwin.refresh()
            except: pass
      except Exception as e:
        self.miner.log("Exception while updating CursesUI stats: %s\n" % traceback.format_exc(), "rB")
      time.sleep(self.updateinterval)

  def message(self, date, str, format):
    attr = 0
    if "r" in format: attr = self.red
    elif "y" in format: attr = self.yellow
    elif "g" in format: attr = self.green
    if "B" in format: attr = attr | curses.A_BOLD
    if "U" in format: attr = attr | curses.A_UNDERLINE
    for i in range(5):
      try:
        self.logwin.addstr(date)
        self.logwin.addstr(str, attr)
        break
      except: pass
    if "\n" in str:
      for i in range(5):
        try:
          (my, mx) = self.mainwin.getmaxyx();
          (ly, lx) = self.logwin.getmaxyx();
          self.logwin.refresh(ly - my + self.ysplit - 1, 0, self.ysplit, 0, min(my, ly - 1 + self.ysplit) - 1, min(mx, lx) - 1)
          break
        except: pass
