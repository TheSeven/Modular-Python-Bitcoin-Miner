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

mod.workereditor = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "event", "layerbox", "uiconfig", "contextmenu"], callback);
    },

    // Shows the worker editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(nls("Worker editor"));
        if (!mod.uiconfig.data.workereditor) mod.uiconfig.data.workereditor = {};
        if (!mod.uiconfig.data.workereditor.height) mod.uiconfig.data.workereditor.height = "500px";
        if (!mod.uiconfig.data.workereditor.width) mod.uiconfig.data.workereditor.width = "700px";
        box.setOuterHeight(mod.uiconfig.data.workereditor.height);
        box.setOuterWidth(mod.uiconfig.data.workereditor.width);
        box.setResizable(true, true, function()
        {
            mod.uiconfig.data.workereditor.height = box.rootNode.style.height;
            mod.uiconfig.data.workereditor.width = box.rootNode.style.width;
            mod.uiconfig.update();
        });
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        var tr = document.createElement("tr");
        var td1 = document.createElement("td");
        var td2 = document.createElement("td");
        var workerListPanel = document.createElement("div");
        var workerEditPanel = document.createElement("div");
        box.contentNode.style.padding = "0px";
        table.style.width = "100%";
        table.style.height = "100%";
        td1.style.width = "300px";
        td1.style.borderRight = "1px dotted #000";
        workerListPanel.style.width = "100%";
        workerListPanel.style.height = "100%";
        workerListPanel.style.overflow = "auto";
        workerEditPanel.style.width = "100%";
        workerEditPanel.style.height = "100%";
        workerEditPanel.style.overflow = "auto";
        td1.appendChild(workerListPanel);
        td2.appendChild(workerEditPanel);
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
        table.appendChild(tbody);
        box.contentNode.appendChild(table);
        refresh();
        
        function refresh()
        {
            mod.dom.clean(workerListPanel);
            mod.dom.clean(workerEditPanel);
            showLoadingIndicator(workerListPanel);
            mod.csc.request("workereditor", "getworkerclasses", {}, function(data)
            {
                var classes = {};
                for (var i in data)
                    if (data.hasOwnProperty(i))
                        classes[data[i].id] = data[i];
                mod.csc.request("workereditor", "getworkers", {}, function(workers)
                {
                    var selectedWorker = false;
                    mod.dom.clean(workerListPanel);
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    table.style.width = "100%";
                    table.appendChild(tbody);
                    workerListPanel.appendChild(table);
                    for (var i in workers)
                        if (workers.hasOwnProperty(i))
                            createworkerEntry(tbody, workers[i]);
                    createNewworkerButton(tbody);
                    
                    function createworkerEntry(tbody, worker)
                    {
                        var tr = document.createElement("tr");
                        worker.td = document.createElement("td");
                        worker.namediv = document.createElement("div");
                        worker.classdiv = document.createElement("div");
                        worker.td.style.padding = "2px";
                        worker.td.style.borderBottom = "1px dotted #777";
                        worker.td.obj = worker;
                        worker.td.onmouseover = function(e)
                        {
                            if (this.obj != selectedWorker) this.style.background = "#ddf";
                        };
                        worker.td.onmouseout = function(e)
                        {
                            if (this.obj != selectedWorker) this.style.background = "inherit";
                        };
                        worker.td.onclick = function(e)
                        {
                            select(this.obj);
                        };
                        worker.td.customContextMenu = function(e)
                        {
                            var obj = this.obj;
                            var menu = new mod.contextmenu.ContextMenu();
                            menu.addEntry(nls("Restart worker"), function()
                            {
                                var box = mod.layerbox.LayerBox();
                                box.setTitle(nls("Restart worker"));
                                var text = nls("Do you really want to restart the worker") + " \"" + obj.name + "\"?";
                                var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                buttons[0].onclick = function()
                                {
                                    if (buttons[0].disabled) return;
                                    buttons[0].disabled = true;
                                    buttons[1].disabled = true;
                                    buttons[0].value = nls("Please wait...");
                                    mod.csc.request("workereditor", "restartworker", {"id": obj.id}, function(data)
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
                            menu.addEntry(nls("Delete worker"), function()
                            {
                                var box = mod.layerbox.LayerBox();
                                box.setTitle(nls("Delete worker"));
                                box.setStyle("error");
                                var text = nls("Do you really want to delete the worker") + " \"" + obj.name + "\"?";
                                var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                                buttons[0].onclick = function()
                                {
                                    if (buttons[0].disabled) return;
                                    buttons[0].disabled = true;
                                    buttons[1].disabled = true;
                                    buttons[0].value = nls("Please wait...");
                                    mod.csc.request("workereditor", "deleteworker", {"id": obj.id}, function(data)
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
                        worker.classdiv.style.color = "#777";
                        worker.classdiv.style.fontSize = "80%";
                        worker.namenode = document.createTextNode(worker.name);
                        worker.namediv.appendChild(worker.namenode);
                        worker.classdiv.appendChild(document.createTextNode(classes[worker["class"]].version));
                        worker.td.appendChild(worker.namediv);
                        worker.td.appendChild(worker.classdiv);
                        tr.appendChild(worker.td);
                        tbody.appendChild(tr);
                    }
                    
                    function createNewworkerButton(tbody)
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
                            newBox.setTitle(nls("Create new worker"));
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
                                mod.csc.request("workereditor", "createworker", {"class": classid}, function(data)
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
                        td.appendChild(document.createTextNode(nls("Create new worker")));
                        tr.appendChild(td);
                        tbody.appendChild(tr);
                    }
                        
                    function select(worker)
                    {
                        if (selectedWorker) selectedWorker.td.style.background = "inherit";
                        worker.td.style.background = "#bbf";
                        selectedWorker = worker;
                        mod.dom.clean(workerEditPanel);
                        delegate(workerEditPanel, "settingseditor",
                        {
                            "id": worker.id,
                            "savecallback": function(settings, callback)
                            {
                                worker.name = settings.name;
                                worker.namenode.nodeValue = settings.name;
                                callback();
                            },
                        });
                    }
                }, {"cache": "none"});
            }, {"cache": "none"});
        }
    }

};
