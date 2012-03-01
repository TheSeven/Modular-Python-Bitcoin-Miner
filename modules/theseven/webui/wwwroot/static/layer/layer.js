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

mod.layer = {

    "zindex": 10000,

    // Make something be a layer
    "layerify": function(anchor, handle, win)
    {
        if (!win) win = window;
        var sizemaster = document.getElementById("container");
        if (window != win) sizemaster = win;

        anchor.style.zIndex = mod.layer.zindex++;

        // Moves the layer to the specified position, clipped to fit into the viewport
        anchor.moveTo = function(x, y)
        {
            if (x > sizemaster.offsetWidth - anchor.offsetWidth) x = sizemaster.offsetWidth - anchor.offsetWidth;
            if (y > sizemaster.offsetHeight - anchor.offsetHeight) y = sizemaster.offsetHeight - anchor.offsetHeight;
            if (x < 0) x = 0;
            if (y < 0) y = 0;
            anchor.style.left = x + "px";
            anchor.style.top = y + "px";
        };

        // Moves the layer by a specified offset
        anchor.moveBy = function(x, y)
        {
            anchor.moveTo(anchor.offsetLeft + x, anchor.offsetTop + y);
        };

        anchor.onmousedown = function(e)
        {
            anchor.style.zIndex = mod.layer.zindex++;
        };

        // We need to hook these events natively,
        // firing up event_trigger for every mouse move would kill most browsers
        handle.onmousedown = function(e)
        {
            anchor.style.zIndex = mod.layer.zindex++;

            // Backup the old event handlers
            var oldMouseUp = win.document.documentElement.onmouseup;
            var oldMouseMove = win.document.documentElement.onmousemove;
            function getMousePos(e)
            {
                if (!e) e = win.event;
                return { "x": e.clientX, "y": e.clientY };
            }
            var pos = getMousePos(e);
            function updatePos(e)
            {
                // Determine target position, trim it to the window or content dimensions and apply it
                var newpos = getMousePos(e);
                anchor.moveBy(newpos.x - pos.x, newpos.y - pos.y);
                pos = newpos;
            }
            win.document.documentElement.onmousemove = updatePos;
            win.document.documentElement.onmouseup = function(e)
            {
                // Update the position a final time
                updatePos(e);
                // Restore the old event handlers
                win.document.documentElement.onmousemove = oldMouseMove;
                win.document.documentElement.onmouseup = oldMouseUp;
            };
            return killEvent(e);
        };
    }

};