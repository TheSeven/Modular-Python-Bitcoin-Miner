// Modular Python Bitcoin Miner WebUI
// Copyright (C) 2012 Michael Sparmann (TheSeven)
//
//     This program is free software; you can redistribute it and/or
//     modify it under the terms of the GNU General Public License
//     as published by the Free Software Foundation; either version 2
//     of the License, or (at your option) any later version.
//
//     This program is distributed in the hope that it will be useful,
//     but WITHOUT ANY WARRANTY; without even the implied warranty of
//     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//     GNU General Public License for more details.
//
//     You should have received a copy of the GNU General Public License
//     along with this program; if not, write to the Free Software
//     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
//
// Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
// want to support further development of the Modular Python Bitcoin Miner.

mod.uiconfig = {

  "data": {},

  "timeout": false,

  // Module initialisation: Check that all dependencies are satisfied
  "init": function(callback)
  {
    depend(["csc"], function()
    {
      mod.csc.request("uiconfig", "read", {}, function(data)
      {
        mod.uiconfig.data = data;
        callback();
      });
    });
  },

  // Accumulate config update requests for up to 10 seconds, and then send the config to the server
  "update": function()
  {
    if (mod.uiconfig.timeout) return;
    mod.uiconfig.timeout = setTimeout(function()
    {
      mod.uiconfig.timeout = false;
      mod.csc.request("uiconfig", "write", mod.uiconfig.data);
    }, 10000);
  }

};