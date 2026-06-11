import logging
import sys
from argparse import ArgumentParser, Namespace
from logging import Logger
from pathlib import Path

from openai.types.chat import ChatCompletion

from chatvis.documents.prompt_generation import (
    PROMPT_GENERATION_PROMPTS,
    PromptGenerationPrompt,
)
from chatvis.llm import OpenAIModel, parse_response, prompt_generation
from chatvis.logger import configure_logging

MODELS: list[str] = ["gpt4o"]
LOG_LEVELS: list[str] = ["debug", "info", "warning", "error", "critical"]
DEFAULT_LOG_LEVEL: str = "info"
DEFAULT_ENDPOINT: str = "https://apps.inside.anl.gov/argoapi/v1"
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
        "--data-filepath",
        type=lambda x: Path(x).absolute(),
        required=True,
        help="Path to data file to evaluate",
    )
    parser.add_argument(
        "--screenshot-path",
        type=lambda x: Path(x).absolute(),
        required=True,
        help="Path where the generated ParaView screenshot should be written",
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
        "--endpoint",
        type=str,
        default=DEFAULT_ENDPOINT,
        help="LLM API endpoint URL (default: %(default)s)",
    )
    parser.add_argument(
        "--log-file",
        action="store_true",
        help="Also write log output to <cwd>/chatvis_<unix-seconds>.log",
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default=DEFAULT_LOG_LEVEL,
        help="Logging verbosity (default: %(default)s)",
    )

    return parser.parse_args()


def setup_logger(log_to_file: bool, log_level: str) -> Logger:
    # Configure logger
    log_path: Path | None = configure_logging(
        log_to_file=log_to_file,
        level=logging.getLevelNamesMapping()[log_level.upper()],
    )

    # Get the application logger
    logger: Logger = logging.getLogger("chatvis")

    # Log to file
    if log_path is not None:
        logger.info("Logging to %s", log_path)

    # Return application logger
    return logger


def check_data(data_filepath: Path, scenario: str) -> bool:
    # Check ML scenarios
    if (scenario[0:2] == "ml") and (data_filepath.name == "ml-100.vtk"):
        return True

    # Check Can scenarios
    if ("points" in scenario) and (data_filepath.name == "can_points.ex2"):
        return True

    # Check Disk scenarios
    if ("stream" in scenario) and (data_filepath.name == "disk.ex2"):
        return True

    return False


def connect_to_argo(
    logger: Logger,
    anl_username: str,
    endpoint: str,
    model_name: str = "gpt4o",
) -> OpenAIModel:
    # Setup object
    model: OpenAIModel = OpenAIModel(
        logger=logger,
        api_key=anl_username,
        model_name=model_name,
        endpoint=endpoint,
    )

    # Handshake: any exception from the client OR an empty response is a failure.
    # We do not string-compare LLM output -- it is nondeterministic.
    try:
        resp: ChatCompletion = model.chat(
            system_prompt='Respond with "Hello World"',
            user_prompt="Hello",
        )
    except Exception as exc:
        logger.error("Argo handshake failed: %s", exc)
        raise RuntimeError("Argo handshake call raised an exception") from exc

    content: str = parse_response(response=resp).strip()
    if not content:
        logger.error("Argo handshake returned an empty response")
        raise RuntimeError("Argo handshake returned an empty response")

    return model


def generate_improved_prompt(
    logger: Logger,
    pgp: PromptGenerationPrompt,
    data_filepath: Path,
    screenshot_path: Path,
    llm: OpenAIModel,
) -> str:
    # Fail fast on degraded few-shot examples rather than sending a
    # half-empty prompt to the LLM.
    if not pgp.example_prompt.generated_prompt.strip():
        raise ValueError(
            "PromptGenerationExample.generated_prompt is empty; refusing to "
            "send a degraded few-shot prompt to the LLM"
        )

    resp: ChatCompletion = prompt_generation(
        pgp=pgp,
        openai=llm,
        input_path=data_filepath,
        output_path=screenshot_path,
    )
    content: str = parse_response(response=resp)
    logger.debug("Parsed `Improved Prompt Generation` response: %s", content)
    return content


def main() -> None:
    # Parse command line
    cli_args: Namespace = cli_parser()

    # Setup logger
    logger: Logger = setup_logger(
        log_to_file=cli_args.log_file,
        log_level=cli_args.log_level,
    )

    # Logg command line args
    logger.debug("Command line args:  %s", cli_args.__dict__)

    # Check if command line args are compatible with one another
    if (
        check_data(
            data_filepath=cli_args.data_filepath,
            scenario=cli_args.scenario,
        )
        is False
    ):
        logger.error("Data file not compatible with this scenario")
        sys.exit(1)
    logger.info(
        "Data file and scenario compatible: %s | %s",
        cli_args.data_filepath,
        cli_args.scenario,
    )

    # Resolve screenshot output path (CLI-provided, already absolute)
    screenshot_path: Path = cli_args.screenshot_path
    logger.info("Screenshot output path: %s", screenshot_path)

    # Connect to Argo
    llm: OpenAIModel = connect_to_argo(
        logger=logger,
        anl_username=cli_args.username,
        endpoint=cli_args.endpoint,
        model_name=cli_args.model,
    )
    logger.info("Argo handshake successful")

    # Improved prompt generation (single dispatch covers every scenario).
    pgp: PromptGenerationPrompt = PROMPT_GENERATION_PROMPTS[cli_args.scenario]
    logger.info("Generating improved prompt for scenario: %s", cli_args.scenario)
    improved_prompt: str = generate_improved_prompt(
        logger=logger,
        pgp=pgp,
        data_filepath=cli_args.data_filepath,
        screenshot_path=screenshot_path,
        llm=llm,
    )
    logger.info("Improved prompt: \n%s", improved_prompt)


if __name__ == "__main__":
    main()
