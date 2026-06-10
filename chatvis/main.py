from argparse import ArgumentParser, Namespace


def cli_parser() -> Namespace:
    parser: ArgumentParser = ArgumentParser(
        prog="chatvis",
        description="Automating Scientific Visualization with a Large Language Model",
        epilog="https://doi.org/10.1109/SCW63240.2024.00014",
    )

    parser.add_argument(
        "--scenario",
        choices=[
            "ml-dvr",
            "ml-iso",
            "ml-slice-iso",
            "points-surf-clip",
            "stream-glyph",
        ],
        default="ml-dvr",
        help="ChatVis paper scenario to execute (default: %(default)s)",
    )
    parser.add_argument(
        "--model",
        choices=["gpt4o"],
        default="gpt4o",
        help="LLM to leverage (default: %(default)s)",
    )

    return parser.parse_args()


def main():
    cli_args: Namespace = cli_parser()

    match cli_args.scenario:
        case "ml-dvr":
            pass
        case "ml-iso":
            pass
        case "ml-slice-iso":
            pass
        case "points-surf-clip":
            pass
        case "stream-glyph":
            pass


if __name__ == "__main__":
    main()
