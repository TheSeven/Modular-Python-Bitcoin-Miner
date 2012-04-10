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



################
# Bootstrapper #
################



import sys
import time
import signal
from optparse import OptionParser
from core.core import Core


if __name__ == "__main__":

  # Set up command line argument parset
  parser = OptionParser("Usage: %prog [instancename] [options]", version = Core.version)
  parser.add_option("--default-loglevel", "-l", action = "store", type = "int", default = 500,
                    help = "Set the default loglevel for new loggers and the fallback logger")
  parser.add_option("--detect-frontends", action = "store_true", default = False,
                    help = "Autodetect available frontends and add them to the instance")
  parser.add_option("--detect-workers", action = "store_true", default = False,
                    help = "Autodetect available workers and add them to the instance")
  parser.add_option("--add-example-work-sources", action = "store_true", default = False,
                    help = "Add the example work sources to the instance")
  (options, args) = parser.parse_args()
  
  # Figure out instance name
  if len(args) == 0: instancename = "default"
  elif len(args) == 1: instancename = args[0]
  else: parser.error("Incorrect number of arguments")

  # Create core instance, will load saved instance state if present
  core = Core(instance = instancename, default_loglevel = options.default_loglevel)
  
  # Autodetect appropriate frontends if requested or if a new instance is being set up
  if options.detect_frontends or core.is_new_instance:
    core.detect_frontends()
  
  # Autodetect available workers if requested or if a new instance is being set up
  if options.detect_workers or core.is_new_instance:
    core.detect_workers()

  # Add example work sources if requested or if a new instance is being set up
  if options.add_example_work_sources or core.is_new_instance:
    from core.blockchain import Blockchain
    from core.worksourcegroup import WorkSourceGroup
    from modules.theseven.bcjsonrpc.bcjsonrpcworksource import BCJSONRPCWorkSource
    # Find the Bitcoin block chain, or create it if neccessary
    blockchain = core.get_blockchain_by_name("Bitcoin")
    if not blockchain:
      blockchain = Blockchain(core)
      blockchain.settings.name = "Bitcoin"
      core.add_blockchain(blockchain)
    # Save the old root work source (will be moved around)
    usersources = core.get_root_work_source()
    # Create the new root work source group
    newroot = WorkSourceGroup(core)
    # Copy the old root work source's name to the new one
    newroot.settings.name = usersources.settings.name
    # Reconfigure the old root work source
    usersources.settings.name = "User work sources"
    usersources.settings.priority = 1000
    usersources.apply_settings()
    newroot.add_work_source(usersources)
    # Create example work source group
    examplesources = WorkSourceGroup(core)
    examplesources.settings.name = "Example/donation work sources"
    examplesources.settings.priority = 10
    examplesources.apply_settings()
    newroot.add_work_source(examplesources)
    # Register the new root work source
    core.set_root_work_source(newroot)
    # Add example work sources to their group
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "BTCMP (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "rr.btcmp.com"
    worksource.settings.port = 7332
    worksource.settings.username = "TheSeven.worker"
    worksource.settings.password = "TheSeven"
    worksource.apply_settings()
    examplesources.add_work_source(worksource)
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "BTCGuild (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "mine3.btcguild.com"
    worksource.settings.username = "TheSeven_guest"
    worksource.settings.password = "x"
    worksource.settings.longpollconnections = 0
    worksource.apply_settings()
    examplesources.add_work_source(worksource)
    worksource = BCJSONRPCWorkSource(core)
    worksource.set_blockchain(blockchain)
    worksource.settings.name = "Eligius (donation)"
    worksource.settings.priority = 1
    worksource.settings.host = "mining.eligius.st"
    worksource.settings.port = 8337
    worksource.settings.username = "1FZMW7BCzExsLmErT2o8oCMLcMYKwd7sHQ"
    worksource.settings.longpollconnections = 0
    worksource.apply_settings()
    examplesources.add_work_source(worksource)
    
  def stop(signum, frame):
    core.stop()
    sys.exit(0)
    
  signal.signal(signal.SIGINT, stop)
  signal.signal(signal.SIGTERM, stop)
  core.start()
  
  while True: time.sleep(100)
