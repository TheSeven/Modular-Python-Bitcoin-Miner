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

mod.nls = {

  // Module initialisation: Check that all dependencies are satisfied
  "init": function(callback)
  {
    window.nls = mod.nls.translate;
    depend(["event"], callback);
  },

  // Load the default language pack
  "Service": function(callback)
  {
    mod.nls.loadlang(lang, callback);
  },

  // Translate a message, if possible
  "translate": function(message, category)
  {
    if (!category) category = "general";
    if (mod.nls.data)
    {
      if ((typeof mod.nls.data[category]) == "undefined")
        log("nls: Category not found in lang " + lang + ": "+category);
      else if (!mod.nls.data[category]);
      else if ((typeof mod.nls.data[category][message]) == "undefined")
        log("nls: Message not found in lang " + lang + ", category "+category+": "+message);
      else if ((typeof mod.nls.data[category][message]) == "string")
        return mod.nls.data[category][message];
    }
    return message;
  },

  // Load a language pack
  "loadlang": function(lang,callback)
  {
    httprequest({"method": "GET", "uri": "static/nls/lang/" + lang + ".json", "callback": function(data)
      {
        mod.nls.data = eval("(" + data.substr(data.indexOf("{")) + ")");
        mod.event.trigger("nls_changed");
        if (callback) callback();
      }, "error": function(data)
      {
        log("nls: Unsupported lang " + lang + "!");
        if (callback) callback();
      }
    });
  }

};