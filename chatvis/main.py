from argparse import ArgumentParser, Namespace

from chatvis.documents.code_generation import CODE_GENERATION_PROMPTS
from chatvis.documents.prompt_generation import PROMPT_GENERATION_PROMPTS

SCENARIOS: list[str] = sorted(
    set(CODE_GENERATION_PROMPTS) & set(PROMPT_GENERATION_PROMPTS)
)
MODELS: list[str] = ["gpt-4", "gpt-4-turbo", "gpt-4o"]


def cli_parser() -> Namespace:
    parser: ArgumentParser = ArgumentParser(
        prog="chatvis",
        description="Automating Scientific Visualization with a Large Language Model",
        epilog="https://doi.org/10.1109/SCW63240.2024.00014",
    )

    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="ml-dvr",
        help="ChatVis paper scenario to execute (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        choices=MODELS,
        default="gpt-4o",
        help="LLM to leverage (default: %(default)s)",
    )

    return parser.parse_args()


def main() -> None:
    cli_args: Namespace = cli_parser()

    match cli_args.scenario:
        case "ml-dvr":
            raise NotImplementedError("scenario 'ml-dvr' is not yet implemented")
        case "ml-iso":
            raise NotImplementedError("scenario 'ml-iso' is not yet implemented")
        case "ml-slice-iso":
            raise NotImplementedError("scenario 'ml-slice-iso' is not yet implemented")
        case "points-surf-clip":
            raise NotImplementedError(
                "scenario 'points-surf-clip' is not yet implemented"
            )
        case "stream-glyph":
            raise NotImplementedError("scenario 'stream-glyph' is not yet implemented")


if __name__ == "__main__":
    main()
