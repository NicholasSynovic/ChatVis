import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

from chatvis import __prog__, __version__

MODELS: list[str] = ["gpt4o"]
LOG_LEVELS: list[str] = ["debug", "info", "warning", "error", "critical"]
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_ENDPOINT: str = "https://apps.inside.anl.gov/argoapi/v1"
DEFAULT_MAX_REPAIR_ATTEMPTS: int = 5
SCENARIOS: list[str] = [  # Todo: Conver these into an Enum
    "ml-dvr",
    "ml-iso",
    "ml-slice-iso",
    "points-surf-clip",
    "stream-glyph",
]


def _default_pvpython() -> Path | None:
    found: str | None = shutil.which("pvpython")
    return Path(found) if found is not None else None


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

        # --- Group 3: Execution Options ---
        execution_group = ap.add_argument_group("Execution Options")
        execution_group.add_argument(
            "--pvpython",
            type=lambda x: Path(x).absolute(),
            default=_default_pvpython(),
            help=(
                "Path to the pvpython executable used to run generated "
                "ParaView scripts (default: first pvpython on PATH)"
            ),
        )
        execution_group.add_argument(
            "--max-repair-attempts",
            type=int,
            default=DEFAULT_MAX_REPAIR_ATTEMPTS,
            help=(
                "Maximum number of code-improvement iterations after the "
                "initial code-generation attempt (default: %(default)s)"
            ),
        )

        # --- Group 4: Logging Options ---
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

        # --- Group 5: Global Options ---
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
