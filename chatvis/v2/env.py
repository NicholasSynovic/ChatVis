"""PATH munging for pvpython.

Side effects on import: mutates ``os.environ['PATH']`` and prints
``PATH_TO_PVPYTHON``. Faithful port of the top of ``run_all.py``/``run_one.py``;
the literal ``":$PATH"`` append (no shell expansion) is preserved as upstream.
"""

import os

# Path to pvpython
PATH_TO_PVPYTHON = os.getenv("PATH_TO_PVPYTHON")
path_to_pvpython = PATH_TO_PVPYTHON + ":$PATH"
print("path to pvpython", PATH_TO_PVPYTHON)
os.environ["PATH"] += os.pathsep + path_to_pvpython
