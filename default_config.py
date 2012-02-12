# Modular Python Bitcoin Miner demonstration configuration file
# Copy this file to config.py and modify it to fit your needs.


################################
# List of modules to be loaded #
################################

import frontend.theseven.cursesui
import frontend.theseven.simplelogger
import pool.theseven.bcjsonrpc
#import worker.theseven.simplers232
#import worker.theseven.icarus
#import worker.fpgamining.x6500
import worker.fpgamining.x6500hotplug


###################
# Global settings #
###################

#bufferseconds = 50      # Work buffer size in seconds (default: 50). This should generally be no
#                        # more than 60 seconds, otherwise you will get increased stale rates!
#getworktimeout = 2      # Work source response timeout in seconds (default: 2)
#sendsharetimeout = 10   # Share upload timeout in seconds (default: 10)
#longpolltimeout = 900   # Long poll connection inactivity timeout in seconds (default: 900)
#longpollgrouptime = 30  # Long poll aggregation timeout in seconds (default: 30)
#longpollgrouptime = 30  # Long poll aggregation timeout in seconds (default: 30)

# DON'T PLAY WITH THESE UNLESS YOU KNOW WHAT YOU'RE DOING!
#getworkbias = -1  # Bias (in MHashes) that is credited to the work source for every work
#                  # request (default: -1). This punishes work sources which cancel their
#                  # work very often, but the default value effectively disables this
#                  # behavior. This needs to be negative (non-zero) though, in order
#                  # to ensure that work requests are distributed evenly between work
#                  # sources during startup.
#longpollkillbias = 0  # Bias (in MHashes) that is credited to the work source for every piece
#                      # of work that was invalidated by a long poll (default: 0). This is
#                      # used to compensate for anomalies caused by getworkbias.
#getworkfailbias = -3000  # Bias (in MHashes) that is credited to the work source for every
#                         # failed work request (default: -3000). This punishes work source
#                         # downtime in general.
#jobstartbias = 0  # Bias (in MHashes) that is credited to the work source everytime
#                  # a job of that work source starts being processed on a worker (default: 0).
#jobfinishbias = 0  # Bias (in MHashes) that is credited to the work source everytime
#                   # a job of that work source ends being processed on a worker (default: 0).
#sharebias = 4000  # Bias (in MHashes) that is multiplied with the difficulty and credited
#                  # to the work source for each found share (default: 4000). This rewards
#                  # work sources with high efficiency. Keep it near the default value to
#                  # ensure that work sources which produce junk work (that never yields
#                  # shares) can not consume much hashing power.
#uploadfailbias = -100  # Bias (in MHashes) that is and credited to the work source for
#                       # each share upload retry (default: -100). Because a huge bias
#                       # doesn't keep a work source from retrying to upload the share,
#                       # you should keep this relatively low to ensure that the work
#                       # source will be used again when it pops back to life. Work source
#                       # downtime should be punished using getjobfailbias instead.
#stalebias = -15000  # Bias (in MHashes) that is multiplied by the difficulty and credited
#                    # to the work source for each stale share (default: -15000). With the
#                    # default settings this will half the work source's hashing power at
#                    # a stale rate of about 2%.
#biasdecay = 0.9995  # Decay factor that is multiplied onto all work sources' bias on every
#                    # getwork on any work source (default: 0.9995). Helps ensuring that
#                    # work sources will be favored after they recover from temporary
#                    # failures until they have caught up with the configured priority.


###########################
# List of user interfaces #
###########################

interfaces = [ \

  # Curses UI
  { \
    # User interface module
    "type": frontend.theseven.cursesui.CursesUI, \
    # Update stats every second (default)
    "updateinterval": 1, \
  }, \

  # Simple logger
  { \
    # User interface module
    "type": frontend.theseven.simplelogger.SimpleLogger, \
    # Log file location (default)
    "logfile": "miner.log", \
  }, \

]


###################
# List of workers #
###################

workers = [ \

#  # SimpleRS232 worker
#  { \
#    # Worker module
#    "type": worker.theseven.simplers232.SimpleRS232Worker, \
#    # Worker module parameters, in this case serial port name (default: /dev/ttyS0)
#    "port": "/dev/ttyUSB0", \
#  }, \

#  # Single X6500 worker
#  { \
#    # Worker module
#    "type": worker.fpgamining.x6500.X6500Worker, \
#    # Worker module parameters, in this case board serial number (default: take first available)
#    #"deviceid": "ABCDEFGH", \
#  }, \

  # X6500 hotplug worker
  { \
    # Worker module
    "type": worker.fpgamining.x6500hotplug.X6500HotplugWorker, \
  }, \

#  # Icarus worker
#  { \
#    # Worker module
#    "type": worker.theseven.icarus.IcarusWorker, \
#    # Worker module parameters, in this case serial port name (default: /dev/ttyUSB0)
#    "port": "/dev/ttyUSB0", \
#  }, \

]


