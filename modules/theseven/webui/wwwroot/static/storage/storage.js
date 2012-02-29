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

mod.storage = {

    "write": function(name, value, session, time, allowCookie)
    {
        var store;
        if (session) store = sessionStorage;
        else if (window.localStorage) store = localStorage;
        else if (window.globalStorage) store = globalStorage[location.hostname];
        if (store)
        {
            try
            {
                store.setItem(name, value);
                if (time) store.setItem("storage_expires_" + name, new Date(new Date().getTime() + time).getTime());
                return true;
            }
            catch (e)
            {
                error(nls("Locally storing some data failed, probably because of an exceeded quota.\n"
                        + "Please allow more storage space for this site in your browser settings.\nDetails:\n") + e);
                return false;
            }
        }
        else
        {
            if (allowCookie)
            {
                var expires = "";
                if (!session) expires = "Tue, 19 Jan 2038 03:14:07 GMT";
                if (time) expires = "; expires=" + new Date(new Date().getTime() + time).toGMTString();
                document.cookie = escape(name) + "=" + escape(value) + expires;
                if (mod.storage.read(name) != value)
                {
                    error(nls("Locally storing some data failed, because no supported storage mechanism worked.\n"
                            + "Please update to a more recent browser and/or enable DOM storage in your browser settings to resolve this issue."));
                    return false;
                }
            }
/*
            notify(nls("Warning: Incompatible browser"),
                   nls("You may experience some issues, because your browser does not seem to support current client-side storage mechanisms.\n"
                     + "Please update to a more recent browser and/or enable DOM storage in your browser settings to resolve this issue."));
*/
            return allowCookie;
        }
    },

    "read": function(name)
    {
        if (window.sessionStorage && sessionStorage.getItem(name) && (!sessionStorage.getItem("storage_expires_" + name)
                                                             || sessionStorage.getItem("storage_expires_" + name) > new Date().getTime()))
            return sessionStorage.getItem(name);
        if (window.localStorage && localStorage[name] && (!localStorage.getItem("storage_expires_" + name)
                                                             || localStorage.getItem("storage_expires_" + name) > new Date().getTime()))
            return localStorage.getItem(name);
        if (window.globalStorage && globalStorage[location.hostname] && globalStorage[location.hostname].getItem(name)
            && (!globalStorage[location.hostname].getItem("storage_expires_" + name)
                || globalStorage[location.hostname].getItem("storage_expires_" + name) > new Date().getTime()))
            return globalStorage[location.hostname].getItem(name);
        var name = escape(name) + "=";
        var cookies = document.cookie.split(";");
        for (var i = 0; i < cookies.length; i++)
        {
            while (cookies[i].charAt(0) == " ") cookies[i] = cookies[i].substr(1, cookies[i].length - 1);
            if (cookies[i].indexOf(name) == 0)
                return unescape(cookies[i].substring(name.length, cookies[i].length));
        }
    },

    "erase": function(name)
    {
        if (window.sessionStorage) sessionStorage.removeItem(name);
        if (window.localStorage) localStorage.removeItem(name);
        if (window.globalStorage && globalStorage[location.hostname]) globalStorage[location.hostname].removeItem(name);
        document.cookie = escape(name) + "=; expires=Thu, 01 Jan 1970 00:00:00 GMT";
    }

};
