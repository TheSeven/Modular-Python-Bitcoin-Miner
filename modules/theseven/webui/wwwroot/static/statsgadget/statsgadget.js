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

mod.statsgadget = {

    // Called on module initialisation, ensures that all dependencies are satisfied
    "init": function(callback)
    {
        depend(["csc", "dom", "box", "event", "layerbox", "uiconfig"], callback);
    },

    // Shows a statistics dashboard
    "Gadget": function(box, config)
    {
        mod.dom.clean(box.contentNode);
        box.setTitle(nls("Statistics"));
        if (!mod.uiconfig.data.statsgadget) mod.uiconfig.data.statsgadget = {};
        if (!mod.uiconfig.data.statsgadget.height) mod.uiconfig.data.statsgadget.height = "250px";
        if (!mod.uiconfig.data.statsgadget.refreshinterval) mod.uiconfig.data.statsgadget.refreshinterval = 5;
        box.setOuterHeight(mod.uiconfig.data.statsgadget.height);
        box.setResizable(false, true, function()
        {
            div.scrollTop = div.scrollHeight;
        }, function()
        {
            mod.uiconfig.data.statsgadget.height = box.rootNode.style.height;
            mod.uiconfig.update();
        });
        var div = document.createElement("div");
        div.style.position = "absolute";
        div.style.left = "0px";
        div.style.right = "0px";
        div.style.height = "100%";
        div.style.overflow = "auto";
        box.contentNode.style.position = "relative";
        box.contentNode.appendChild(div);
        var settingsButton = document.createElement("input");
        settingsButton.type = "button";
        settingsButton.value = nls("Settings");
        settingsButton.className = "box_titlebutton";
        settingsButton.style.cssFloat = "right";
        settingsButton.onclick = function(e)
        {
            var box = mod.layerbox.LayerBox();
            box.setTitle(nls("Statistics viewer settings"));
            var refreshIntervalField = box.addInput(nls("Refresh interval:"));
            refreshIntervalField.value = mod.uiconfig.data.statsgadget.refreshinterval;
            var submitButton = box.addInput(null, "submit");
            submitButton.value = nls("Save");
            refreshIntervalField.focus();
            box.events.push(mod.event.catchKey(27, box.destroy));
            box.form.onsubmit = function(e)
            {
                if (submitButton.disabled) return killEvent(e);
                submitButton.disabled = true;
                submitButton.value = nls("Please wait...");
                var errorMsg = false;
                var refreshinterval = parseInt(refreshIntervalField.value);
                if (isNaN(refreshinterval)) errorMsg = nls("Invalid refresh interval");
                if (errorMsg)
                {
                    submitButton.disabled = false;
                    submitButton.value = nls("Save");
                    error(errorMsg);
                }
                else
                {
                    box.destroy();
                    mod.uiconfig.data.statsgadget.refreshinterval = refreshinterval;
                    mod.uiconfig.update();
                }
                return killEvent(e);
            };
        };
        box.titleNode.appendChild(settingsButton);
        var refreshButton = document.createElement("input");
        refreshButton.type = "button";
        refreshButton.value = nls("Refresh");
        refreshButton.className = "box_titlebutton";
        refreshButton.style.cssFloat = "right";
        refreshButton.onclick = refresh;
        box.titleNode.appendChild(refreshButton);
        showLoadingIndicator(div);
        refresh();
        var timeout = null;
        function refresh()
        {
            if (timeout) clearTimeout(timeout);
            mod.csc.request("statsgadget", "getallstats", {}, function(data)
            {
                var time = data["timestamp"];
                var gHashesTotalDefinition = {"title": "GHashes total", "renderer": intRenderer};
                var averageMHpsDefinition = {"title": "Average MH/s", "renderer": floatRenderer, "rendererconfig": {"precision": 2}};
                var jobRequestsDefinition = {"title": "Job requests", "renderer": intRenderer};
                var uploadRetriesDefinition = {"title": "Upload retries", "renderer": intRenderer};
                var acceptedJobsDefinition = {"title": "Accepted jobs", "renderer": intRenderer};
                var receivedJobsDefinition = {"title": "Received jobs", "renderer": intRenderer};
                var acceptedSharesDefinition = {"title": "Accepted shares", "renderer": intRenderer};
                var uptimeDefinition = {"title": "Uptime", "transform": timeAgoTransform, "renderer": timespanRenderer};
                var timeAgoDefinition = {"title": "Time ago", "transform": timeAgoTransform, "renderer": timespanRenderer};
                var failedJobRequestsDefinition =
                {
                    "title": "Failed job requests",
                    "renderer": intPercentageRenderer,
                    "rendererconfig": {"reference": makeReference("jobrequests"), "percentagePrecision": 2},
                };
                var acceptedJobsPercentageDefinition =
                {
                    "title": "Accepted jobs",
                    "renderer": intPercentageRenderer,
                    "rendererconfig": {"reference": makeReference("jobsreceived"), "percentagePrecision": 2},
                };
                var canceledJobsDefinition =
                {
                    "title": "Canceled jobs",
                    "renderer": intPercentageRenderer,
                    "rendererconfig": {"reference": makeReference("jobsaccepted"), "percentagePrecision": 2},
                };
                var rejectedSharesDefinition =
                {
                    "title": "Rejected shares",
                    "renderer": intPercentageRenderer,
                    "rendererconfig": {"reference": submittedSharesReference, "percentagePrecision": 2},
                };
                var invalidSharesDefinition =
                {
                    "title": "Invalid shares",
                    "renderer": intPercentageRenderer,
                    "rendererconfig": {"reference": foundSharesReference, "percentagePrecision": 2},
                };
                var workerTable = makeTable(data["workers"],
                {
                    "obj": {},
                    "id": {},
                    "name": {100: {"title": "Worker name"}},
                    "mhps": {200: {"title": "Current MH/s", "renderer": floatRenderer, "rendererconfig": {"precision": 2}}},
                    "temperature": {210: {"title": "Temperature [°C]", "renderer": floatRenderer, "rendererconfig": {"precision": 2}}},
                    "errorrate": {220: {"title": "Error rate", "renderer": percentageRenderer, "rendererconfig": {"percentagePrecision": 2}}},
                    "avgmhps": {230: averageMHpsDefinition},
                    "ghashes": {240: gHashesTotalDefinition},
                    "jobsaccepted": {300: acceptedJobsDefinition, 310: makePerHourDefinition("Jobs per hour", 2)},
                    "jobscanceled": {320: canceledJobsDefinition, 330: makePerHourDefinition("Canceled per hour", 2)},
                    "sharesaccepted": {400: acceptedSharesDefinition},
                    "sharesrejected": {410: rejectedSharesDefinition, 420: makePerHourDefinition("Rejects per hour", 2)},
                    "sharesinvalid": {430: invalidSharesDefinition, 440: makePerHourDefinition("Invalids per hour", 2)},
                    "starttime": {1000: uptimeDefinition},
                    "parallel_jobs": {1100: {"title": "Jobs processed in parallel", "renderer": intRenderer}},
                    "current_job": {},
                    "current_work_source": {},
                    "current_work_source_id": {},
                    "current_work_source_name": {2000: {"title": "Current work source"}},
                });
                var worksourceTable = makeTable(data["worksources"],
                {
                    "obj": {},
                    "id": {},
                    "name": {100: {"title": "Work source name"}},
                    "blockchain": {},
                    "blockchain_id": {},
                    "blockchain_name": {110: {"title": "Blockchain"}},
                    "signals_new_block": {110: {"title": "Signals new block", "renderer": booleanRenderer}},
                    "supports_rollntime": {120: {"title": "Supports X-Roll-NTime", "renderer": booleanRenderer}},
                    "jobs_per_request": {130: {"title": "Jobs per request", "renderer": intRenderer}},
                    "job_expiry": {140: {"title": "Job validity timeframe", "renderer": timespanRenderer}},
                    "difficulty": {150: {"title": "Difficulty", "renderer": floatRenderer, "rendererconfig": {"precision": 2}}},
                    "avgmhps": {200: averageMHpsDefinition},
                    "ghashes": {210: gHashesTotalDefinition},
                    "jobrequests": {300: jobRequestsDefinition, 310: makePerHourDefinition("Requests per hour", 2)},
                    "failedjobreqs": {320: failedJobRequestsDefinition, 330: makePerHourDefinition("Failed requests per hour", 2)},
                    "uploadretries": {340: uploadRetriesDefinition, 350: makePerHourDefinition("Upload retries per hour", 2)},
                    "jobsreceived": {400: receivedJobsDefinition, 410: makePerHourDefinition("Received per hour", 2)},
                    "jobsaccepted": {420: acceptedJobsPercentageDefinition, 430: makePerHourDefinition("Accepted per hour", 2)},
                    "jobscanceled": {440: canceledJobsDefinition, 450: makePerHourDefinition("Canceled per hour", 2)},
                    "sharesaccepted": {500: acceptedSharesDefinition},
                    "sharesrejected": {510: rejectedSharesDefinition, 520: makePerHourDefinition("Rejects per hour", 2)},
                    "starttime": {1000: uptimeDefinition},
                    "consecutive_errors": {1100: {"title": "Consecutive errors", "renderer": intRenderer}},
                    "locked_out": {1200: {"title": "Lockout time remaining", "renderer": timespanRenderer}},
                });
                var blockchainTable = makeTable(data["blockchains"],
                {
                    "obj": {},
                    "id": {},
                    "name": {100: {"title": "Blockchain name"}},
                    "blocks": {200: {"title": "Blocks seen", "renderer": intRenderer}, 210: makePerHourDefinition("Blocks per hour", 2)},
                    "lastblock": {220: {"title": "Last block", "renderer": timestampRenderer}, 230: timeAgoDefinition},
                    "avgmhps": {300: averageMHpsDefinition},
                    "ghashes": {310: gHashesTotalDefinition},
                    "jobsreceived": {400: receivedJobsDefinition, 410: makePerHourDefinition("Received per hour", 2)},
                    "jobsaccepted": {420: acceptedJobsPercentageDefinition, 430: makePerHourDefinition("Accepted per hour", 2)},
                    "jobscanceled": {440: canceledJobsDefinition, 450: makePerHourDefinition("Canceled per hour", 2)},
                    "sharesaccepted": {500: acceptedSharesDefinition},
                    "sharesrejected": {510: rejectedSharesDefinition, 520: makePerHourDefinition("Rejects per hour", 2)},
                    "starttime": {1000: uptimeDefinition},
                });
                mod.dom.clean(div);
                div.appendChild(workerTable);
                div.appendChild(document.createElement("hr"));
                div.appendChild(worksourceTable);
                div.appendChild(document.createElement("hr"));
                div.appendChild(blockchainTable);
                timeout = setTimeout(refresh, mod.uiconfig.data.statsgadget.refreshinterval * 1000);
                
                function perHourTransform(stats, value, def)
                {
                    return value * 3600 / (time - stats.starttime);
                }
                
                function timeAgoTransform(stats, value, def)
                {
                    return time - value;
                }
                
                function foundSharesReference(stats, value, def)
                {
                    return stats.sharesaccepted + stats.sharesrejected + stats.sharesinvalid;
                }
                
                function submittedSharesReference(stats, value, def)
                {
                    return stats.sharesaccepted + stats.sharesrejected;
                }
                
                function makeReference(field)
                {
                    return function(stats, value, def)
                    {
                        return stats[field];
                    }
                }
                
                function makePerHourDefinition(title, precision)
                {
                    return {
                        "title": title,
                        "transform": perHourTransform,
                        "renderer": floatRenderer,
                        "rendererconfig": {"precision": precision}
                    };
                }
                
                function buildKeyMap(keymap, defs, col, data)
                {
                    for (var i in data)
                        if (data.hasOwnProperty(i))
                            for (var j in data[i])
                                if (data[i].hasOwnProperty(j))
                                {
                                    if (j == "children") col = buildKeyMap(keymap, defs, col, data[i][j]);
                                    else
                                    {
                                        keymap[j] = true;
                                        if (!defs[j])
                                        {
                                            defs[j] = {};  
                                            defs[j][col++] = {};
                                        }
                                    }
                                }
                    return col;
                }
                
                function makeTable(data, defs)
                {
                    defs.children = {};
                    keymap = {};
                    buildKeyMap(keymap, defs, 5000, data);
                    var cols = {};
                    for (var i in keymap)
                        if (keymap.hasOwnProperty(i))
                            for (var col in defs[i])
                                if (defs[i].hasOwnProperty(col))
                                {
                                    cols[col] = defs[i][col];
                                    if (!cols[col].field) cols[col].field = i;
                                    if (!cols[col].title) cols[col].title = cols[col].field;
                                    if (!cols[col].renderer) cols[col].renderer = stringRenderer;
                                    if (!cols[col].rendererconfig) cols[col].rendererconfig = {};
                                }
                    delete keymap;
                    var keys = [];
                    for (var i in cols)
                        if (cols.hasOwnProperty(i))
                            keys.push(i);
                    keys.sort(function(a, b)
                    {
                        return a - b;
                    });
                    defs = [];
                    for (var i in keys)
                        if (keys.hasOwnProperty(i))
                            defs.push(cols[keys[i]]);
                    delete cols;
                    delete keys;
                    var table = document.createElement("table");
                    var tbody = document.createElement("tbody");
                    var tr = document.createElement("tr");
                    for (var i in defs)
                        if (defs.hasOwnProperty(i))
                        {
                            var th = document.createElement("th");
                            th.appendChild(document.createTextNode(defs[i].title));
                            tr.appendChild(th);
                        }
                    tbody.appendChild(tr);
                    table.appendChild(tbody);
                    table.className = "table_visible";
                    table.style.border = "hidden";
                    makeRows(tbody, data, defs, 0);
                    return table;
                }
                
                function makeRows(tbody, data, defs, level)
                {
                    for (var i in data)
                        if (data.hasOwnProperty(i))
                        {
                            var tr = document.createElement("tr");
                            var first = true;
                            for (var j in defs)
                                if (defs.hasOwnProperty(j))
                                {
                                    var td = document.createElement("td");
                                    td.style.whiteSpace = "nowrap";
                                    if (first)
                                    {
                                        td.style.textAlign = "left";
                                        td.style.paddingLeft = (3 + level * 20) + "px";
                                    }
                                    var value = data[i][defs[j].field];
                                    if (defs[j].transform) value = defs[j].transform(data[i], value, defs[j]);
                                    defs[j].renderer(td, data[i], value, defs[j], defs[j].rendererconfig);
                                    tr.appendChild(td);
                                    first = false;
                                }
                            tbody.appendChild(tr);
                            if (data[i].children) makeRows(tbody, data[i].children, defs, level + 1);
                        }
                }
                
                function intRenderer(td, stats, value, def, config)
                {
                    config.precision = 0;
                    floatRenderer(td, stats, Math.round(value), def, config);
                }
                
                function intPercentageRenderer(td, stats, value, def, config)
                {
                    config.precision = 0;
                    floatPercentageRenderer(td, stats, Math.round(value), def, config);
                }
                
                function floatRenderer(td, stats, value, def, config)
                {
                    if (!value) value = 0;
                    if (config.precision) value = value.toFixed(config.precision);
                    td.appendChild(document.createTextNode(value));
                }
                
                function floatPercentageRenderer(td, stats, value, def, config)
                {
                    floatRenderer(td, stats, value, def, config);
                    var percentage = 100 * value / config.reference(stats, value, def);
                    if (!percentage) percentage = 0;
                    if (config.percentagePrecision)
                        percentage = percentage.toFixed(config.percentagePrecision);
                    td.appendChild(document.createTextNode(" (" + percentage + "%)"));
                }
                
                function percentageRenderer(td, stats, value, def, config)
                {
                    var percentage = 100 * value
                    if (!percentage) percentage = 0;
                    if (config.percentagePrecision)
                        percentage = percentage.toFixed(config.percentagePrecision);
                    td.appendChild(document.createTextNode(percentage + "%"));
                }
                
                function booleanRenderer(td, stats, value, def, config)
                {
                    if (!config["default"]) config["default"] = "Unknown";
                    if (value === false) value = "No";
                    else if (value) value = "Yes";
                    else value = config["default"];
                    td.appendChild(document.createTextNode(value));
                }
                
                function stringRenderer(td, stats, value, def, config)
                {
                    if (!config["default"]) config["default"] = "Unknown";
                    if (value === undefined) config["default"];
                    td.appendChild(document.createTextNode(value));
                }
                
                function timespanRenderer(td, stats, value, def, config)
                {
                    if (!value) value = 0;
                    value = Math.round(value)
                    out = (value % 60) + "s";
                    value = Math.floor(value / 60);
                    if (value) out = (value % 60) + "m, " + out;
                    value = Math.floor(value / 60);
                    if (value) out = (value % 24) + "h, " + out;
                    value = Math.floor(value / 24);
                    if (value) out = (value % 30) + "D, " + out;
                    value = Math.floor(value / 30);
                    if (value) out = (value % 12) + "M, " + out;
                    value = Math.floor(value / 12);
                    if (value) out = value + "Y, " + out;
                    td.appendChild(document.createTextNode(out));
                }
                
                function timestampRenderer(td, stats, value, def, config)
                {
                    var out;
                    if (!config["default"]) config["default"] = "Unknown";
                    if (!value) out = config["default"];
                    else
                    {
                        var d = new Date(value * 1000);
                        out = pad(d.getFullYear(), 4) + "-" + pad(d.getMonth() + 1, 2) + "-"
                            + pad(d.getDate(), 2) + " " + pad(d.getHours(), 2) + ":"
                            + pad(d.getMinutes(), 2) + ":" + pad(d.getSeconds(), 2) + "." 
                            + pad(d.getMilliseconds(), 3);
                    }
                    td.appendChild(document.createTextNode(out));
                }
                
                function pad(value, length)
                {
                    value = String(value);
                    while (value.length < length) value = "0" + value;
                    return value;
                }
                
            }, { "cache": "none" });
        }
    }

};
