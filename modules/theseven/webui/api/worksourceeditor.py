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
def getworksourceclasses(core, webui, httprequest, path, request, privileges):
  return [{"id": c.id, "version": c.version, "is_group": c.is_group} for c in core.worksourceclasses]

  

@jsonapi
def getworksources(core, webui, httprequest, path, request, privileges):
  def format_work_source(worksource):
    data = {"id": worksource.id, "name": worksource.settings.name,
            "class": worksource.__class__.id, "is_group": worksource.is_group}
    if worksource.is_group: data["children"] = [format_work_source(c) for c in worksource.children]
    else:
      blockchain = worksource.get_blockchain()
      data["blockchain"] = blockchain.id if blockchain else 0
    return data
  return format_work_source(core.get_root_work_source())

  
  
@jsonapi
def createworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksourceclass = core.registry.get(request["class"])
    parent = core.registry.get(request["parent"])
    worksource = worksourceclass(core)
    parent.add_work_source(worksource)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    if worksource.is_group:
      with worksource.childlock:
        for child in worksource.children:
          worksource.remove_work_source(child)
          child.destroy()
    worksource.get_parent().remove_work_source(worksource)
    worksource.destroy()
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def moveworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    parent = core.registry.get(request["parent"])
    parent.add_work_source(worksource)
    return {}
  except: return {"error": traceback.format_exc()}

  
  
@jsonapi
def getblockchains(core, webui, httprequest, path, request, privileges):
  return [{"id": b.id, "name": b.settings.name} for b in core.blockchains]

  
  
@jsonapi
def setblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    try: blockchain = core.registry.get(request["blockchain"])
    except: blockchain = None
    worksource.set_blockchain(blockchain)
    return {}
  except: return {"error": traceback.format_exc()}
  
  
  
@jsonapi
def restartworksource(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    worksource = core.registry.get(request["id"])
    worksource.restart()
    return {}
  except: return {"error": traceback.format_exc()}
  