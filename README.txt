Modular Python Bitcoin Miner
Copyright (C) 2012 Michael Sparmann (TheSeven)

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

MPBM requires Python >= 2.6, most testing is done with Python 3.2.

The default user interface module uses the python curses module. Most Linux distributions
should have a package for this. Unofficial Windows curses modules are available here:
http://www.lfd.uci.edu/~gohlke/pythonlibs/#curses

Miner backend modules might use interface modules like PyUSB or PySerial as well.


Getting started
===============

1. Install the required prerequisites (see System Requirements above)
2. Run the following command in the mpbm directory: python run-mpbm.py
3. Connect to http://localhost:8832 with your favorite web browser
4. Login with user name "admin" and password "mpbm"
5. Go to "Frontends", "WebUI" and change the default login credentials
6. Customize workers and work sources if neccessary


Customizing
===========

If you don't want to use one of the already supported mining workers,
you will have to write your own worker module. Just duplicate e.g.
the modules/theseven/simplers232 tree and adapt it to fit your needs.
Things are mostly straightforward and that file has more comments than code,
but if you run into trouble or didn't understand some details, feel free to contact
TheSeven (or [7]) on irc.freenode.net. I'll try to help if I have time.
Offering some bitcoins might encourage me to not be lazy :)
