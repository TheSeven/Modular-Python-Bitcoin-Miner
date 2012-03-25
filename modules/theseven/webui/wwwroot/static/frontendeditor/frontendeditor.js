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

mod.frontendeditor = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "event", "layerbox", "uiconfig", "contextmenu"], callback);
    },

    // Shows the frontend editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(nls("Frontend editor"));
        if (!mod.uiconfig.data.frontendeditor) mod.uiconfig.data.frontendeditor = {};
        if (!mod.uiconfig.data.frontendeditor.height) mod.uiconfig.data.frontendeditor.height = "500px";
        if (!mod.uiconfig.data.frontendeditor.width) mod.uiconfig.data.frontendeditor.width = "700px";
        box.setOuterHeight(mod.uiconfig.data.frontendeditor.height);
        box.setOuterWidth(mod.uiconfig.data.frontendeditor.width);
        box.setResizable(true, true, function()
        {
            mod.uiconfig.data.frontendeditor.height = box.rootNode.style.height;
            mod.uiconfig.data.frontendeditor.width = box.rootNode.style.width;
            mod.uiconfig.update();
        });
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        var tr = document.createElement("tr");
        var td1 = document.createElement("td");
        var td2 = document.createElement("td");
        var frontendListPanel = document.createElement("div");
        var frontendEditPanel = document.createElement("div");
        box.contentNode.style.padding = "0px";
        table.style.width = "100%";
        table.style.height = "100%";
        td1.style.width = "300px";
        td1.style.borderRight = "1px dotted #000";
        frontendListPanel.style.width = "100%";
        frontendListPanel.style.height = "100%";
        frontendListPanel.style.overflow = "auto";
        frontendEditPanel.style.width = "100%";
        frontendEditPanel.style.height = "100%";
        frontendEditPanel.style.overflow = "auto";
        td1.appendChild(frontendListPanel);
        td2.appendChild(frontendEditPanel);
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
        table.appendChild(tbody);
        box.contentNode.appendChild(table);
        refresh();
        
        function refresh()
        {
            mod.dom.clean(frontendListPanel);
            mod.dom.clean(frontendEditPanel);
            showLoadingIndicator(frontendListPanel);
            mod.csc.request("frontendeditor", "getfrontendclasses", {}, function(data)
            {
                var classes = {};
                for (var i in data)
                    if (data.hasOwnProperty(i))
                        classes[data[i].id] = data[i];
                mod.csc.request("frontendeditor", "getfrontends", {}, function(frontends)
                {
                    var selectedFrontend = false;
                    mod.dom.clean(frontendListPanel);
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    table.style.width = "100%";
                    table.appendChild(tbody);
                    frontendListPanel.appendChild(table);
                    for (var i in frontends)
                        if (frontends.hasOwnProperty(i))
                            createFrontendEntry(tbody, frontends[i]);
                    createNewFrontendButton(tbody);
                    
                    function createFrontendEntry(tbody, frontend)
                    {
                        var tr = document.createElement("tr");
                        frontend.td = document.createElement("td");
                        frontend.namediv = document.createElement("div");
                        frontend.classdiv = document.createElement("div");
                        frontend.td.style.padding = "2px";
                        frontend.td.style.borderBottom = "1px dotted #777";
                        frontend.td.obj = frontend;
                        frontend.td.onmouseover = function(e)
                        {
                            if (this.obj != selectedFrontend) this.style.background = "#ddf";
                        };
                        frontend.td.onmouseout = function(e)
                        {
                            if (this.obj != selectedFrontend) this.style.background = "inherit";
                        };
                        frontend.td.onclick = function(e)
                        {
                            select(this.obj);
                        };
                        frontend.td.customContextMenu = function(e)
                        {
                            var obj = this.obj;
                            var menu = new mod.contextmenu.ContextMenu();
                            menu.addEntry(nls("Restart frontend"), function()
                            {
                                var box = mod.layerbox.LayerBox();
                                box.setTitle(nls("Restart frontend"));
                                var text = nls("Do you really want to restart the frontend") + " \"" + obj.name + "\"?";
                                var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                buttons[0].onclick = function()
                                {
                                    if (buttons[0].disabled) return;
                                    buttons[0].disabled = true;
                                    buttons[1].disabled = true;
                                    buttons[0].value = nls("Please wait...");
                                    mod.csc.request("frontendeditor", "restartfrontend", {"id": obj.id}, function(data)
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
                            menu.addEntry(nls("Delete frontend"), function()
                            {
                                var box = mod.layerbox.LayerBox();
                                box.setTitle(nls("Delete frontend"));
                                box.setStyle("error");
                                var text = nls("Do you really want to delete the frontend") + " \"" + obj.name + "\"?";
                                var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                buttons[0].onclick = function()
                                {
                                    if (buttons[0].disabled) return;
                                    buttons[0].disabled = true;
                                    buttons[1].disabled = true;
                                    buttons[0].value = nls("Please wait...");
                                    mod.csc.request("frontendeditor", "deletefrontend", {"id": obj.id}, function(data)
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
                        frontend.classdiv.style.color = "#777";
                        frontend.classdiv.style.fontSize = "80%";
                        frontend.namenode = document.createTextNode(frontend.name);
                        frontend.namediv.appendChild(frontend.namenode);
                        frontend.classdiv.appendChild(document.createTextNode(classes[frontend["class"]].version));
                        frontend.td.appendChild(frontend.namediv);
                        frontend.td.appendChild(frontend.classdiv);
                        tr.appendChild(frontend.td);
                        tbody.appendChild(tr);
                    }
                    
                    function createNewFrontendButton(tbody)
                    {
                        var tr = document.createElement("tr");
                        td = document.createElement("td");
                        td.style.padding = "2px";
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
                            newBox.setTitle(nls("Create new frontend"));
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
                                mod.csc.request("frontendeditor", "createfrontend", {"class": classid}, function(data)
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
                        td.appendChild(document.createTextNode(nls("Create new frontend")));
                        tr.appendChild(td);
                        tbody.appendChild(tr);
                    }
                        
                    function select(frontend)
                    {
                        if (selectedFrontend) selectedFrontend.td.style.background = "inherit";
                        frontend.td.style.background = "#bbf";
                        selectedFrontend = frontend;
                        mod.dom.clean(frontendEditPanel);
                        delegate(frontendEditPanel, "settingseditor",
                        {
                            "id": frontend.id,
                            "savecallback": function(settings, callback)
                            {
                                frontend.name = settings.name;
                                frontend.namenode.nodeValue = settings.name;
                                callback();
                            },
                        });
                    }
                }, {"cache": "none"});
            }, {"cache": "none"});
        }
    }

};
