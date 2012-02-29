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

mod.dom = {

    // Remove all children of a specified DOM node
    "clean": function(node)
    {
        while (node.childNodes.length > 0) node.removeChild(node.childNodes[0]);
    },

    // Make a node fill up the whole space of it's next reference parent node
    "fill": function(node)
    {
        node.className += " parentfiller";
    },

    "positionRelative": function(obj, relativeTo, left, top, invertx, inverty)
    {
        var node = relativeTo;
        while (node.offsetParent && node.offsetParent != document.documentElement)
        {
            top += node.offsetTop - node.scrollTop;
            left += node.offsetLeft - node.scrollLeft;
            node = node.offsetParent;
        }
        obj.style.position = "absolute";
        if (invertx) obj.style.right = (document.documentElement.clientWidth - left) + "px";
        else obj.style.left = left + "px";
        if (inverty) obj.style.bottom = (document.documentElement.clientHeight - top) + "px";
        else obj.style.top = top + "px";
        if (obj.parentNode != node) node.appendChild(obj);
    },

    "getAbsolutePos": function(obj)
    {
        var node = obj;
        var top = 0;
        var left = 0;
        while (node.offsetParent)
        {
            top += node.offsetTop - node.scrollTop;
            left += node.offsetLeft - node.scrollLeft;
            node = node.offsetParent;
        }
        return { "left": left, "top": top };
    }

};