import os
import importlib.util
from config import PLUGIN_FOLDER


def find_plugins(subfolder: str):
    """
    List all plugin module names (without .py) in given subfolder.
    """
    path = os.path.join(PLUGIN_FOLDER, subfolder)
    return [f[:-3] for f in os.listdir(path)
            if f.endswith('.py') and not f.startswith('__')]


def load_plugin(subfolder: str, name: str):
    """
    Dynamically import and return module named `name` from subfolder.
    """
    module_path = os.path.join(PLUGIN_FOLDER, subfolder, f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module