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

mod.contextmenu = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["event"], callback);
    },

    "ContextMenu": function(style)
    {
        if (!style) style = "";
        var obj = this;

        this.window = window;
        this.rootNode = document.createElement("div");
        this.rootNode.className = "contextmenu contextmenu_" + style;
        this.rootNode.style.position = "absolute";
        this.rootNode.style.zIndex = 50000;

        this.rootNode.onmouseout = function()
        {
            obj.timeout = setTimeout(obj.hide, 1000);
        };

        this.rootNode.onmouseover = function()
        {
            if (obj.timeout) clearTimeout(obj.timeout);
        };

        this.addEntry = function(name, callback, buttonstyle)
        {
            var text = document.createTextNode(name);
            var node = document.createElement("div");
            node.className = "contextmenu_entry contextmenu_" + style + "_entry";
            if (buttonstyle) node.className += " " + buttonstyle;
            node.appendChild(text);
            obj.rootNode.appendChild(node);
            if (!callback) callback = killEvent;
            node.onmousedown = callback;
            return node;
        };

        this.addBarrier = function(barrierstyle)
        {
            var node = document.createElement("div");
            node.className = "contextmenu_barrier contextmenu_" + style + "_barrier";
            if (barrierstyle) node.className += " " + barrierstyle;
            obj.rootNode.appendChild(node);
            node.onmousedown = killEvent;
            return node;
        };

        this.show = function(e)
        {
            if (!e) e = window.event;
            obj.rootNode.style.left = e.clientX + "px";
            obj.rootNode.style.top = e.clientY + "px";
            document.getElementById("container").appendChild(obj.rootNode);
            obj.mousehook = mod.event.hook("windowmousedown", obj.hide);
            obj.keyhook = mod.event.catchKey(27, obj.hide);
            return killEvent(e);
        };

        this.hide = function(e)
        {
            if (obj.keyhook) obj.keyhook.unhook();
            if (obj.mousehook) obj.mousehook.unhook();
            if (obj.rootNode.parentNode) obj.rootNode.parentNode.removeChild(obj.rootNode);
            return killEvent(e);
        };

    }

};