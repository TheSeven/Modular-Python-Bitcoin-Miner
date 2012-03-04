from . import init
from . import gadgethost
from . import log
from . import uiconfig
from . import frontendeditor
from . import worksourceeditor
from . import settingseditor

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
  "/api/worksourceeditor/getworksourceclasses": worksourceeditor.getworksourceclasses,
  "/api/worksourceeditor/getworksources": worksourceeditor.getworksources,
  "/api/worksourceeditor/createworksource": worksourceeditor.createworksource,
  "/api/worksourceeditor/deleteworksource": worksourceeditor.deleteworksource,
  "/api/worksourceeditor/moveworksource": worksourceeditor.moveworksource,
  "/api/settingseditor/readsettings": settingseditor.readsettings,
  "/api/settingseditor/writesettings": settingseditor.writesettings,
}
