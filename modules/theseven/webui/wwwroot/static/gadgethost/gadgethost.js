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

mod.gadgethost = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "box"], callback);
    },

    // Displays a collection of gadgets
    "InlineUI": function(range, config)
    {
        mod.dom.clean(range);

        var handles = [];
        mod.dom.clean(range);
        this.releaseRange = function()
        {
            for (var i in handles)
                if (handles.hasOwnProperty(i) && handles[i].releaseRange)
                    handles[i].releaseRange();
        };

        function loadgadget(box, module, moduleparam)
        {
            depend([module], function()
            {
                handles.push(new mod[module].Gadget(box, moduleparam));
            });
        }

        mod.csc.request("gadgethost", "getgadgets", { "collection": config }, function(data)
        {
            mod.dom.clean(range);
            var table = document.createElement("table");
            table.style.width = "100%";
            var tbody = document.createElement("tbody");
            var tr = document.createElement("tr");
            for (var i in data)
                if (data.hasOwnProperty(i))
                {
                    var td = document.createElement("td");
                    if (data[i].width) td.style.width = data[i].width + "px";
                    var table2 = document.createElement("table");
                    table2.style.width = "100%";
                    var tbody2 = document.createElement("tbody");
                    for (var j in data[i].entries)
                        if (data[i].entries.hasOwnProperty(j))
                        {
                            var tr2 = document.createElement("tr");
                            var td2 = document.createElement("td");
                            if (data[i].entries[j].height) td2.style.height = data[i].entries[j].height + "px";
                            td2.style.padding = "1px";
                            var box = new mod.box.Box();
                            box.setOuterWidth("100%");
                            box.setOuterHeight("100%");
                            loadgadget(box, data[i].entries[j].module, data[i].entries[j].moduleparam);
                            td2.appendChild(box.rootNode);
                            tr2.appendChild(td2);
                            tbody2.appendChild(tr2);
                        }
                    table2.appendChild(tbody2);
                    td.appendChild(table2);
                    tr.appendChild(td);
                }
            tbody.appendChild(tr);
            table.appendChild(tbody);
            range.appendChild(table);
        });
    }

};
