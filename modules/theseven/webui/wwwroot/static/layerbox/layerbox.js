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

mod.layerbox = {

    "params": {"xmin": 10, "xmax": 50, "xstep": 10,
               "ymin": 10, "ymax": 60, "ystep": 10},

    // Module initialization: Check that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["box", "layer"], callback);
    },

    // Allow themes to configure the opening position of layer boxes
    "setParams": function(params)
    {
        mod.layerbox.params = params;
    },

    // The JS class representing a layer box
    "LayerBox": function(anchor, win)
    {
        if (!win) win = window;
        var box = new mod.box.Box(win);
        // Upper case Box here to not confuse it with a box style name
        box.rootNode.className += " LayerBox";
        box.rootNode.style.position = "absolute";
        mod.layer.layerify(box.rootNode, box.titleNode, win);
        if (!anchor) anchor = document.getElementsByTagName("body")[0];
        box.setCloseable(box.destroy);
        anchor.appendChild(box.rootNode);
        box.moveTo = box.rootNode.moveTo;
        box.moveBy = box.rootNode.moveBy;
        if (!mod.layerbox.params.xcurrent || mod.layerbox.params.xcurrent > mod.layerbox.params.xmax)
            mod.layerbox.params.xcurrent = mod.layerbox.params.xmin;
        if (!mod.layerbox.params.ycurrent || mod.layerbox.params.ycurrent > mod.layerbox.params.ymax)
            mod.layerbox.params.ycurrent = mod.layerbox.params.ymin;
        box.moveTo(mod.layerbox.params.xcurrent, mod.layerbox.params.ycurrent);
        mod.layerbox.params.xcurrent += mod.layerbox.params.xstep;
        mod.layerbox.params.ycurrent += mod.layerbox.params.ystep;
        return box;
    }

};