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
            
            function makeTag(tag, type, id, value, fill)
            {
                var input = document.createElement(tag);
                if (id) input.id = id;
                if (type) input.type = type;
                if (value !== null) input.value = value;
                if (fill)
                {
                    input.style.boxSizing = "border-box";
                    input.style.MozBoxSizing = "border-box";
                    input.style.MsBoxSizing = "border-box";
                    input.style.width = "100%";
                }
                return input;
            }

            var editors =
            {
                "string": function(range, setting, id)
                {
                    var input = makeTag("input", "text", id, setting.value, true);
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return input.value;
                    };
                },
                
                "password": function(range, setting, id)
                {
                    var input = makeTag("input", "password", id, setting.value, true);
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return input.value;
                    };
                },
                
                "multiline": function(range, setting, id)
                {
                    var input = makeTag("textarea", null, id, setting.value, true);
                    input.style.height = "100px";
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return input.value;
                    };
                },
                
                "json": function(range, setting, id)
                {
                    var input = makeTag("textarea", null, id, JSON.stringify(setting.value), true);
                    input.style.height = "100px";
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return JSON.parse(input.value);
                    };
                },
                
                "int": function(range, setting, id)
                {
                    var input = makeTag("input", "text", id, setting.value, true);
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        var value = parseInt(input.value);
                        if (isNaN(value)) throw nls("Could not parse integer");
                        return value;
                    };
                },
                
                "float": function(range, setting, id)
                {
                    var input = makeTag("input", "text", id, setting.value, true);
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        var value = parseFloat(input.value);
                        if (isNaN(value)) throw nls("Could not parse float");
                        return value;
                    };
                },
                
                "boolean": function(range, setting, id)
                {
                    var input = makeTag("input", "checkbox", id, null, false);
                    input.checked = setting.value;
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return input.checked;
                    };
                },
                
                "enum": function(range, setting, id)
                {
                    var input = makeTag("select", null, id, null, true);
                    for (var i in setting.spec.values)
                        if (setting.spec.values.hasOwnProperty(i))
                        {
                            var option = document.createElement("option");
                            option.value = setting.spec.values[i].value;
                            if (setting.spec.values[i].value == setting.value)
                                option.selected = "selected";
                            option.appendChild(document.createTextNode(setting.spec.values[i].title));
                            input.appendChild(option);
                        }
                    range.appendChild(input);
                    this.getValue = function()
                    {
                        return input.options[input.selectedIndex].value;
                    };
                },
                
                "list": function(range, setting, id)
                {
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    var tr = document.createElement("tr");
                    var th = document.createElement("th");
                    th.appendChild(document.createTextNode(setting.spec.element.title));
                    tr.appendChild(th);
                    th = document.createElement("th");
                    var addButton = makeTag("input", "button", null, "+", true);
                    th.appendChild(addButton);
                    tr.appendChild(th);
                    tbody.appendChild(tr);
                    table.style.width = "100%";
                    var rows = [];
                    for (var i in setting.value)
                        if (setting.value.hasOwnProperty(i))
                            rows.push(makeRow(setting.value[i]));
                    table.appendChild(tbody);
                    range.appendChild(table);
                    addButton.onclick = function(e)
                    {
                        rows.push(makeRow(""));
                    };
                    function makeRow(value)
                    {
                        var elementsetting = {"spec": setting.spec.element, "value": value};
                        var row = {"element": elementsetting};
                        var tr = document.createElement("tr");
                        var td = document.createElement("td");
                        editor = editors[row.element.spec.type];
                        if (editor) row.element.editor = new editor(td, row.element, null);
                        tr.appendChild(td);
                        td = document.createElement("td");
                        var removeButton = makeTag("input", "button", null, "-", true);
                        td.appendChild(removeButton);
                        tr.appendChild(td);
                        tbody.appendChild(tr);
                        removeButton.onclick = function(e)
                        {
                            var idx = rows.indexOf(row);
                            if (idx != -1) rows.splice(idx, 1);
                            if (tr.parentNode) tr.parentNode.removeChild(tr);
                        }
                        return row;
                    }
                    this.getValue = function()
                    {
                        var list = [];
                        for (var i in rows)
                            if (rows.hasOwnProperty(i))
                            {
                                list.push(rows[i].element.editor ? rows[i].element.editor.getValue() : rows[i].element.value);
                            }
                        return list;
                    };
                },
                
                "dict": function(range, setting, id)
                {
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    var tr = document.createElement("tr");
                    var th = document.createElement("th");
                    th.appendChild(document.createTextNode(setting.spec.key.title));
                    tr.appendChild(th);
                    th = document.createElement("th");
                    th.appendChild(document.createTextNode(setting.spec.value.title));
                    tr.appendChild(th);
                    th = document.createElement("th");
                    var addButton = makeTag("input", "button", null, "+", true);
                    th.appendChild(addButton);
                    tr.appendChild(th);
                    tbody.appendChild(tr);
                    table.style.width = "100%";
                    var rows = [];
                    for (var i in setting.value)
                        if (setting.value.hasOwnProperty(i))
                            rows.push(makeRow(i, setting.value[i]));
                    table.appendChild(tbody);
                    range.appendChild(table);
                    addButton.onclick = function(e)
                    {
                        rows.push(makeRow("", ""));
                    };
                    function makeRow(key, value)
                    {
                        var keysetting = {"spec": setting.spec.key, "value": key};
                        var valuesetting = {"spec": setting.spec.value, "value": value};
                        var row = {"key": keysetting, "value": valuesetting};
                        var tr = document.createElement("tr");
                        var td = document.createElement("td");
                        var editor = editors[row.key.spec.type];
                        if (editor) row.key.editor = new editor(td, row.key, null);
                        tr.appendChild(td);
                        td = document.createElement("td");
                        editor = editors[row.value.spec.type];
                        if (editor) row.value.editor = new editor(td, row.value, null);
                        tr.appendChild(td);
                        td = document.createElement("td");
                        var removeButton = makeTag("input", "button", null, "-", true);
                        td.appendChild(removeButton);
                        tr.appendChild(td);
                        tbody.appendChild(tr);
                        removeButton.onclick = function(e)
                        {
                            var idx = rows.indexOf(row);
                            if (idx != -1) rows.splice(idx, 1);
                            if (tr.parentNode) tr.parentNode.removeChild(tr);
                        }
                        return row;
                    }
                    this.getValue = function()
                    {
                        var dict = {};
                        for (var i in rows)
                            if (rows.hasOwnProperty(i))
                            {
                                var key = rows[i].key.editor ? rows[i].key.editor.getValue() : rows[i].key.value;
                                var value = rows[i].value.editor ? rows[i].value.editor.getValue() : rows[i].value.value;
                                if (dict.hasOwnProperty(key)) throw nls("Key collision in dict") + ": \"" + key + "\"";
                                dict[key] = value;
                            }
                        return dict;
                    };
                },
            };
            
            mod.dom.clean(range);
            var form = document.createElement("form");
            var table = document.createElement("table");
            var tbody = document.createElement("tbody");
            for (var i in data.settings)
                if (data.settings.hasOwnProperty(i))
                {
                    var setting = data.settings[i];
                    var id = id = "box_" + uid + "_settinginput" + (inputindex++);
                    var editor = editors[setting.spec.type];
                    if (!editor) continue;
                    var tr = document.createElement("tr");
                    var th = document.createElement("th");
                    var td = document.createElement("td");
                    var label = document.createElement("label");
                    setting.editor = new editor(td, setting, id);
                    label.htmlFor = id;
                    th.className = "box_form_label";
                    var title = setting.spec.title + (setting.spec.type == "boolean" ? "" : ":");
                    label.appendChild(document.createTextNode(title));
                    if (setting.spec.type == "boolean") td.appendChild(label);
                    else th.appendChild(label);
                    tr.appendChild(th);
                    tr.appendChild(td);
                    tbody.appendChild(tr);
                }
            var submit = makeTag("input", "submit", null, nls("Save"), true);
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
                        if (setting.editor)
                            try
                            {
                                settings[setting.name] = setting.editor.getValue();
                            }
                            catch (e)
                            {
                                errorMsg = nls("Invalid value in field") + " \"" + setting.spec.title + "\": " + e;
                                break;
                            }
                        else settings[setting.name] = setting.value;
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
