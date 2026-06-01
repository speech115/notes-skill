from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping


CommandHandler = Callable[[argparse.Namespace], int]


def dispatch_command(
    args: argparse.Namespace,
    *,
    handlers: Mapping[str, CommandHandler],
    parser_error: Callable[[str], object],
) -> int:
    handler = handlers.get(str(args.command))
    if handler is None:
        parser_error(f"Unsupported command: {args.command}")
        return 2
    return handler(args)


__all__ = ["CommandHandler", "dispatch_command"]
