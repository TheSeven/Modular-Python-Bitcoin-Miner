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

mod.debugmenu = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "layerbox", "uiconfig"], callback);
    },

    // Shows the frontend editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(nls("Debug menu"));
        box.setOuterWidth("200px");
        
        var buttons =
        [
            {"name": "Dump thread states", "module": "debugviewer", "moduleparam": {"function": "dumpthreadstates", "title": nls("Dump thread states")}},
        ]
        
        for (var i in buttons)
            if (buttons.hasOwnProperty(i))
            {
                var button = document.createElement("input");
                button.type = "button";
                button.style.width = "100%";
                button.value = nls(buttons[i].name);
                button.data = buttons[i];
                button.onclick = buttons[i].handler ? buttons[i].handler : function(e)
                {
                    var obj = this;
                    depend([obj.data.module], function()
                    {
                        mod[obj.data.module].LayerUI(obj.data.moduleparam);
                    });
                }
                box.contentNode.appendChild(button);
            }
        
        function saveconfiguration(e)
        {
            var obj = this;
            obj.disabled = true;
            obj.value = nls("Please wait...");
            mod.csc.request("menugadget", "saveconfiguration", {}, function(data)
            {
                if (data.error) return error(data.error);
                obj.value = nls("Save configuration");
                obj.disabled = false;
            }, {"cache": "none"});
        }
    }

};
