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

mod.settingseditor = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["dom"], callback);
    },

    // Shows a settings editor for the specified settings in the specified range
    "InlineUI": function(range, config)
    {
        var uid = "";
        var chars = "01234567890ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz";
        for (var i = 0; i < 16; i++) uid += chars.substr(0 | Math.random() * chars.length, 1);
        var inputindex = 0;
        mod.dom.clean(range);
        showLoadingIndicator(range);
        mod.csc.request("settingseditor", "readsettings", {"id": config.id}, function(data)
        {
            if (data.error) return error(data.error);
            mod.dom.clean(range);
            var form = document.createElement("form");
            var table = document.createElement("table");
            var tbody = document.createElement("tbody");
            for (var i in data.settings)
                if (data.settings.hasOwnProperty(i))
                {
                    var setting = data.settings[i];
                    var input;
                    switch (setting.spec.type)
                    {
                        case "string":
                        case "int":
                        case "float":
                        case "password":
                            input = document.createElement("input");
                            input.type = setting.spec.type == "password" ? "password" : "text";
                            input.value = setting.value;
                            break;
                        case "multiline":
                        case "json":
                            input = document.createElement("textarea");
                            input.style.height = "100px";
                            input.value = setting.spec.type == "json" ? JSON.stringify(setting.value) : setting.value;
                            break;
                        case "boolean":
                            input = document.createElement("input");
                            input.type = "checkbox";
                            input.checked = setting.value;
                            break;
                        default: continue;
                    }
                    setting.input = input;
                    var tr = document.createElement("tr");
                    var th = document.createElement("th");
                    var td = document.createElement("td");
                    var label = document.createElement("label");
                    if (setting.spec.type != "boolean")
                    {
                        input.style.boxSizing = "border-box";
                        input.style.MozBoxSizing = "border-box";
                        input.style.MsBoxSizing = "border-box";
                        input.style.width = "100%";
                    }
                    input.id = "box_" + uid + "_settinginput" + (inputindex++);
                    label.htmlFor = input.id;
                    var title = setting.spec.title + (setting.spec.type == "boolean" ? "" : ":");
                    label.appendChild(document.createTextNode(title));
                    th.className = "box_form_label";
                    td.appendChild(input);
                    if (setting.spec.type == "boolean") td.appendChild(label);
                    else th.appendChild(label);
                    tr.appendChild(th);
                    tr.appendChild(td);
                    tbody.appendChild(tr);
                }
            var submit = document.createElement("input");
            submit.type = "submit";
            submit.value = nls("Save");
            submit.style.boxSizing = "border-box";
            submit.style.MozBoxSizing = "border-box";
            submit.style.MsBoxSizing = "border-box";
            submit.style.width = "100%";
            table.style.width = "100%";
            table.appendChild(tbody);
            form.appendChild(table);
            form.appendChild(submit);
            range.appendChild(form);
            form.onsubmit = function(e)
            {
                if (submit.disabled) return;
                submit.disabled = true;
                submit.value = nls("Please wait...");
                settings = {};
                var errorMsg = false;
                for (var i in data.settings)
                    if (data.settings.hasOwnProperty(i))
                    {
                        var setting = data.settings[i];
                        var invalid = false;
                        switch (setting.spec.type)
                        {
                            case "string":
                            case "password":
                                settings[setting.name] = setting.input.value;
                                break;
                            case "int":
                                settings[setting.name] = parseInt(setting.input.value);
                                if (isNaN(settings[setting.name])) invalid = true;
                                break;
                            case "float":
                                settings[setting.name] = parseFloat(setting.input.value);
                                if (isNaN(settings[setting.name])) invalid = true;
                                break;
                            case "multiline":
                            case "json":
                                settings[setting.name] = setting.input.value;
                                if (setting.spec.type == "json")
                                    try
                                    {
                                        log(settings[setting.name]);
                                        settings[setting.name] = JSON.parse(settings[setting.name]);
                                        log(settings[setting.name]);
                                    }
                                    catch (e)
                                    {
                                        invalid = true;
                                    }
                                break;
                            case "boolean":
                                settings[setting.name] = setting.input.checked;
                                break;
                            default: settings[setting.name] = setting.value;
                        }
                        if (invalid)
                        {
                            errorMsg = nls("Invalid value in field") + " \"" + setting.spec.label + "\"!";
                            break;
                        }
                    }
                if (!errorMsg && config.validationcallback) errorMsg = config.validationcallback(settings);
                if (errorMsg)
                {
                    error(errorMsg);
                    submit.value = nls("Save");
                    submit.disabled = false;
                }
                else
                {
                    mod.csc.request("settingseditor", "writesettings",
                    {
                        "id": config.id,
                        "settings": settings,
                    }, function(data)
                    {
                        if (data.error) return error(data.error);
                        if (config.savecallback) config.savecallback(settings, done);
                        else done();
                        function done()
                        {
                            submit.value = nls("Save");
                            submit.disabled = false;
                        }
                    }, {"cache": "none"});
                }
                return killEvent(e);
            };
        }, {"cache": "none"});
    }

};
