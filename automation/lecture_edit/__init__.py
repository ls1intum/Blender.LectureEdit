from .config import *
from .paths import *
from .scenes import *

def reload():
    import importlib
    import sys
    to_reload = [module for name, module in sys.modules.items() if name.startswith("lecture_edit")]
    for module in to_reload:
        importlib.reload(module)


