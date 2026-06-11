import logging
from argparse import ArgumentParser, Namespace
from pathlib import Path

from openai.types.chat import ChatCompletion

from chatvis.documents.code_generation import CODE_GENERATION_PROMPTS
from chatvis.documents.prompt_generation import PROMPT_GENERATION_PROMPTS
from chatvis.llm import OpenAIModel, parse_response
from chatvis.logger import configure_logging

MODELS: list[str] = ["gpt4o"]
LOG_LEVELS: list[str] = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
SCENARIOS: list[str] = [
    "ml-dvr",
    "ml-iso",
    "ml-slice-iso",
    "points-surf-clip",
    "stream-glyph",
]


def cli_parser() -> Namespace:
    parser: ArgumentParser = ArgumentParser(
        prog="chatvis",
        description="Automating Scientific Visualization with a Large Language Model",
        epilog="https://doi.org/10.1109/SCW63240.2024.00014",
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default=SCENARIOS[0],
        help="ChatVis paper scenario to execute (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        choices=MODELS,
        default=MODELS[0],
        help="LLM to leverage (default: %(default)s)",
    )
    parser.add_argument(
        "--username",
        type=str,
        required=True,
        help="Argonne National Labs username",
    )
    parser.add_argument(
        "--log-file",
        action="store_true",
        help="Also write log output to <cwd>/chatvis_<unix-seconds>.log",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default=LOG_LEVELS[0],
        help="Logging verbosity (default: %(default)s)",
    )

    return parser.parse_args()


def connect_to_argo(
    anl_username: str,
    model_name: str = "gpt4o",
) -> OpenAIModel:
    # Setup object
    model: OpenAIModel = OpenAIModel(
        anl_username=anl_username,
        model_name=model_name,
    )

    # Test connection
    resp: ChatCompletion = model.chat(
        system_prompt='Respond with "Hello World"',
        user_prompt="Hello",
    )
    if parse_response(response=resp) != "Hello World":
        raise IOError("LLM did not respond with the correct handshake")

    return model


def main() -> None:
    # Parse command line
    cli_args: Namespace = cli_parser()

    # Setup logger
    log_path: Path | None = configure_logging(
        log_to_file=cli_args.log_file,
        level=logging.getLevelNamesMapping()[cli_args.log_level],
    )
    if log_path is not None:
        logging.getLogger("chatvis").info("logging to %s", log_path)

    # Connect to Argo
    model: OpenAIModel = connect_to_argo(cli_args.username, cli_args.model)

    # match cli_args.scenario:
    #     case "ml-dvr":
    #         raise NotImplementedError("scenario 'ml-dvr' is not yet implemented")
    #     case "ml-iso":
    #         raise NotImplementedError("scenario 'ml-iso' is not yet implemented")
    #     case "ml-slice-iso":
    #         raise NotImplementedError("scenario 'ml-slice-iso' is not yet implemented")
    #     case "points-surf-clip":
    #         raise NotImplementedError(
    #             "scenario 'points-surf-clip' is not yet implemented"
    #         )
    #     case "stream-glyph":
    #         raise NotImplementedError("scenario 'stream-glyph' is not yet implemented")


if __name__ == "__main__":
    main()
