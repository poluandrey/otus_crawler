"""Command-line interface."""

import argparse
import asyncio
import logging
from pathlib import Path

from crawler.crawler import Crawler, CrawlerConfig


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Asynchronous Hacker News crawler")
    parser.add_argument(
        "--interval", type=float, default=60, help="seconds between runs"
    )
    parser.add_argument("--limit", type=int, default=30, help="stories per run")
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--output", type=Path, default=Path("data"))
    parser.add_argument("--base-url", default="https://news.ycombinator.com/")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--verbose", action="store_true")
    return parser


async def async_main(args: argparse.Namespace) -> None:
    """Create and run the crawler from parsed CLI arguments."""
    if args.limit < 1 or args.concurrency < 1 or args.interval <= 0:
        raise SystemExit("limit, concurrency and interval must be positive")
    config = CrawlerConfig(
        base_url=args.base_url,
        interval=args.interval,
        limit=args.limit,
        concurrency=args.concurrency,
        timeout=args.timeout,
        output=args.output,
    )
    crawler = Crawler(config)
    if args.once:
        await crawler.run_once()
    else:
        await crawler.run_forever()


def main() -> None:
    """Run the command-line application."""
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Crawler stopped")


if __name__ == "__main__":
    main()
