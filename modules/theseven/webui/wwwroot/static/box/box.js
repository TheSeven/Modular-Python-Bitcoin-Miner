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

mod.box = {

    // The JS class representing a box
    "Box": function(win)
    {
        if (!win) win = window;
        var obj = this;

        // Generate box UID
        this.uid = "";
        var chars = "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
        for (var i = 0; i < 16; i++) this.uid += chars.substr(0 | Math.random() * chars.length, 1);
        var inputindex = 0;

        this.events = [];

        // Exported nodes
        this.rootNode = win.document.createElement("table");
        this.titleNode = win.document.createElement("td");
        this.titleTextNode = win.document.createTextNode("");
        this.contentNode = win.document.createElement("td");

        // Buttons
        var closebutton = win.document.createElement("div");
        closebutton.style.display = "none";

        // Border nodes
        var td11 = win.document.createElement("td");
        var td13 = win.document.createElement("td");
        var td21 = win.document.createElement("td");
        var td23 = win.document.createElement("td");
        var td31 = win.document.createElement("td");
        var td32 = win.document.createElement("td");
        var td33 = win.document.createElement("td");

        // Glue nodes
        var tbody = win.document.createElement("tbody");
        var tr1 = win.document.createElement("tr");
        var tr2 = win.document.createElement("tr");
        var tr3 = win.document.createElement("tr");

        // Set the CSS classes
        this.rootNode.className = "box";
        td11.className = "box_topleft";
        this.titleNode.className = "box_title";
        td13.className = "box_topright";
        td21.className = "box_left";
        this.contentNode.className = "box_content";
        td23.className = "box_right";
        td31.className = "box_bottomleft";
        td32.className = "box_bottom";
        td33.className = "box_bottomright";
        closebutton.className = "box_close";

        // Put it all together
        this.titleNode.appendChild(closebutton);
        this.titleNode.appendChild(this.titleTextNode);
        tr1.appendChild(td11);
        tr1.appendChild(this.titleNode);
        tr1.appendChild(td13);
        tr2.appendChild(td21);
        tr2.appendChild(this.contentNode);
        tr2.appendChild(td23);
        tr3.appendChild(td31);
        tr3.appendChild(td32);
        tr3.appendChild(td33);
        tbody.appendChild(tr1);
        tbody.appendChild(tr2);
        tbody.appendChild(tr3);
        this.rootNode.appendChild(tbody);

        // Sets the title of a box
        this.setTitle = function(title)
        {
            obj.titleTextNode.nodeValue = title;
        };

        // Sets the style of a box
        this.setStyle = function(style)
        {
            obj.rootNode.className = obj.rootNode.className.replace(/[^ ]*box/, style + "box");
        };

        // If a callback was given, show a close button linked to the callback, else remove the button
        this.setCloseable = function(callback)
        {
            closebutton.onclick = callback;
            if (callback) closebutton.style.display = "block";
            else closebutton.style.display = "none";
        };

        // Deletes the outer and sets the inner width of the box
        this.setInnerWidth = function(width)
        {
            obj.rootNode.style.width = "auto";
            obj.contentNode.style.width = width;
        };

        // Deletes the inner and sets the outer width of the box
        this.setOuterWidth = function(width)
        {
            obj.contentNode.style.width = "auto";
            obj.rootNode.style.width = width;
        };

        // Deletes the outer and sets the inner height of the box
        this.setInnerHeight = function(height)
        {
            obj.rootNode.style.height = "auto";
            obj.contentNode.style.height = height;
        };

        // Deletes the inner and sets the outer height of the box
        this.setOuterHeight = function(height)
        {
            obj.contentNode.style.height = "auto";
            obj.rootNode.style.height = height;
        };

        // Detach the box from it's parent, mainly intended as a shorthand argument for setCloseable
        this.destroy = function()
        {
            for (var i in obj.events)
            {
                if (obj.events.hasOwnProperty(i))
                    obj.events[i].unhook();
            }
            if (obj.rootNode.parentNode) obj.rootNode.parentNode.removeChild(obj.rootNode);
        };

        this.setImage = function(url)
        {
            if (!obj.image)
            {
                var table = document.createElement("table");
                var tbody = document.createElement("tbody");
                var tr = document.createElement("tr");
                var td1 = document.createElement("td");
                td1.style.verticalAlign = "middle";
                obj.image = document.createElement("img");
                td1.appendChild(obj.image);
                tr.appendChild(td1);
                obj.rightPart = document.createElement("td");
                obj.rightPart.style.textAlign = "center";
                obj.rightPart.style.verticalAlign = "middle";
                while (obj.contentNode.firstChild)
                {
                    var node = obj.contentNode.firstChild;
                    obj.contentNode.removeChild(node);
                    obj.rightPart.appendChild(node);
                }
                tr.appendChild(obj.rightPart);
                tbody.appendChild(tr);
                table.appendChild(tbody);
                obj.contentNode.appendChild(table);
            }
            obj.image.src = url;
        };
        
        this.removeForm = function()
        {
            if (obj.form && obj.form.parentNode)
                obj.form.parentNode.removeChild(obj.form);
            obj.form = null;
            obj.formbody = null;
        };
        
        this.createForm = function()
        {
            if (!obj.form || !obj.form.parentNode || !obj.formbody.parentNode)
            {
                obj.form = document.createElement("form");
                if (obj.rightPart && obj.rightPart.parentNode) obj.rightPart.appendChild(obj.form);
                else obj.contentNode.appendChild(obj.form);
                var table = document.createElement("table");
                table.style.width = "100%";
                obj.form.appendChild(table);
                obj.formbody = document.createElement("tbody");
                table.appendChild(obj.formbody);
            }
        };

        this.addInput = function(label, input, params)
        {
            if (!params) params = [];
            obj.createForm();
            var tr;
            if (params.continuerow)
            {
                tr = obj.formbody.lastChild;
            }
            else
            {
                tr = document.createElement("tr");
                obj.formbody.appendChild(tr);
            }
            if (!params.noinput)
            {
                if (typeof input != "object")
                {
                    var type = "text";
                    if (input) type = input;
                    input = document.createElement("input");
                    input.type = type;
                }
                try
                {
                    input.id = "box_" + obj.uid + "_input" + (inputindex++);
                }
                catch (e)
                {
                }
            }
            if (!params.nolabel)
            {
                if (label && (!label.nodeName || label.nodeName.toUpperCase() != "LABEL") && !params.nolabelwrapping)
                {
                    var node;
                    if (typeof label == "string") node = document.createTextNode(label);
                    else node = label;
                    label = document.createElement("label");
                    label.appendChild(node);
                }
                if (label && input && label.nodeName.toUpperCase() == "LABEL") label.htmlFor = input.id;
                var th = document.createElement("th");
                th.className = "box_form_label";
                if (params.labelrowspan) th.rowSpan = params.labelrowspan;
                if (params.labelcolspan) th.colSpan = params.labelcolspan;
                if (label)
                {
                    th.appendChild(label);
                    try
                    {
                        if (input) input.label = label;
                    }
                    catch (e)
                    {
                    }
                }
                tr.appendChild(th);
            }
            if (!params.noinput)
            {
                var td = document.createElement("td");
                if (params.inputrowspan) th.rowSpan = params.inputrowspan;
                if (params.inputcolspan) th.colSpan = params.inputcolspan;
                if (!params.dontfill && input.style && (!input.type || (input.type.toUpperCase() != "CHECKBOX" && input.type.toUpperCase() != "RADIO")))
                {
                    input.style.boxSizing = "border-box";
                    input.style.MozBoxSizing = "border-box";
                    input.style.MsBoxSizing = "border-box";
                    input.style.width = "100%";
                }
                td.appendChild(input);
                tr.appendChild(td);
            }
            return input ? input : label;
        };

        this.multipleChoice = function(question, options, vertical, stretch)
        {
            var table = document.createElement("table");
            table.style.width = "100%";
            var tbody = document.createElement("tbody");
            var tr = document.createElement("tr");
            var td = document.createElement("td");
            td.style.textAlign = "center";
            td.style.verticalAlign = "middle";
            td.style.width = "100%";
            if (typeof question == "string") question = document.createTextNode(question);
            td.appendChild(question);
            tr.appendChild(td);
            tbody.appendChild(tr);
            table.appendChild(tbody);
            if (obj.rightPart) obj.rightPart.appendChild(table);
            else obj.contentNode.appendChild(table);
            if (!vertical)
            {
                td.colSpan = options.length;
                tr = document.createElement("tr");
                tbody.appendChild(tr);
            }
            for (var i in options)
            {
                if (options.hasOwnProperty(i))
                {
                    if (typeof options[i] == "string")
                    {
                        var text = options[i];
                        options[i] = document.createElement("input");
                        options[i].type = "button";
                        options[i].value = text;
                    }
                    if (stretch) options[i].style.width = "100%";
                    if (vertical)
                    {
                        tr = document.createElement("tr");
                        tbody.appendChild(tr);
                    }
                    td = document.createElement("td");
                    td.style.textAlign = "center";
                    td.style.verticalAlign = "middle";
                    td.appendChild(options[i]);
                    tr.appendChild(td);
                }
            }
            return options;
        };

        this.setResizable = function(horizontally, vertically, changecallback, finalcallback)
        {
            function mousedown(e, h, v)
            {
                // Backup the old event handlers
                var oldMouseUp = win.document.documentElement.onmouseup;
                var oldMouseMove = win.document.documentElement.onmousemove;
                function getMousePos(e)
                {
                    if (!e) e = win.event;
                    return {"x": e.clientX, "y": e.clientY};
                }
                var pos = getMousePos(e);
                var size = {"x": obj.rootNode.offsetWidth, "y": obj.rootNode.offsetHeight};
                function updateSize(e)
                {
                    var newpos = getMousePos(e);
                    if (h) obj.rootNode.style.width = (newpos.x - pos.x + size.x) + "px";
                    if (v) obj.rootNode.style.height = (newpos.y - pos.y + size.y) + "px";
                    if (changecallback) changecallback();
                }
                win.document.documentElement.onmousemove = updateSize;
                win.document.documentElement.onmouseup = function(e)
                {
                    // Update the size a final time
                    updateSize(e);
                    if (finalcallback) finalcallback();
                    // Restore the old event handlers
                    win.document.documentElement.onmousemove = oldMouseMove;
                    win.document.documentElement.onmouseup = oldMouseUp;
                };
                return killEvent(e);
            }
            
            // We need to hook these events natively,
            // firing up event_trigger for every mouse move would kill most browsers
            if (horizontally)
            {
                td23.style.cursor = "e-resize";
                td23.onmousedown = function(e)
                {
                    mousedown(e, true, false);
                };
            }
            else
            {
                td23.style.cursor = "inherit";
                td23.onmousedown = truefunc;
            }
            if (vertically)
            {
                td32.style.cursor = "s-resize";
                td32.onmousedown = function(e)
                {
                    mousedown(e, false, true);
                };
            }
            else
            {
                td32.style.cursor = "inherit";
                td32.onmousedown = truefunc;
            }
            if (horizontally && vertically)
            {
                td33.style.cursor = "se-resize";
                td33.onmousedown = function(e)
                {
                    mousedown(e, true, true);
                };
            }
            else
            {
                td33.style.cursor = "inherit";
                td33.onmousedown = truefunc;
            }
        };
    }

};