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

mod.theme.data["default"] = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["dom", "layerbox"], callback);
    },

    // Load the stylesheet and set up a bunch of divs to contain other components
    "InlineUI": function(range, config)
    {
        if ((typeof config) == "string") config = JSON.parse(config);
        var oldcount = document.styleSheets.length;
        var style = document.createElement("link");
        var hook;
        var content;
        var alive = true;
        mod.dom.clean(range);
        mod.layerbox.setParams({"xmin": 250, "xmax": 350, "xstep": 20,
                                "ymin": 100, "ymax": 180, "ystep": 20});
        style.rel = "stylesheet";
        style.type = "text/css";
        style.href = "static/theme/data/default/default.css";
        document.getElementsByTagName("head")[0].appendChild(style);
        function wait()
        {
            if (!alive) return;
            if (document.styleSheets.length < oldcount + 1) setTimeout(wait, 10);
            else
            {
                content = document.createElement("div");
                content.style.position = "absolute";
                content.style.left = "0px";
                content.style.right = "0px";
                content.style.top = "0px";
                content.style.bottom = "0px";
                content.style.overflow = "auto";
                range.appendChild(content);
                var module = config.module;
                var moduleparam = config.moduleparam;
                if (params.module)
                {
                    module = params.module;
                    moduleparam = params.moduleparam;
                }
                delegate(content, module, moduleparam);
                callback();
            }
        }
        wait();

        this.releaseRange = function()
        {
            alive = false;
            if (hook) hook.unhook();
            if (content && content.owner && content.owner.releaseRange) content.owner.releaseRange();
            style.parentNode.removeChild(style);
        }
    }

};