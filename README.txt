Modular Python Bitcoin Miner
Copyright (C) 2011-2012 Michael Sparmann (TheSeven)

    This program is free software; you can redistribute it and/or
    modify it under the terms of the GNU General Public License
    as published by the Free Software Foundation; either version 2
    of the License, or (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program; if not, write to the Free Software
    Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.

Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
want to support further development of the Modular Python Bitcoin Miner.


System Requirements
===================

The default user interface module uses the python curses module. Most Linux distributions should
have a package for this. Unofficial Windows curses modules are available here:
http://www.lfd.uci.edu/~gohlke/pythonlibs/#curses

Miner backend modules might use interface modules like PyUSB or PySerial as well.


Configuration
=============

You can configure MPBM by copying the default_config.py file to config.py
and modifying it to fit your needs. This file describes the
front and back end modules that will be used by the MPBM core.
default_config.py is already pre-populated with some sample entries.
More advanced options that aren't present in the example config file
are documented at the top of the corresponding python module file.


Customizing
===========

If you don't want to use one of the already supported mining workers,
you will have to write your own worker module. Just duplicate e.g. simplers232.py,
adapt it to fit your needs, and reference your new module from config.py.
Things are mostly straightforward and that file has more comments than code,
but if you run into trouble or didn't understand some details, feel free to contact
TheSeven (or [7]) on irc.freenode.net. I'll try to help if I have time.
Offering some bitcoins might encourage me to not be lazy :)
