"""Load the ParaView operations corpus.

Side effects on import: opens and JSON-parses ``operations.json``. Deviates
from upstream by reading the file from the v2 package directory rather than
from the caller's CWD; values loaded are otherwise identical.
"""

import json
from pathlib import Path

# Read and parse the JSON file
json_file_path = Path(__file__).parent / "operations.json"
with open(json_file_path, "r") as file:
    operations_json = json.load(file)
