#!/usr/bin/env python3
"""Send a ServerChan notification.

Uses only the Python standard library so it works in lightweight Codex sessions.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Send a ServerChan push message.")
    parser.add_argument("--title", required=True, help="Notification title.")
    parser.add_argument("--desp", default="", help="Notification body/description.")
    parser.add_argument(
        "--sendkey",
        default=os.environ.get("SERVERCHAN_SENDKEY"),
        help="ServerChan send key. Defaults to SERVERCHAN_SENDKEY.",
    )
    parser.add_argument(
        "--endpoint-base",
        default="https://sctapi.ftqq.com",
        help="ServerChan API base URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the request summary without sending it.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.sendkey:
        print("Missing send key. Pass --sendkey or set SERVERCHAN_SENDKEY.", file=sys.stderr)
        return 2

    endpoint = f"{args.endpoint_base.rstrip('/')}/{args.sendkey}.send"
    data = urllib.parse.urlencode({"title": args.title, "desp": args.desp}).encode("utf-8")

    if args.dry_run:
        masked_key = args.sendkey[:6] + "..." + args.sendkey[-4:] if len(args.sendkey) > 12 else "***"
        print(json.dumps(
            {
                "endpoint": endpoint.replace(args.sendkey, masked_key),
                "method": "POST",
                "title": args.title,
                "desp_length": len(args.desp),
            },
            ensure_ascii=False,
            indent=2,
        ))
        return 0

    request = urllib.request.Request(endpoint, data=data, method="POST")
    request.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            body = response.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001 - CLI should show transport failures plainly.
        print(f"ServerChan request failed: {exc}", file=sys.stderr)
        return 1

    print(body)
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return 1

    if payload.get("code") == 0 or payload.get("data", {}).get("error") == "SUCCESS":
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
