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

mod.event = {

    "hooks": {},

    // Hook a callback to a specified event
    "hook": function(event, callback)
    {
        if (!mod.event.hooks[event]) mod.event.hooks[event] = new Array();
        var hook = mod.event.hooks[event].push(callback) - 1;
        return { "unhook": function() { if (mod.event.hooks[event]) delete mod.event.hooks[event][hook]; } };
    },

    // Trigger all hooks connected to a specified event
    "trigger": function(event, param)
    {
        if (!mod.event.hooks[event]) return;
        var hooks = mod.event.hooks[event].slice().reverse();
        for (var hook in hooks)
            if (hooks.hasOwnProperty(hook) && hooks[hook](param) == false) return false;
    },

    "catchKey": function(keyCode, callback, allowBubble)
    {
        if (!allowBubble) allowBubble = false;
        return mod.event.hook("windowkeydown", function(e)
        {
            if (!e) e = window.event;
            if (e.keyCode == keyCode)
            {
                callback(e);
                return allowBubble;
            }
        });
    }

};

// Hook some system events
window.onresize = function(e)
{
    mod.event.trigger("windowresized", e);
    if (/MSIE [4-7]/.test(navigator.userAgent))
    {
        setTimeout(function()
        {
            mod.event.trigger("windowresized", e);
        }, 1000);
    }
};
window.onkeydown = function(e)
{
    return mod.event.trigger("windowkeydown", e) == false ? killEvent(e) : true;
};
window.onkeypress = function(e)
{
    return mod.event.trigger("windowkeypress", e) == false ? killEvent(e) : true;
};
window.onkeyup = function(e)
{
    return mod.event.trigger("windowkeyup", e) == false ? killEvent(e) : true;
};
window.onmousedown = function(e)
{
    return mod.event.trigger("windowmousedown", e) == false ? killEvent(e) : true;
};
window.onclick = function(e)
{
    return mod.event.trigger("windowclick", e) == false ? killEvent(e) : true;
};
window.onmouseup = function(e)
{
    return mod.event.trigger("windowmouseup", e) == false ? killEvent(e) : true;
};