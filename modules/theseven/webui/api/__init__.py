from . import init
from . import gadgethost
from . import menugadget
from . import log
from . import uiconfig
from . import frontendeditor
from . import workereditor
from . import worksourceeditor
from . import blockchaineditor
from . import settingseditor
from . import debug

handlermap = {
  "/api/init/init": init.init,
  "/api/gadgethost/getgadgets": gadgethost.getgadgets,
  "/api/menugadget/saveconfiguration": menugadget.saveconfiguration,
  "/api/log/stream": log.stream,
  "/api/uiconfig/read": uiconfig.read,
  "/api/uiconfig/write": uiconfig.write,
  "/api/frontendeditor/getfrontendclasses": frontendeditor.getfrontendclasses,
  "/api/frontendeditor/getfrontends": frontendeditor.getfrontends,
  "/api/frontendeditor/createfrontend": frontendeditor.createfrontend,
  "/api/frontendeditor/deletefrontend": frontendeditor.deletefrontend,
  "/api/workereditor/getworkerclasses": workereditor.getworkerclasses,
  "/api/workereditor/getworkers": workereditor.getworkers,
  "/api/workereditor/createworker": workereditor.createworker,
  "/api/workereditor/deleteworker": workereditor.deleteworker,
  "/api/worksourceeditor/getworksourceclasses": worksourceeditor.getworksourceclasses,
  "/api/worksourceeditor/getworksources": worksourceeditor.getworksources,
  "/api/worksourceeditor/createworksource": worksourceeditor.createworksource,
  "/api/worksourceeditor/deleteworksource": worksourceeditor.deleteworksource,
  "/api/worksourceeditor/moveworksource": worksourceeditor.moveworksource,
  "/api/worksourceeditor/getblockchains": worksourceeditor.getblockchains,
  "/api/worksourceeditor/setblockchain": worksourceeditor.setblockchain,
  "/api/blockchaineditor/getblockchains": blockchaineditor.getblockchains,
  "/api/blockchaineditor/createblockchain": blockchaineditor.createblockchain,
  "/api/blockchaineditor/deleteblockchain": blockchaineditor.deleteblockchain,
  "/api/settingseditor/readsettings": settingseditor.readsettings,
  "/api/settingseditor/writesettings": settingseditor.writesettings,
  "/api/debug/dumpthreadstates": debug.dumpthreadstates,
}
