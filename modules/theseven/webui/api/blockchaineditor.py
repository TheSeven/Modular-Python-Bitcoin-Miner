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
def getblockchains(core, webui, httprequest, path, request, privileges):
  return [{"id": b.id, "name": b.settings.name} for b in core.blockchains]

  

@jsonapi
def createblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    name = request["name"]
    from core.blockchain import Blockchain
    blockchain = Blockchain(core)
    blockchain.settings.name = name
    blockchain.apply_settings()
    core.add_blockchain(blockchain)
    return {}
  except: return {"error": traceback.format_exc()}

  

@jsonapi
def deleteblockchain(core, webui, httprequest, path, request, privileges):
  if privileges != "admin": return httprequest.send_response(403)
  try:
    blockchain = core.registry.get(request["id"])
    core.remove_blockchain(blockchain)
    blockchain.destroy()
    return {}
  except: return {"error": traceback.format_exc()}
