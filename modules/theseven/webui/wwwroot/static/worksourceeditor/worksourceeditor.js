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

mod.worksourceeditor = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "event", "layerbox", "uiconfig", "contextmenu"], callback);
    },

    // Shows the worksource editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(nls("Work source editor"));
        if (!mod.uiconfig.data.worksourceeditor) mod.uiconfig.data.worksourceeditor = {};
        if (!mod.uiconfig.data.worksourceeditor.height) mod.uiconfig.data.worksourceeditor.height = "500px";
        if (!mod.uiconfig.data.worksourceeditor.width) mod.uiconfig.data.worksourceeditor.width = "700px";
        box.setOuterHeight(mod.uiconfig.data.worksourceeditor.height);
        box.setOuterWidth(mod.uiconfig.data.worksourceeditor.width);
        box.setResizable(true, true, function()
        {
            mod.uiconfig.data.worksourceeditor.height = box.rootNode.style.height;
            mod.uiconfig.data.worksourceeditor.width = box.rootNode.style.width;
            mod.uiconfig.update();
        });
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        var tr = document.createElement("tr");
        var td1 = document.createElement("td");
        var td2 = document.createElement("td");
        var worksourceListPanel = document.createElement("div");
        var worksourceEditPanel = document.createElement("div");
        box.contentNode.style.padding = "0px";
        table.style.width = "100%";
        table.style.height = "100%";
        td1.style.width = "300px";
        td1.style.borderRight = "1px dotted #000";
        worksourceListPanel.style.width = "100%";
        worksourceListPanel.style.height = "100%";
        worksourceListPanel.style.overflow = "auto";
        worksourceEditPanel.style.width = "100%";
        worksourceEditPanel.style.height = "100%";
        worksourceEditPanel.style.overflow = "auto";
        td1.appendChild(worksourceListPanel);
        td2.appendChild(worksourceEditPanel);
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
        table.appendChild(tbody);
        box.contentNode.appendChild(table);
        refresh();
        
        function refresh()
        {
            mod.dom.clean(worksourceListPanel);
            mod.dom.clean(worksourceEditPanel);
            showLoadingIndicator(worksourceListPanel);
            mod.csc.request("worksourceeditor", "getworksourceclasses", {}, function(data)
            {
                var classes = {};
                for (var i in data)
                    if (data.hasOwnProperty(i))
                        classes[data[i].id] = data[i];
                mod.csc.request("worksourceeditor", "getworksources", {}, function(data)
                {
                    var selectedWorksource = false;
                    var mouseOverWorksource = false;
                    mod.dom.clean(worksourceListPanel);
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    table.style.width = "100%";
                    table.appendChild(tbody);
                    worksourceListPanel.appendChild(table);
                    createWorksourceEntry(tbody, data, 0);
                    
                    function createWorksourceEntry(tbody, worksource, level)
                    {
                        var tr = document.createElement("tr");
                        worksource.td = document.createElement("td");
                        worksource.namediv = document.createElement("div");
                        worksource.classdiv = document.createElement("div");
                        tr.style.cursor = "inherit";
                        worksource.td.style.cursor = "inherit";
                        worksource.namediv.style.cursor = "inherit";
                        worksource.classdiv.style.cursor = "inherit";
                        worksource.td.style.padding = "2px";
                        worksource.td.style.paddingLeft = (2 + 20 * level) + "px";
                        if (level) worksource.td.style.borderTop = "1px dotted #777";
                        worksource.td.obj = worksource;
                        worksource.td.onmouseover = function(e)
                        {
                            mouseOverWorksource = this.obj;
                            if (this.obj != selectedWorksource) this.style.background = "#ddf";
                        };
                        worksource.td.onmouseout = function(e)
                        {
                            mouseOverWorksource = false;
                            if (this.obj != selectedWorksource) this.style.background = "inherit";
                        };
                        worksource.td.onclick = function(e)
                        {
                            select(this.obj);
                        };
                        if (level)
                        {
                            worksource.td.onmousedown = function(e)
                            {
                                var obj = this.obj;
                                tbody.style.cursor = "no-drop";
                                var oldMouseUp = document.documentElement.onmouseup;
                                var oldMouseMove = document.documentElement.onmousemove;
                                document.documentElement.onmousemove = function(e)
                                {
                                    var cursor = "move";
                                    if (!mouseOverWorksource || !mouseOverWorksource.is_group) cursor = "no-drop";
                                    else
                                    {
                                        var w = mouseOverWorksource;
                                        while (w)
                                        {
                                            if (w == obj)
                                            {
                                                cursor = "no-drop";
                                                break;
                                            }
                                            w = w.parent;
                                        }
                                    }
                                    tbody.style.cursor = cursor;
                                };
                                document.documentElement.onmouseup = function(e)
                                {
                                    var parent = mouseOverWorksource;
                                    tbody.style.cursor = "inherit";
                                    document.documentElement.onmousemove = oldMouseMove;
                                    document.documentElement.onmouseup = oldMouseUp;
                                    if (!parent || !parent.is_group) return;
                                    var w = parent;
                                    while (w)
                                    {
                                        if (w == obj) return;
                                        w = w.parent;
                                    }
                                    var box = mod.layerbox.LayerBox();
                                    box.setTitle(nls("Move work source"));
                                    var text = nls("Do you really want to move the work source") + " \"" + obj.name + "\" "
                                             + nls("into the work source") + " \"" + parent.name + "\"?";
                                    var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                    buttons[0].onclick = function()
                                    {
                                        if (buttons[0].disabled) return;
                                        buttons[0].disabled = true;
                                        buttons[1].disabled = true;
                                        buttons[0].value = nls("Please wait...");
                                        mod.csc.request("worksourceeditor", "moveworksource", {"id": obj.id, "parent": parent.id}, function(data)
                                        {
                                            box.destroy();
                                            if (data.error) return error(data.error);
                                            refresh();
                                        }, {"cache": "none"});
                                    };
                                    buttons[1].onclick = box.destroy;
                                    box.events.push(mod.event.catchKey(13, buttons[0].onclick));
                                    box.events.push(mod.event.catchKey(27, box.destroy));
                                };
                                return killEvent(e);
                            };
                            worksource.td.customContextMenu = function(e)
                            {
                                var obj = this.obj;
                                var menu = new mod.contextmenu.ContextMenu();
                                if (!obj.is_group)
                                {
                                    menu.addEntry(nls("Assign to blockchain"), function()
                                    {
                                        var box = mod.layerbox.LayerBox();
                                        box.setTitle(nls("Assign to blockchain"));
                                        showLoadingIndicator(box.contentNode).style.position = "static";
                                        mod.csc.request("worksourceeditor", "getblockchains", {}, function(data)
                                        {
                                            mod.dom.clean(box.contentNode);
                                            var blockchainField = box.addInput("Blockchain:", document.createElement("select"));
                                            data.unshift({"id": 0, "name": nls("None")});
                                            for (var i in data)
                                                if (data.hasOwnProperty(i))
                                                {
                                                    var option = document.createElement("option");
                                                    option.value = data[i].id;
                                                    if (data[i].id == obj.blockchain) option.selected = "selected";
                                                    option.appendChild(document.createTextNode(data[i].name));
                                                    blockchainField.appendChild(option);
                                                }
                                            var submitButton = box.addInput(null, "submit");
                                            submitButton.value = nls("Save");
                                            blockchainField.focus();
                                            box.events.push(mod.event.catchKey(27, box.destroy));
                                            box.form.onsubmit = function(e)
                                            {
                                                if (submitButton.disabled) return killEvent(e);
                                                submitButton.disabled = true;
                                                submitButton.value = nls("Please wait...");
                                                var blockchainid = parseInt(blockchainField.options[blockchainField.selectedIndex].value);
                                                mod.csc.request("worksourceeditor", "setblockchain", {"id": obj.id, "blockchain": blockchainid}, function(data)
                                                {
                                                    if (data.error)
                                                    {
                                                        error(data.error);
                                                        submitButton.value = nls("Save");
                                                        submitButton.disabled = false;
                                                    }
                                                    else
                                                    {
                                                        box.destroy();
                                                        refresh();
                                                    }
                                                }, {"cache": "none"});
                                                return killEvent(e);
                                            };
                                        }, {"cache": "none"});
                                        menu.hide();
                                    });
                                    menu.addBarrier();
                                }
                                menu.addEntry(nls("Restart work source"), function()
                                {
                                    var box = mod.layerbox.LayerBox();
                                    box.setTitle(nls("Restart work source"));
                                    var text = nls("Do you really want to restart the work source") + " \"" + obj.name + "\""
                                             + (worksource.children ? nls(" including its children") : "") + "?";
                                    var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                    buttons[0].onclick = function()
                                    {
                                        if (buttons[0].disabled) return;
                                        buttons[0].disabled = true;
                                        buttons[1].disabled = true;
                                        buttons[0].value = nls("Please wait...");
                                        mod.csc.request("worksourceeditor", "restartworksource", {"id": obj.id}, function(data)
                                        {
                                            box.destroy();
                                            if (data.error) return error(data.error);
                                            refresh();
                                        }, {"cache": "none"});
                                    };
                                    buttons[1].onclick = box.destroy;
                                    box.events.push(mod.event.catchKey(13, buttons[0].onclick));
                                    box.events.push(mod.event.catchKey(27, box.destroy));
                                    menu.hide();
                                });
                                menu.addEntry(nls("Delete work source"), function()
                                {
                                    var box = mod.layerbox.LayerBox();
                                    box.setTitle(nls("Delete work source"));
                                    box.setStyle("error");
                                    var text = nls("Do you really want to delete the work source") + " \"" + obj.name + "\""
                                             + (worksource.children ? nls(" including its children") : "") + "?";
                                    var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                    buttons[0].onclick = function()
                                    {
                                        if (buttons[0].disabled) return;
                                        buttons[0].disabled = true;
                                        buttons[1].disabled = true;
                                        buttons[0].value = nls("Please wait...");
                                        mod.csc.request("worksourceeditor", "deleteworksource", {"id": obj.id}, function(data)
                                        {
                                            box.destroy();
                                            if (data.error) return error(data.error);
                                            refresh();
                                        }, {"cache": "none"});
                                    };
                                    buttons[1].onclick = box.destroy;
                                    box.events.push(mod.event.catchKey(13, buttons[0].onclick));
                                    box.events.push(mod.event.catchKey(27, box.destroy));
                                    menu.hide();
                                });
                                menu.show();
                                return killEvent(e);
                            };
                        }
                        worksource.classdiv.style.color = "#777";
                        worksource.classdiv.style.fontSize = "80%";
                        worksource.namenode = document.createTextNode(worksource.name);
                        worksource.namediv.appendChild(worksource.namenode);
                        worksource.classdiv.appendChild(document.createTextNode(classes[worksource["class"]].version));
                        worksource.td.appendChild(worksource.namediv);
                        worksource.td.appendChild(worksource.classdiv);
                        tr.appendChild(worksource.td);
                        tbody.appendChild(tr);
                        if (worksource.is_group)
                        {
                            for (var i in worksource.children)
                                if (worksource.children.hasOwnProperty(i))
                                {
                                    worksource.children[i].parent = worksource;
                                    createWorksourceEntry(tbody, worksource.children[i], level + 1);
                                }
                            createNewWorksourceButton(tbody, worksource, level + 1);
                        }
                    }
                    
                    function createNewWorksourceButton(tbody, parent, level)
                    {
                        var tr = document.createElement("tr");
                        td = document.createElement("td");
                        tr.style.cursor = "inherit";
                        td.style.cursor = "inherit";
                        td.style.padding = "2px";
                        td.style.paddingLeft = (2 + 20 * level) + "px";
                        td.style.borderTop = "1px dotted #777";
                        td.onmouseover = function(e)
                        {
                            this.style.background = "#ddf";
                        };
                        td.onmouseout = function(e)
                        {
                            this.style.background = "inherit";
                        };
                        td.onclick = function(e)
                        {
                            var newBox = mod.layerbox.LayerBox();
                            newBox.setTitle(nls("Create new work source"));
                            var classField = newBox.addInput("Class:", document.createElement("select"));
                            for (var i in classes)
                                if (classes.hasOwnProperty(i))
                                {
                                    var option = document.createElement("option");
                                    option.value = classes[i].id;
                                    option.appendChild(document.createTextNode(classes[i].version));
                                    classField.appendChild(option);
                                }
                            var submitButton = newBox.addInput(null, "submit");
                            submitButton.value = nls("Create");
                            classField.focus();
                            newBox.events.push(mod.event.catchKey(27, newBox.destroy));
                            newBox.form.onsubmit = function(e)
                            {
                                if (submitButton.disabled) return killEvent(e);
                                submitButton.disabled = true;
                                submitButton.value = nls("Please wait...");
                                var classid = parseInt(classField.options[classField.selectedIndex].value);
                                mod.csc.request("worksourceeditor", "createworksource", {"parent": parent.id, "class": classid}, function(data)
                                {
                                    if (data.error)
                                    {
                                        error(data.error);
                                        submitButton.value = nls("Create");
                                        submitButton.disabled = false;
                                    }
                                    else
                                    {
                                        newBox.destroy();
                                        refresh();
                                    }
                                }, {"cache": "none"});
                                return killEvent(e);
                            };
                        };
                        td.appendChild(document.createTextNode(nls("Create new work source")));
                        tr.appendChild(td);
                        tbody.appendChild(tr);
                    }
                        
                    function select(worksource)
                    {
                        if (selectedWorksource) selectedWorksource.td.style.background = "inherit";
                        worksource.td.style.background = "#bbf";
                        selectedWorksource = worksource;
                        mod.dom.clean(worksourceEditPanel);
                        delegate(worksourceEditPanel, "settingseditor",
                        {
                            "id": worksource.id,
                            "savecallback": function(settings, callback)
                            {
                                worksource.name = settings.name;
                                worksource.namenode.nodeValue = settings.name;
                                callback();
                            },
                        });
                    }
                }, {"cache": "none"});
            }, {"cache": "none"});
        }
    }

};
