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

mod.loggadget = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "box", "event", "layerbox", "uiconfig"], callback);
    },

    // Shows a statistics dashboard
    "Gadget": function(box, config)
    {
        var stream = false;
        mod.dom.clean(box.contentNode);
        box.setTitle(nls("Log"));
        if (!mod.uiconfig.data.loggadget) mod.uiconfig.data.loggadget = {};
        if (!mod.uiconfig.data.loggadget.height) mod.uiconfig.data.loggadget.height = "400px";
        if (!mod.uiconfig.data.loggadget.loglevel) mod.uiconfig.data.loggadget.loglevel = 500;
        box.setOuterHeight(mod.uiconfig.data.loggadget.height);
        box.setResizable(false, true, function()
        {
            div.scrollTop = div.scrollHeight;
        }, function()
        {
            mod.uiconfig.data.loggadget.height = box.rootNode.style.height;
            mod.uiconfig.update();
        });
        var div = document.createElement("div");
        var table = document.createElement("table");
        var tbody = document.createElement("tbody");
        table.appendChild(tbody);
        div.style.position = "absolute";
        div.style.left = "0px";
        div.style.right = "0px";
        div.style.height = "100%";
        div.style.overflow = "auto";
        div.allowSelect = true;
        div.allowDrag = true;
        div.allowContextMenu = true;
        div.className = "autocursor";
        div.appendChild(table);
        box.contentNode.style.position = "relative";
        box.contentNode.style.backgroundColor = "#000";
        box.contentNode.style.color = "#fff";
        box.contentNode.style.padding = "0px";
        box.contentNode.appendChild(div);
        var settingsButton = document.createElement("input");
        settingsButton.type = "button";
        settingsButton.value = nls("Settings");
        settingsButton.className = "box_titlebutton";
        settingsButton.style.cssFloat = "right";
        settingsButton.onclick = function(e)
        {
            var box = mod.layerbox.LayerBox();
            box.setTitle(nls("Log viewer settings"));
            var loglevelField = box.addInput(nls("Log level:"));
            loglevelField.value = mod.uiconfig.data.loggadget.loglevel;
            var submitButton = box.addInput(null, "submit");
            submitButton.value = nls("Save");
            loglevelField.focus();
            box.events.push(mod.event.catchKey(27, box.destroy));
            box.form.onsubmit = function(e)
            {
                if (submitButton.disabled) return killEvent(e);
                submitButton.disabled = true;
                submitButton.value = nls("Please wait...");
                var errorMsg = false;
                var loglevel = parseInt(loglevelField.value);
                if (isNaN(loglevel)) errorMsg = nls("Invalid log level");
                if (errorMsg)
                {
                    submitButton.disabled = false;
                    submitButton.value = nls("Save");
                    error(errorMsg);
                }
                else
                {
                    box.destroy();
                    mod.uiconfig.data.loggadget.loglevel = loglevel;
                    mod.uiconfig.update();
                    reconnect();
                }
                return killEvent(e);
            };
        };
        box.titleNode.appendChild(settingsButton);
        var reconnectButton = document.createElement("input");
        reconnectButton.type = "button";
        reconnectButton.value = nls("Reconnect");
        reconnectButton.className = "box_titlebutton";
        reconnectButton.style.cssFloat = "right";
        reconnectButton.style.display = "none";
        reconnectButton.onclick = function(e)
        {
            reconnectButton.style.display = "none";
            reconnect();
        };
        box.titleNode.appendChild(reconnectButton);
        
        function pad(value, length)
        {
            value = String(value);
            while (value.length < length) value = "0" + value;
            return value;
        }
        
        function askreconnect(errormessage)
        {
            var askBox = mod.layerbox.LayerBox();
            askBox.setTitle(nls("Log stream connection lost"));
            var buttons = askBox.multipleChoice(nls("Do you want to reconnect to the log stream?"),
                                                [nls("Yes"), nls("No")]);
            buttons[0].onclick = function()
            {
                reconnect();
                askBox.destroy();
            };
            buttons[1].onclick = function()
            {
              askBox.destroy();
              reconnectButton.style.display = "block";
            };
            askBox.events.push(mod.event.catchKey(13, buttons[0].onclick));
            askBox.events.push(mod.event.catchKey(27, buttons[1].onclick));
            askBox.setCloseable(buttons[1].onclick);
        }

        function reconnect()
        {
            if (stream)
            {
              stream.onreadystatechange = nullfunc;
              stream.abort();
            }
            mod.dom.clean(tbody);
            stream = mod.csc.request("log", "stream", {"loglevel": mod.uiconfig.data.loggadget.loglevel}, function(data)
            {
                var atBottom = div.scrollTop + div.offsetHeight + 20 > div.scrollHeight;
                for (var i in data)
                    if (data.hasOwnProperty(i))
                    {
                        var tr = document.createElement("tr");
                        var td1 = document.createElement("td");
                        var td2 = document.createElement("td");
                        var td3 = document.createElement("td");
                        var td4 = document.createElement("td");
                        var d = new Date(data[i].timestamp);
                        var timestamp = pad(d.getFullYear(), 4) + "-" + pad(d.getMonth() + 1, 2) + "-"
                                      + pad(d.getDate(), 2) + " " + pad(d.getHours(), 2) + ":"
                                      + pad(d.getMinutes(), 2) + ":" + pad(d.getSeconds(), 2) + "." 
                                      + pad(d.getMilliseconds(), 3);
                        td1.style.padding = "0px 3px";
                        td1.style.whiteSpace = "pre";
                        td1.appendChild(document.createTextNode(timestamp));
                        td2.style.padding = "0px 3px";
                        td2.style.whiteSpace = "pre";
                        td2.style.textAlign = "right";
                        td2.appendChild(document.createTextNode("[" + data[i].loglevel + "]"));
                        td3.style.padding = "0px 3px";
                        td3.style.whiteSpace = "pre";
                        td3.style.textAlign = "right";
                        td3.appendChild(document.createTextNode(data[i].source + ": "));
                        td4.style.padding = "0px 3px";
                        td4.style.whiteSpace = "pre";
                        for (var j in data[i].message)
                          if (data[i].message.hasOwnProperty(j))
                          {
                              var span = document.createElement("span");
                              var format = data[i].message[j].format;
                              if (format.indexOf("r") != -1) span.style.color = "#f00";
                              if (format.indexOf("y") != -1) span.style.color = "#ff0";
                              if (format.indexOf("g") != -1) span.style.color = "#0f0";
                              if (format.indexOf("B") != -1) span.style.fontWeight = "bold";
                              span.appendChild(document.createTextNode(data[i].message[j].data));
                              td4.appendChild(span);
                          }
                        tr.appendChild(td1);
                        tr.appendChild(td2);
                        tr.appendChild(td3);
                        tr.appendChild(td4);
                        tbody.appendChild(tr);
                        if (atBottom) div.scrollTop = div.scrollHeight;
                    }
            },
            {
                "cache": "none",
                "stream": true,
                "noindicator": true,
                "callback": askreconnect,
                "error": askreconnect,
                "commerror": askreconnect,
            });
        }
        reconnect();
    }

};
