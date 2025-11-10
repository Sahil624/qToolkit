try:
    from ._version import __version__
except ImportError:
    # Fallback when using the package in dev mode without installing
    # in editable mode with pip. It is highly recommended to install
    # the package from a stable release or in editable mode: https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs
    import warnings
    warnings.warn("Importing 'edu_agents' outside a proper installation.")
    __version__ = "dev"
from .handlers import setup_handlers
from jupyter_server.serverapp import ServerApp


def _jupyter_labextension_paths():
    return [{
        "src": "labextension",
        "dest": "edu_agents"
    }]


def _jupyter_server_extension_points():
    return [{
        "module": "edu_agents"
    }]


def _load_jupyter_server_extension(server_app: ServerApp):
    """Registers the API handler to receive HTTP requests from the frontend extension.

    Parameters
    ----------
    server_app: jupyterlab.labapp.LabApp
        JupyterLab application instance
    """
    print("========== Loading edu_agents server extension ========")
    print(type(server_app))
    setup_handlers(server_app.web_app)
    name = "edu_agents"
    server_app.log.info(f"Registered {name} server extension")

# Import the function itself (not the decorated version)
from .course_completed import course_completed 

def load_ipython_extension(ipython):
    ipython.register_magic_function(course_completed, 'cell', 'course_completed')

def unload_ipython_extension(ipython):
    pass