########################
# List of work sources #
########################

# MPBM supports multiple blockchains and aggregates long poll responses
# from all pools within a blockchain to further reduce stales.
# Work from all pools within a blockchain is flushed as soon as any of
# the pools responds to a long poll (subsequent long poll responses from
# other pools within the next seconds will be suppressed).
# This means that e.g. P2Pool will need to be put into a separate blockchain
# definition because its long poll responses don't correlate with other pools.

# The available hashing power (from all workers) can be distributed across
# different work sources by adjusting the priority values. MPBM will attempt
# to distribute hash rate proportionally to these priorities, unless a work
# source fails. If that happens, the work source's priority will be reduced
# and slowly be increased again when the work source comes back to life.
# You can see this in action with the P2Pool entry in the default config
# if you don't have a P2Pool instance running on localhost.

# If you want to support further development of MPBM, you can do me a favor by
# leaving the demo pool entries active, and just adding your own one below them.
# If you give your own pool entries a total priority of 1000, you will donate
# 1% (on average) of your total hash rate to the author of this software.
# This won't make a big difference for you, but it does for me.
# Templates for that can be found below the demo pool entries.

blockchains = [ \

  # Regular bitcoin blockchain
  { \
    # Pools to be used for this blockchain
    "pools": [ \

      # Sample pool entry (BTCMP)
      # Please leave this entry active to support further development of this software (see above)
      { \
        # Pool interface module
        "type": pool.theseven.bcjsonrpc.JSONRPCPool, \
        # Display name of the pool (default: host name)
        "name": "BTCMP (demo)", \
        # Priority (default: 1)
        "priority": 2, \
        # Host name of the pool
        "host": "rr.btcmp.com", \
        # HTTP port of the pool (default: 8332)
        "port": 7332, \
        # HTTP authentication user name (default: no authentication)
        "username": "TheSeven.worker", \
        # HTTP authentication password (default: empty)
        "password": "TheSeven", \
      }, \

      # Sample pool entry (BTC Guild)
      # Please leave this entry active to support further development of this software (see above)
      { \
        # Pool interface module
        "type": pool.theseven.bcjsonrpc.JSONRPCPool, \
        # Display name of the pool (default: host name)
        "name": "BTCGuild (demo)", \
        # Priority (default: 1)
        "priority": 6, \
        # Host name of the pool
        "host": "btcguild.com", \
        # HTTP authentication user name (default: no authentication)
        "username": "TheSeven_guest", \
        # HTTP authentication password (default: empty, but BTC Guild doesn't like that)
        "password": "x", \
      }, \

      # Sample pool entry (Eligius)
      # Please leave this entry active to support further development of this software (see above)
      { \
        # Pool interface module
        "type": pool.theseven.bcjsonrpc.JSONRPCPool, \
        # Display name of the pool (default: host name)
        "name": "Eligius (demo)", \
        # Priority (default: 1)
        "priority": 2, \
        # Host name of the pool
        "host": "mining.eligius.st", \
        # HTTP port of the pool (default: 8332)
        "port": 8337, \
        # HTTP authentication user name (default: no authentication)
        "username": "1FZMW7BCzExsLmErT2o8oCMLcMYKwd7sHQ", \
      }, \

#     # Your own pool entry
#     { \
#       # Pool interface module
#       "type": pool.theseven.bcjsonrpc.JSONRPCPool, \
#       # Display name of the pool (default: host name)
#       "name": "My primary pool", \
#       # Priority (default: 1)
#       "priority": 1000, \
#       # Host name of the pool
#       "host": "mining.mypool.com", \
#       # HTTP port of the pool (default: 8332)
#       "port": 8332, \
#       # HTTP authentication user name (default: no authentication)
#       "username": "MyUsername", \
#       # HTTP authentication password (default: empty)
#       "password": "MyPassword", \
#     }, \

    ], \
  }, \

# # P2Pool sharechain
# { \
#   # Pools to be used for this blockchain
#   "pools": [ \
#
#   # P2Pool instance on localhost
#   { \
#       # Pool interface module
#       "type": pool.theseven.bcjsonrpc.JSONRPCPool, \
#       # Display name of the pool (default: host name)
#       "name": "P2Pool", \
#       # Priority (default: 1)
#       "priority": 1000, \
#       # Host name of the pool
#       "host": "127.0.0.1", \
#       # HTTP port of the pool (default: 8332)
#       "port": 9332, \
#     }, \
#
#   ], \
# }, \

]
