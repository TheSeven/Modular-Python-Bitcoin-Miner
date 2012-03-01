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



from ..decorators import jsonapi
import json
try: from queue import Queue
except: from Queue import Queue



@jsonapi
def stream(core, webui, httprequest, path, request, privileges):
  # Figure out the loglevel, by default send all messages
  loglevel = int(request["loglevel"]) if "loglevel" in request else 1000

  # Stream this by means of a chunked transfer
  httprequest.protocol_version = "HTTP/1.1"
  httprequest.log_request(200, "<chunked>")
  httprequest.send_response(200)
  httprequest.send_header("Content-Type", "application/json")
  httprequest.send_header("Transfer-Encoding", "chunked")
  httprequest.end_headers()

  def write_chunk(data):
    data = data.encode("utf_8")
    httprequest.wfile.write(("%X\r\n" % len(data)).encode("ascii") + data + "\r\n".encode("ascii"))
    httprequest.wfile.flush()

  queue = Queue()
    
  try:
    # Register our log message queue
    webui.register_log_listener(queue)
    
    while True:
      # Wait for data to turn up in the queue
      message = queue.get()
      messages = [message] if message["loglevel"] <= loglevel else []
      # If there's more in the queue, fetch that as well
      while True:
        try: message = queue.get_nowait()
        except: break
        if message["loglevel"] <= loglevel: messages.append(message)
      # Send the messages that we got to the client
      write_chunk(json.dumps(messages, ensure_ascii = False) + "\0")
      
  except: pass
  finally: webui.unregister_log_listener(queue)
