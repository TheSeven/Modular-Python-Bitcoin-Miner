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

mod.loggadget = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "box", "event"], callback);
    },

    // Shows a statistics dashboard
    "Gadget": function(box, config)
    {
        mod.dom.clean(box.contentNode);
        box.setTitle(nls("Log"));
        var div = document.createElement("div");
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        table.appendChild(tbody);
        div.allowSelect = true;
        div.allowDrag = true;
        div.allowContextMenu = true;
        div.style.cursor = "text";
        div.style.backgroundColor = "#000";
        div.style.color = "#fff";
        div.style.height = "400px";
        div.style.overflow = "auto";
        div.appendChild(table);
        box.contentNode.appendChild(div);
        
        function pad(value, length)
        {
            value = String(value);
            while (value.length < length) value = "0" + value;
            return value;
        }
        
        mod.csc.request("log", "stream", {}, function(data)
        {
            for (var i in data)
                if (data.hasOwnProperty(i))
                {
                    var tr = document.createElement("tr");
                    var td1 = document.createElement("td");
                    var td2 = document.createElement("td");
                    var td3 = document.createElement("td");
                    var d = new Date(data[i].timestamp);
                    var timestamp = pad(d.getFullYear(), 4) + "-" + pad(d.getMonth() + 1, 2) + "-"
                                  + pad(d.getDate(), 2) + " " + pad(d.getHours(), 2) + ":"
                                  + pad(d.getMinutes(), 2) + ":" + pad(d.getSeconds(), 2) + "." 
                                  + pad(d.getMilliseconds(), 3);
                    td1.style.padding = "0px 3px";
                    td1.appendChild(document.createTextNode(timestamp));
                    td2.style.padding = "0px 3px";
                    td2.style.textAlign = "right";
                    td2.appendChild(document.createTextNode("[" + data[i].loglevel + "]"));
                    td3.style.padding = "0px 3px";
                    for (var j in data[i].message)
                      if (data[i].message.hasOwnProperty(j))
                      {
                          var span = document.createElement("span");
                          var format = data[i].message[j].format;
                          if (format.indexOf("r") != -1) span.style.color = "#f00";
                          if (format.indexOf("y") != -1) span.style.color = "#ff0";
                          if (format.indexOf("g") != -1) span.style.color = "#0f0";
                          if (format.indexOf("B") != -1) span.style.fontWeight = "bold";
                          span.appendChild(document.createTextNode(data[i].message[j].data));
                          td3.appendChild(span);
                      }
                    tr.appendChild(td1);
                    tr.appendChild(td2);
                    tr.appendChild(td3);
                    tbody.appendChild(tr);
                    div.scrollTop = div.scrollHeight;
                }
        }, { "cache": "none", "stream": true, "noindicator": true });
    }

};
