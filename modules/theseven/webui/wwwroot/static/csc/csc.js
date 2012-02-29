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

mod.csc=  {

  // Module initialisation: Check that all dependencies are satisfied
  "init": function(callback)
  {
    depend(["json"], callback);
  },

  // Send a request to the server and call a callback as soon as the response arrives
  "request":function(module, filename, request, callback, params)
  {
    if (!params) params = new Array();
    params.method = "POST";
    params.uri = "api/" + module + "/" + filename;
    params.data = JSON.stringify(request);
    params.callback = function(data)
    {
      callback(JSON.parse(data));
    };
    if (!params.header) params.header = new Array();
    if (!params.header["Content-Type"]) params.header["Content-Type"] = "application/json";
    httprequest(params);
  }

};