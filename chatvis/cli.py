import shutil
from argparse import ArgumentParser, Namespace
from pathlib import Path

from chatvis import __prog__, __version__

MODELS: list[str] = ["gpt4o"]
LOG_LEVELS: list[str] = ["debug", "info", "warning", "error", "critical"]
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_ENDPOINT: str = "https://apps.inside.anl.gov/argoapi/v1"
DEFAULT_MAX_REPAIR_ATTEMPTS: int = 5
SCENARIOS: list[str] = [
    "ml-dvr",
    "ml-iso",
    "ml-slice-iso",
    "points-surf-clip",
    "stream-glyph",
]

# v2 RAG defaults. The FAISS index and metadata-lookup pickle default to
# files named faiss.index / metadata_lookup.pickle in the current working
# directory, matching CodeEmbeddings' own relative-path defaults in
# chatvis/v2/documents/code.py. The top-k default mirrors
# CodeEmbeddings(top_k_results=...) so the CLI and library agree.
DEFAULT_TOP_K: int = 5
DEFAULT_FAISS_INDEX: Path = Path("faiss.index")
DEFAULT_METADATA_LOOKUP: Path = Path("metadata_lookup.pickle")


def _default_pvpython() -> Path | None:
    found: str | None = shutil.which("pvpython")
    return Path(found) if found is not None else None


def _add_scenario_data_group(parser: ArgumentParser) -> None:
    """Add the shared scenario/data flags used by both v1 and v2.

    Both subcommands take the same scenario selection plus the dataset
    and screenshot paths; keeping the definitions in one place stops the
    two parsers from drifting apart.
    """
    group = parser.add_argument_group("Scenario & Data Options")
    group.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default=SCENARIOS[0],
        help="ChatVis paper scenario to execute (default: %(default)s)",
    )
    group.add_argument(
        "--data-filepath",
        type=lambda x: Path(x).absolute(),
        required=True,
        help="Path to data file to evaluate",
    )
    group.add_argument(
        "--screenshot-path",
        type=lambda x: Path(x).absolute(),
        required=True,
        help="Path where the generated ParaView screenshot should be written",
    )


def _add_execution_group(parser: ArgumentParser) -> None:
    """Add the shared repair-loop flag used by both v1 and v2."""
    group = parser.add_argument_group("Execution Options")
    group.add_argument(
        "--max-repair-attempts",
        type=int,
        default=DEFAULT_MAX_REPAIR_ATTEMPTS,
        help=(
            "Maximum number of code-improvement iterations after the "
            "initial code-generation attempt (default: %(default)s)"
        ),
    )


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

        # ----- Globals (apply to every subcommand) -----

        # --- Group: Global Options ---
        # Using a custom group for version ensures it isn't lost under the
        # default "options" catch-all block.
        global_group = ap.add_argument_group("Global Options")
        global_group.add_argument(
            "-V",
            "--version",
            action="version",
            version=f"%(prog)s {__version__}",
            help="Show the application version and exit",
        )

        # --- Group: Execution Options ---
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

        # --- Group: LLM & Authentication Options ---
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

        # --- Group: Logging Options ---
        logging_group = ap.add_argument_group("Logging Options")
        logging_group.add_argument(
            "--log-file",
            action="store_true",
            help="Write log output to <cwd>/chatvis_<unix-seconds>.log",
        )
        logging_group.add_argument(
            "--log-level",
            choices=LOG_LEVELS,
            default=DEFAULT_LOG_LEVEL,
            help="Logging verbosity (default: %(default)s)",
        )

        # ----- Subcommands -----
        subparsers = ap.add_subparsers(
            dest="subcommand",
            required=True,
            metavar="{v1,v2}",
            title="Subcommands",
        )

        # ----- v1 subcommand -----
        v1 = subparsers.add_parser(
            "v1",
            help="Run the v1 single-scenario pipeline",
            description=(
                "Run the v1 single-scenario pipeline (prompt improvement -> "
                "code generation -> pvpython -> bounded repair loop)."
            ),
        )

        # --- v1 Group: Scenario & Data Options ---
        _add_scenario_data_group(v1)

        # --- v1 Group: Execution Options ---
        _add_execution_group(v1)

        # ----- v2 subcommand -----
        v2 = subparsers.add_parser(
            "v2",
            help="Run the v2 RAG-based pipeline",
            description=(
                "Run the v2 RAG-based pipeline (prompt-driven FAISS "
                "retrieval -> code generation -> pvpython -> bounded repair "
                "loop). The FAISS index and metadata lookup are built on "
                "demand when the configured paths do not exist."
            ),
        )

        # --- v2 Group: Scenario & Data Options ---
        _add_scenario_data_group(v2)

        # --- v2 Group: RAG Options ---
        v2_rag_group = v2.add_argument_group("RAG Options")
        v2_rag_group.add_argument(
            "--faiss-index",
            type=lambda x: Path(x).absolute(),
            default=DEFAULT_FAISS_INDEX,
            help=(
                "Path to the FAISS index of ParaView code snippets "
                "(default: %(default)s)"
            ),
        )
        v2_rag_group.add_argument(
            "--metadata-lookup",
            type=lambda x: Path(x).absolute(),
            default=DEFAULT_METADATA_LOOKUP,
            help=(
                "Path to the pickled snippet metadata lookup paired with "
                "the FAISS index (default: %(default)s)"
            ),
        )
        v2_rag_group.add_argument(
            "--top-k",
            type=int,
            default=DEFAULT_TOP_K,
            help=(
                "Number of code snippets to retrieve from the FAISS index "
                "per query (default: %(default)s)"
            ),
        )

        # --- v2 Group: Execution Options ---
        _add_execution_group(v2)

        return ap.parse_args()
