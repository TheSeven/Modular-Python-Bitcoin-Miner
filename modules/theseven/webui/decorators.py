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



import json
import traceback



class jsonapi(object):


  def __init__(self, f):
    self.f = f

    
  def __call__(self, core, webui, httprequest, path, privileges):
    try:
      # We only accept JSON. If this is something different => 400 Bad Request
      if httprequest.headers.get("content-type", None) not in ("application/json", "application/json; charset=UTF-8"):
        return httprequest.send_response(400)
      length = int(httprequest.headers.get("content-length"))
      # Read request from the connection
      data = b""
      while len(data) < length: data += httprequest.rfile.read(length - len(data))
      # Decode the request
      data = json.loads(data.decode("utf_8"))
      # Run the API function
      data = self.f(core, webui, httprequest, path, data, privileges)
      if data == None: return
      # Encode the response
      data = json.dumps(data, ensure_ascii = False, default = lambda obj: None).encode("utf_8")
      # Send response headers
      httprequest.log_request(200, len(data))
      httprequest.send_response(200)
      httprequest.send_header("Content-Type", "application/json; charset=UTF-8")
      httprequest.send_header("Content-Length", len(data))
      httprequest.end_headers()
      httprequest.wfile.write(data)
    # Something went wrong, no matter what => 500 Internal Server Error
    except:
      core.log("Exception while handling API call: %s\n" % traceback.format_exc(), 700, "y")
      try: httprequest.send_response(500)
      except: pass
