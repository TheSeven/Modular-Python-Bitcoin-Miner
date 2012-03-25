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

mod.blockchaineditor = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "event", "layerbox", "uiconfig", "contextmenu"], callback);
    },

    // Shows the blockchain editor window
    "LayerUI": function(config)
    {
        var box = mod.layerbox.LayerBox();
        box.setTitle(nls("Blockchain editor"));
        if (!mod.uiconfig.data.blockchaineditor) mod.uiconfig.data.blockchaineditor = {};
        if (!mod.uiconfig.data.blockchaineditor.height) mod.uiconfig.data.blockchaineditor.height = "500px";
        if (!mod.uiconfig.data.blockchaineditor.width) mod.uiconfig.data.blockchaineditor.width = "700px";
        box.setOuterHeight(mod.uiconfig.data.blockchaineditor.height);
        box.setOuterWidth(mod.uiconfig.data.blockchaineditor.width);
        box.setResizable(true, true, function()
        {
            mod.uiconfig.data.blockchaineditor.height = box.rootNode.style.height;
            mod.uiconfig.data.blockchaineditor.width = box.rootNode.style.width;
            mod.uiconfig.update();
        });
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        var tr = document.createElement("tr");
        var td1 = document.createElement("td");
        var td2 = document.createElement("td");
        var blockchainListPanel = document.createElement("div");
        var blockchainEditPanel = document.createElement("div");
        box.contentNode.style.padding = "0px";
        table.style.width = "100%";
        table.style.height = "100%";
        td1.style.width = "300px";
        td1.style.borderRight = "1px dotted #000";
        blockchainListPanel.style.width = "100%";
        blockchainListPanel.style.height = "100%";
        blockchainListPanel.style.overflow = "auto";
        blockchainEditPanel.style.width = "100%";
        blockchainEditPanel.style.height = "100%";
        blockchainEditPanel.style.overflow = "auto";
        td1.appendChild(blockchainListPanel);
        td2.appendChild(blockchainEditPanel);
        tr.appendChild(td1);
        tr.appendChild(td2);
        tbody.appendChild(tr);
        table.appendChild(tbody);
        box.contentNode.appendChild(table);
        refresh();
        
        function refresh()
        {
            mod.dom.clean(blockchainListPanel);
            mod.dom.clean(blockchainEditPanel);
            showLoadingIndicator(blockchainListPanel);
            mod.csc.request("blockchaineditor", "getblockchains", {}, function(blockchains)
            {
                var selectedBlockchain = false;
                mod.dom.clean(blockchainListPanel);
                var table = document.createElement("table");
                var tbody = document.createElement("tbody");
                table.style.width = "100%";
                table.appendChild(tbody);
                blockchainListPanel.appendChild(table);
                for (var i in blockchains)
                    if (blockchains.hasOwnProperty(i))
                        createblockchainEntry(tbody, blockchains[i]);
                createNewblockchainButton(tbody);
                
                function createblockchainEntry(tbody, blockchain)
                {
                    var tr = document.createElement("tr");
                    blockchain.td = document.createElement("td");
                    blockchain.td.style.padding = "2px";
                    blockchain.td.style.borderBottom = "1px dotted #777";
                    blockchain.td.obj = blockchain;
                    blockchain.td.onmouseover = function(e)
                    {
                        if (this.obj != selectedBlockchain) this.style.background = "#ddf";
                    };
                    blockchain.td.onmouseout = function(e)
                    {
                        if (this.obj != selectedBlockchain) this.style.background = "inherit";
                    };
                    blockchain.td.onclick = function(e)
                    {
                        select(this.obj);
                    };
                    blockchain.td.customContextMenu = function(e)
                    {
                        var obj = this.obj;
                        var menu = new mod.contextmenu.ContextMenu();
                        menu.addEntry(nls("Delete blockchain"), function()
                        {
                            var box = mod.layerbox.LayerBox();
                            box.setTitle(nls("Delete blockchain"));
                            box.setStyle("error");
                            var text = nls("Do you really want to delete the blockchain") + " \"" + obj.name + "\"?";
                            var buttons = box.multipleChoice(text, [nls("Yes"), nls("No")]);
                            buttons[0].onclick = function()
                            {
                                if (buttons[0].disabled) return;
                                buttons[0].disabled = true;
                                buttons[1].disabled = true;
                                buttons[0].value = nls("Please wait...");
                                mod.csc.request("blockchaineditor", "deleteblockchain", {"id": obj.id}, function(data)
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
                    blockchain.namenode = document.createTextNode(blockchain.name);
                    blockchain.td.appendChild(blockchain.namenode);
                    tr.appendChild(blockchain.td);
                    tbody.appendChild(tr);
                }
                
                function createNewblockchainButton(tbody)
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
                        newBox.setTitle(nls("Create new blockchain"));
                        var nameField = newBox.addInput("Name:", document.createElement("input"));
                        nameField.type = "text";
                        var submitButton = newBox.addInput(null, "submit");
                        submitButton.value = nls("Create");
                        nameField.focus();
                        newBox.events.push(mod.event.catchKey(27, newBox.destroy));
                        newBox.form.onsubmit = function(e)
                        {
                            if (submitButton.disabled) return killEvent(e);
                            submitButton.disabled = true;
                            submitButton.value = nls("Please wait...");
                            mod.csc.request("blockchaineditor", "createblockchain", {"name": nameField.value}, function(data)
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
                    td.appendChild(document.createTextNode(nls("Create new blockchain")));
                    tr.appendChild(td);
                    tbody.appendChild(tr);
                }
                    
                function select(blockchain)
                {
                    if (selectedBlockchain) selectedBlockchain.td.style.background = "inherit";
                    blockchain.td.style.background = "#bbf";
                    selectedBlockchain = blockchain;
                    mod.dom.clean(blockchainEditPanel);
                    delegate(blockchainEditPanel, "settingseditor",
                    {
                        "id": blockchain.id,
                        "savecallback": function(settings, callback)
                        {
                            blockchain.name = settings.name;
                            blockchain.namenode.nodeValue = settings.name;
                            callback();
                        },
                    });
                }
            }, {"cache": "none"});
        }
    }

};
