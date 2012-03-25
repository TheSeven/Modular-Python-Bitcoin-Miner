# Modular Python Bitcoin Miner
# Copyright (C) 2012 Michael Sparmann (TheSeven)
#
#     This program is free software; you can redistribute it and/or
#     modify it under the terms of the GNU General Public License
#     as published by the Free Software Foundation; either version 2
#     of the License, or (at your option) any later version.
#
#     This program is distributed in the hope that it will be useful,
#     but WITHOUT ANY WARRANTY; without even the implied warranty of
#     MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#     GNU General Public License for more details.
#
#     You should have received a copy of the GNU General Public License
#     along with this program; if not, write to the Free Software
#     Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# Please consider donating to 1PLAPWDejJPJnY2ppYCgtw5ko8G5Q4hPzh if you
# want to support further development of the Modular Python Bitcoin Miner.



##########################################################################
# Web-based status and configuration user interface, offering a JSON API #
##########################################################################



import os
import time
import shutil
import base64
from threading import RLock, Thread
from core.basefrontend import BaseFrontend
from .api import handlermap
try: import urllib.parse as urllib
except: import urllib
try: from socketserver import ThreadingTCPServer
except: from SocketServer import ThreadingTCPServer
try: from http.server import BaseHTTPRequestHandler
except: from BaseHTTPServer import BaseHTTPRequestHandler



class WebUI(BaseFrontend):

  version = "theseven.webui v0.1.0beta"
  default_name = "WebUI"
  can_log = True
  can_configure = True
  can_autodetect = True
  settings = dict(BaseFrontend.settings, **{
    "port": {"title": "HTTP port", "type": "int", "position": 1000},
    "users": {
      "title": "Users",
      "type": "dict",
      "key": {"title": "User:Password", "type": "string"},
      "value": {
        "title": "Privilege level",
        "type": "enum",
        "values": [
          {"value": "readonly", "title": "Read only access"},
          {"value": "admin", "title": "Full access"},
        ],
      },
      "position": 2000
    },
    "log_buffer_max_length": {"title": "Maximum log buffer length", "type": "int", "position": 3000},
    "log_buffer_purge_size": {"title": "Log buffer purge size", "type": "int", "position": 3010},
  })


  @classmethod
  def autodetect(self, core):
    core.add_frontend(self(core))


  def __init__(self, core, state = None):
    super(WebUI, self).__init__(core, state)
    self.log_lock = RLock()


  def apply_settings(self):
    super(WebUI, self).apply_settings()
    if not "port" in self.settings: self.settings.port = 8832
    if not "users" in self.settings: self.settings.users = {"admin:mpbm": "admin"}
    if not "uiconfig" in self.settings: self.settings.uiconfig = {"loggadget": {"loglevel": self.core.default_loglevel}}
    if not "log_buffer_max_length" in self.settings: self.settings.log_buffer_max_length = 1000
    if not "log_buffer_purge_size" in self.settings: self.settings.log_buffer_purge_size = 100
    if self.started and self.settings.port != self.port: self.async_restart(3)
    
    
  def _reset(self):
    self.log_buffer = []
    self.log_listeners = []

    
  def _start(self):
    super(WebUI, self)._start()
    self.httpd = ThreadingTCPServer(("", self.settings.port), RequestHandler, False)
    self.httpd.webui = self
    self.httpd.allow_reuse_address = 1
    self.httpd.server_bind()
    self.httpd.server_activate()
    self.serverthread = Thread(None, self.httpd.serve_forever, self.settings.name + "_httpd")
    self.serverthread.daemon = True
    self.serverthread.start()
    self.port = self.settings.port


  def _stop(self):
    self.httpd.shutdown()
    self.serverthread.join(10)
    self.httpd.server_close()
    super(WebUI, self)._stop()


  def write_log_message(self, timestamp, loglevel, messages):
    if not self.started: return
    data = {
      "timestamp": time.mktime(timestamp.timetuple()) * 1000 + timestamp.microsecond / 1000,
      "loglevel": loglevel,
      "message": [{"data": data, "format": format} for data, format in messages],
    }
    with self.log_lock:
      for queue in self.log_listeners:
        queue.put(data)
      self.log_buffer.append(data)
      if len(self.log_buffer) > self.settings.log_buffer_max_length:
        self.log_buffer = self.log_buffer[self.settings.log_buffer_purge_size:]
        
        
  def register_log_listener(self, listener):
    with self.log_lock:
      if not listener in self.log_listeners:
        self.log_listeners.append(listener)
      for data in self.log_buffer: listener.put(data)
        
        
  def unregister_log_listener(self, listener):
    with self.log_lock:
      while listener in self.log_listeners:
        self.log_listeners.remove(listener)
        
        

