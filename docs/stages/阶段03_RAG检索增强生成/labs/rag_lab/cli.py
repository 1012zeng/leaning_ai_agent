"""Command-line entry points for demo, failure injection, and benchmark."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from rag_lab.benchmark import benchmark
from rag_lab.config import load_config
from rag_lab.errors import StageError
from rag_lab.failures import SCENARIOS, run_failures
from rag_lab.pipeline import OfflineRagPipeline
from rag_lab.serialization import dumps

LOGGER = logging.getLogger("rag_lab")


def build_parser() -> argparse.ArgumentParser:
    """Build the feature-complete teaching CLI."""

    parser = argparse.ArgumentParser(prog="rag-lab")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run the offline end-to-end pipeline")
    demo.add_argument("--config", default="configs/offline.json")
    demo.add_argument("--stdout", action="store_true", help="print all intermediate objects")
    failures = subparsers.add_parser("failures", help="run reproducible fault experiments")
    failures.add_argument("--config", default="configs/offline.json")
    failures.add_argument("--scenario", choices=("all", *SCENARIOS), default="all")
    bench = subparsers.add_parser("benchmark", help="measure local offline latency")
    bench.add_argument("--config", default="configs/offline.json")
    bench.add_argument("--iterations", type=int, default=30)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run a CLI command and return a process exit status."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s event=%(message)s")
    args = build_parser().parse_args(argv)
    try:
        config = load_config(Path(args.config))
        if args.command == "demo":
            pipeline = OfflineRagPipeline(config)
            result = pipeline.run()
            output_path, trace_path = pipeline.write_outputs(result)
            payload: object = (
                result
                if args.stdout
                else {
                    "shape": result.shape(),
                    "answer": result.generation.answer,
                    "citations": result.generation.citations,
                    "output_path": output_path.as_posix(),
                    "trace_path": trace_path.as_posix(),
                }
            )
            LOGGER.info(
                "pipeline_completed query_id=%s outcome=%s trace_id=%s",
                result.query.query_id,
                result.generation.answer.outcome,
                result.trace_events[0].trace_id,
            )
            print(dumps(payload))
            return 0
        if args.command == "failures":
            results = run_failures(config, args.scenario)
            print(
                dumps({"all_observed": all(item.observed for item in results), "results": results})
            )
            return 0 if all(item.observed for item in results) else 1
        if args.command == "benchmark":
            print(dumps(benchmark(config, args.iterations)))
            return 0
    except StageError as error:
        print(dumps(error.problem), file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError) as error:
        print(dumps({"code": "CLI_INPUT_ERROR", "detail": str(error)}), file=sys.stderr)
        return 2
    return 2
