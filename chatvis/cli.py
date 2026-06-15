from argparse import ArgumentParser, Namespace
from pathlib import Path

from chatvis import __prog__, __version__

MODELS: list[str] = ["gpt4o"]
LOG_LEVELS: list[str] = ["debug", "info", "warning", "error", "critical"]
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_ENDPOINT: str = "https://apps.inside.anl.gov/argoapi/v1"
SCENARIOS: list[str] = [  # Todo: Conver these into an Enum
    "ml-dvr",
    "ml-iso",
    "ml-slice-iso",
    "points-surf-clip",
    "stream-glyph",
]


class CLI:
    def __init__(self) -> None:
        self.prog: str = __prog__
        self.description: str = (
            "Automating Scientific Visualization with a Large Language Model"
        )
        self.epilog: str = "DOI: https://doi.org/10.1109/SCW63240.2024.00014"

    def parser(self) -> Namespace:
        ap: ArgumentParser = ArgumentParser(
            prog=self.prog,
            description=self.description,
            epilog=self.epilog,
        )

        # --- Group 1: Scenario & Data Options ---
        data_group = ap.add_argument_group("Scenario & Data Options")
        data_group.add_argument(
            "--scenario",
            choices=SCENARIOS,
            default=SCENARIOS[0],
            help="ChatVis paper scenario to execute (default: %(default)s)",
        )
        data_group.add_argument(
            "--data-filepath",
            type=lambda x: Path(x).absolute(),
            required=True,
            help="Path to data file to evaluate",
        )
        data_group.add_argument(
            "--screenshot-path",
            type=lambda x: Path(x).absolute(),
            required=True,
            help="Path where the generated ParaView screenshot should be written",
        )

        # --- Group 2: LLM & Authentication Options ---
        llm_group = ap.add_argument_group("LLM & Authentication Options")
        llm_group.add_argument(
            "--model",
            choices=MODELS,
            default=MODELS[0],
            help="LLM to leverage (default: %(default)s)",
        )
        llm_group.add_argument(
            "--username",
            type=str,
            required=True,
            help="Argonne National Labs username",
        )
        llm_group.add_argument(
            "--endpoint",
            type=str,
            default=DEFAULT_ENDPOINT,
            help="LLM API endpoint URL (default: %(default)s)",
        )

        # --- Group 3: Logging Options ---
        logging_group = ap.add_argument_group("Logging Options")
        logging_group.add_argument(
            "--log-file",
            action="store_true",
            help="Also write log output to <cwd>/chatvis_<unix-seconds>.log",
        )
        logging_group.add_argument(
            "--log-level",
            choices=LOG_LEVELS,
            default=DEFAULT_LOG_LEVEL,
            help="Logging verbosity (default: %(default)s)",
        )

        # --- Group 4: Global Options ---
        # Note: Using a custom group for version ensures it isn't lost
        # under the default "options" catch-all block.
        global_group = ap.add_argument_group("Global Options")
        global_group.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
            help="Show the application version and exit",
        )

        return ap.parse_args()
