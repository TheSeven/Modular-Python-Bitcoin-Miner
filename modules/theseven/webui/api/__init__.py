from . import init
from . import gadgethost

handlermap = {
  "/api/init/init": init.init,
  "/api/gadgethost/getgadgets": gadgethost.getgadgets,
}
