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

mod.debugviewer = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "layerbox", "uiconfig"], callback);
    },

    // Shows the frontend editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(config.title);
        if (!mod.uiconfig.data.debugviewer) mod.uiconfig.data.debugviewer = {};
        if (!mod.uiconfig.data.debugviewer.height) mod.uiconfig.data.debugviewer.height = "500px";
        if (!mod.uiconfig.data.debugviewer.width) mod.uiconfig.data.debugviewer.width = "700px";
        box.setOuterHeight(mod.uiconfig.data.debugviewer.height);
        box.setOuterWidth(mod.uiconfig.data.debugviewer.width);
        box.setResizable(true, true, function()
        {
            mod.uiconfig.data.debugviewer.height = box.rootNode.style.height;
            mod.uiconfig.data.debugviewer.width = box.rootNode.style.width;
            mod.uiconfig.update();
        });
        var div = document.createElement("div");
        div.className = "pre autocursor";
        div.style.height = "100%";
        div.style.overflow = "auto";
        div.allowSelect = true;
        div.allowDrag = true;
        div.allowContextMenu = true;
        box.contentNode.appendChild(div);
        var refreshButton = document.createElement("input");
        refreshButton.type = "button";
        refreshButton.value = nls("Refresh");
        refreshButton.className = "box_titlebutton";
        refreshButton.style.cssFloat = "right";
        refreshButton.onclick = refresh;
        box.titleNode.appendChild(refreshButton);
        refresh();
        function refresh()
        {
            showLoadingIndicator(div);
            mod.csc.request("debug", config["function"], {}, function(data)
            {
                mod.dom.clean(div);
                div.appendChild(document.createTextNode(data.data));
            }, { "cache": "none" });
        }
    }

};
