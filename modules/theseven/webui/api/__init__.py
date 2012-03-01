from . import init
from . import gadgethost
from . import log

handlermap = {
  "/api/init/init": init.init,
  "/api/gadgethost/getgadgets": gadgethost.getgadgets,
  "/api/log/stream": log.stream,
}