class RequestHandler(BaseHTTPRequestHandler):

  server_version = WebUI.version
  rootfile = "/static/init/init.htm"
  mimetypes = {
    '': 'application/octet-stream',  # Default
    '.htm': 'text/html',
    '.html': 'text/html',
    '.png': 'image/png',
    '.gif': 'image/gif',
    '.js': 'text/javascript',
    '.css': 'text/css',
  }

  
  def log_request(self, code = '-', size = '-'):
    if code == 200:
      if size != "-": self.log_message("HTTP request: %s \"%s\" %s %s", self.address_string(), self.requestline, str(code), str(size))
    else: self.log_error("Request failed: %s \"%s\" %s %s", self.address_string(), self.requestline, str(code), str(size))
   
   
  def log_error(self, format, *args):
    webui = self.server.webui
    webui.core.log("%s: %s\n" % (webui.settings.name, format % args), 600, "y")


  def log_message(self, format, *args):
    webui = self.server.webui
    webui.core.log("%s: %s\n" % (webui.settings.name, format % args), 800, "")

    
  def do_HEAD(self):
    # Essentially the same as GET, just without a body
    self.do_GET(False)


  def do_GET(self, send_body = True):
    # Figure out the base path that will be prepended to the requested path
    basepath = os.path.realpath(os.path.join(os.path.dirname(__file__), "wwwroot"))
    # Remove query strings and anchors, and unescape the path
    path = urllib.unquote(self.path.split('?',1)[0].split('#',1)[0])
    # Rewrite requests to "/" to the specified root file
    if path == "/": path = self.__class__.rootfile
    # Paths that don't start with a slash are invalid => 400 Bad Request
    if path[0] != "/": return self.fail(400)
    # Check authentication and figure out privilege level
    privileges = self.check_auth()
    if not privileges:
      # Invalid credentials => 401 Authorization Required
      self.fail(401, [("WWW-Authenticate", "Basic realm=\"MPBM WebUI\"")])
      return None
    # Figure out the actual filesystem path to the requested file
    path = os.path.realpath(os.path.join(basepath, path[1:]))
    # If it tries to escape from the wwwroot directory => 403 Forbidden
    if path[:len(basepath)] != basepath: return self.fail(403)
    # If it simply isn't there => 404 Not Found
    if not os.path.exists(path): return self.fail(404)
    # If it isn't a regular file (but e.g. a directory) => 403 Forbidden
    if not os.path.isfile(path): return self.fail(403)
    # Try to figure out the mime type based on the file name extension
    ext = os.path.splitext(path)[1]
    mimetypes = self.__class__.mimetypes
    if ext in mimetypes: mimetype = mimetypes[ext]
    elif ext.lower() in mimetypes: mimetype = mimetypes[ext.lower()]
    else: mimetype = mimetypes['']
    try:
      f = open(path, "rb")
      # Figure out file size using seek/tell
      f.seek(0, os.SEEK_END)
      length = f.tell()
      f.seek(0, os.SEEK_SET)
      # Send response headers
      self.log_request(200, length)
      self.send_response(200)
      self.send_header("Content-Type", mimetype)
      self.send_header("Content-Length", length)
      self.end_headers()
      # Send file data to the client, if this isn't a HEAD request
      if send_body: shutil.copyfileobj(f, self.wfile, length)
    # Something went wrong, no matter what => 500 Internal Server Error
    except: self.fail(500)
    finally:
      try: f.close()
      except: pass

      
  def do_POST(self):
    # Remove query strings and anchors, and unescape the path
    path = urllib.unquote(self.path.split('?',1)[0].split('#',1)[0])
    # Paths that don't start with a slash are invalid => 400 Bad Request
    if path[0] != "/": return self.fail(400)
    # Check authentication and figure out privilege level
    privileges = self.check_auth()
    if not privileges:
      # Invalid credentials => 401 Authorization Required
      self.fail(401)
      self.send_header("WWW-Authenticate", "Basic realm=\"MPBM WebUI\"")
      return None
    # Look for a handler for that path and execute it if present
    if path in handlermap:
      handlermap[path](self.server.webui.core, self.server.webui, self, path, privileges)
    # No handler for that path found => 404 Not Found
    else: self.fail(404)

    
  def check_auth(self):
    # Check authentication and figure out privilege level
    authdata = self.headers.get("authorization", None)
    credentials = ""
    if authdata != None: 
      authdata = authdata.split(" ", 1)
      if authdata[0].lower() == "basic":
        try: credentials = base64.b64decode(authdata[1].encode("ascii")).decode("utf_8")
        except: pass
    privileges = None
    if credentials in self.server.webui.settings.users:
      privileges = self.server.webui.settings.users[credentials]
    return privileges

  
  def fail(self, status, headers = []):
    self.send_response(status)
    for header in headers:
      self.send_header(*header)
    self.send_header("Content-Length", 0)
    self.end_headers()
