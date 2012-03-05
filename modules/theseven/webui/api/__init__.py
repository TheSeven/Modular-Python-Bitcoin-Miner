from . import init
from . import gadgethost
from . import log
from . import uiconfig
from . import frontendeditor
from . import workereditor
from . import worksourceeditor
from . import settingseditor
from . import menugadget

handlermap = {
  "/api/init/init": init.init,
  "/api/gadgethost/getgadgets": gadgethost.getgadgets,
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
  "/api/settingseditor/readsettings": settingseditor.readsettings,
  "/api/settingseditor/writesettings": settingseditor.writesettings,
  "/api/menugadget/saveconfiguration": menugadget.saveconfiguration,
}
