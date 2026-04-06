from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_CSV_PATH = Path("egypt_travel_keywords_ar_en_offers_prices.csv")
DEFAULT_API_URL = "http://127.0.0.1:8000/api/v1/pipeline"
DEFAULT_OUTPUT_DIR = Path("logs")


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name)
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Read the first column from a CSV file and call the W2B API for each value.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV_PATH,
        help="Path to the input CSV file.",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=DEFAULT_API_URL,
        help="Full API endpoint URL.",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Value sent as the 'pages' field in the API request body.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Per-request timeout in seconds.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.0,
        help="Delay between requests in seconds.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of rows to process.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional JSON output file. Defaults to logs/pipeline_batch_<timestamp>.json.",
    )
    return parser.parse_args(argv)


def load_first_column(csv_path: Path, limit: int | None = None) -> tuple[str, list[str]]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError(f"CSV file has no header row: {csv_path}")

        first_column = reader.fieldnames[0]
        values: list[str] = []

        for row in reader:
            raw_value = (row.get(first_column) or "").strip()
            if not raw_value:
                continue
            values.append(raw_value)
            if limit is not None and len(values) >= limit:
                break

    if not values:
        raise ValueError(f"No non-empty values found in first column '{first_column}'.")

    return first_column, values


def build_output_path(output: Path | None) -> Path:
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        return output

    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return DEFAULT_OUTPUT_DIR / f"pipeline_batch_{timestamp}.json"


def call_pipeline(
    session: requests.Session,
    api_url: str,
    keyword: str,
    pages: int,
    timeout: int,
) -> dict[str, Any]:
    started_at = datetime.now().isoformat()

    try:
        response = session.post(
            api_url,
            json={"query": keyword, "pages": pages},
            timeout=timeout,
        )
        finished_at = datetime.now().isoformat()

        item: dict[str, Any] = {
            "keyword": keyword,
            "ok": response.ok,
            "status_code": response.status_code,
            "started_at": started_at,
            "finished_at": finished_at,
        }

        try:
            item["response"] = response.json()
        except ValueError:
            item["response_text"] = response.text

        if not response.ok:
            item["error"] = f"HTTP {response.status_code}"

        return item
    except requests.RequestException as exc:
        return {
            "keyword": keyword,
            "ok": False,
            "error": str(exc),
            "started_at": started_at,
            "finished_at": datetime.now().isoformat(),
        }


def save_report(path: Path, report: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2, ensure_ascii=False)


def main(argv: list[str] | None = None) -> int:
    configure_stdio()
    args = parse_args(argv)

    if args.pages < 1:
        raise ValueError("--pages must be at least 1.")
    if args.timeout < 1:
        raise ValueError("--timeout must be at least 1.")
    if args.delay < 0:
        raise ValueError("--delay must be non-negative.")
    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1 when provided.")

    first_column, keywords = load_first_column(args.csv, args.limit)
    output_path = build_output_path(args.output)

    session = requests.Session()
    results: list[dict[str, Any]] = []

    print(f"Loaded {len(keywords)} keyword(s) from column '{first_column}'.")
    print(f"Calling {args.api_url}")

    for index, keyword in enumerate(keywords, start=1):
        print(f"[{index}/{len(keywords)}] {keyword}")
        result = call_pipeline(
            session=session,
            api_url=args.api_url,
            keyword=keyword,
            pages=args.pages,
            timeout=args.timeout,
        )
        results.append(result)

        if args.delay:
            time.sleep(args.delay)

    success_count = sum(1 for item in results if item["ok"])
    failure_count = len(results) - success_count

    report = {
        "csv_path": str(args.csv),
        "first_column": first_column,
        "api_url": args.api_url,
        "pages": args.pages,
        "processed_count": len(results),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }
    save_report(output_path, report)

    print(f"Finished. Success: {success_count}, Failed: {failure_count}")
    print(f"Report saved to: {output_path}")
    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1)
