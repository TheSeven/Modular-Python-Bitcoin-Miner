from . import init
from . import gadgethost
from . import log
from . import uiconfig

handlermap = {
  "/api/init/init": init.init,
  "/api/gadgethost/getgadgets": gadgethost.getgadgets,
  "/api/log/stream": log.stream,
  "/api/uiconfig/read": uiconfig.read,
  "/api/uiconfig/write": uiconfig.write,
}
