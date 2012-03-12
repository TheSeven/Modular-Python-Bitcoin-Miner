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
import traceback



@jsonapi
def getworkerclasses(core, webui, httprequest, path, request, privileges):
  return [{"id": c.id, "version": c.version} for c in core.workerclasses]

  

@jsonapi
def getworkers(core, webui, httprequest, path, request, privileges):
  return [{"id": w.id, "name": w.settings.name, "class": w.__class__.id} for w in core.workers]

  

@jsonapi
def createworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    workerclass = core.registry.get(request["class"])
    worker = workerclass(core)
    core.add_worker(worker)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worker = core.registry.get(request["id"])
    core.remove_worker(worker)
    worker.destroy()
    return {}
  except: return {"error": traceback.format_exc()}
  
  
  
@jsonapi
def restartworker(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worker = core.registry.get(request["id"])
    worker.restart()
    return {}
  except: return {"error": traceback.format_exc()}
  