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

mod.json = {

    "init": function(callback)
    {
        // Augment the Array prototype to include a function to convert the array into a JSON string
        Array.prototype.toJSONString = function()
        {
            var out = "[";
            var comma;

            // Append a string fragment to the output, preceded by a comma if neccessary
            function append(string)
            {
                if (comma) out += ",";
                out += string;
                comma = true;
            }

            for (var i = 0; i < this.length; i++)
                if (this[i] && typeof this[i].toJSONString === "function") append(this[i].toJSONString());
            else append("null");

            return out + "]";
        };

        // Augment the Boolean prototype to include a function to convert the boolean into a JSON string
        Boolean.prototype.toJSONString = function()
        {
            return String(this);
        };

        // Augment the Date prototype to include a function to convert the date into a JSON string
        Date.prototype.toJSONString = function()
        {
            // Prepend a zero to one-digit numbers
            function pad(number)
            {
                return number < 10 ? "0" + n : n;
            }

            return "\"" + this.getFullYear() + "-" + pad(this.getMonth() + 1) + "-" + pad(this.getDate()) + "T"
            + pad(this.getHours()) + ":" + pad(this.getMinutes()) + ":" + pad(this.getSeconds()) + "\"";
        };

        // Augment the Number prototype to include a function to convert the number into a JSON string
        Number.prototype.toJSONString = function()
        {
            return isFinite(this) ? String(this) : "null";
        };

        // Augment the Object prototype to include a function to convert the object into a JSON string
        Object.prototype.toJSONString = function()
        {
            var out = "{";
            var comma;
            var key;

            // Append a string fragment to the output, preceded by the key and a comma if neccessary
            function append(string)
            {
                if (comma) out += ",";
                out += key.toJSONString() + ":" + string;
                comma = true;
            }

            for (key in this)
                if (this.hasOwnProperty(key))
            {
                if (this[key] && typeof this[key].toJSONString === "function") append(this[key].toJSONString());
                else append("null");
            }

            return out + "}";
        };


        // Augment the String prototype to include a function to convert the string into a JSON string
        String.prototype.toJSONString = function()
        {
            // Conversion table for control characters
            var conv = { "\b": "\\b", "\t": "\\t", "\n": "\\n", "\f": "\\f", "\r": "\\r", "\"": "\\\"", "\\": "\\\\" };

            if (/["\\\x00-\x1f]/.test(this))
            {
                return "\"" + this.replace(/([\x00-\x1f\\"])/g, function(dummy, b)
                {
                    if (conv[b]) return conv[b];
                    return "\\u00" + Math.floor(b.charCodeAt() / 16).toString(16) + (b.charCodeAt() % 16).toString(16);
                }) + "\"";
            }

            return "\"" + this + "\"";
        };

        // Augment the String prototype to include a function to decode a JSON string
        String.prototype.decodeJSON = function()
        {
            try
            {
                return eval("(" + this + ")");
            }
            catch (e)
            {
                throw ("json: Got some junk. Error: " + e.toString() + "\n\nData:\n" + this);
            }
        };

        // Emulate native JSON for pre-ECMAScript 3.1 browsers
        if (!window.JSON)
            window.JSON = {
                "parse": function(data)
                {
                    return data.decodeJSON();
                },
                "stringify": function(data)
                {
                    return data.toJSONString();
                }
            };

        // Report successful initialisation of the module
        callback();
    }

};