"""ChatVis CLI entry point.

Currently a minimal stub that only parses command-line arguments while the
pipeline is rebuilt on top of ``chatvis.v1``. End-to-end scenario execution
will be reintroduced commit by commit.
"""

import logging
from argparse import Namespace
from logging import Logger
from pathlib import Path

from chatvis.cli import CLI
from chatvis.logger import configure_logging


def setup_logger(log_to_file: bool, log_level: str) -> Logger:
    log_path: Path | None = configure_logging(
        log_to_file=log_to_file,
        level=logging.getLevelNamesMapping()[log_level.upper()],
    )

    logger: Logger = logging.getLogger("chatvis")

    if log_path is not None:
        logger.info("Logging to %s", log_path)

    return logger


def main() -> None:
    cli_args: Namespace = CLI().parser()

    logger: Logger = setup_logger(
        log_to_file=cli_args.log_file,
        log_level=cli_args.log_level,
    )

    logger.debug("Command line args: %s", cli_args.__dict__)
    logger.info("ChatVis CLI stub: pipeline not yet wired up.")


if __name__ == "__main__":
    main()
