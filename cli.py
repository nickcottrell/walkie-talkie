"""Walkie-talkie CLI.

Usage:
  walkie encode "<text>" [--basis NAME] [--blacklist WORD ...]
  walkie decode <path-or-stdin> [--mode prose|primitive|both]
  walkie roundtrip "<text>"
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from decoder import decode
from encoder import encode
from schema import record_from_dict


def cmd_encode(args: argparse.Namespace) -> int:
    record = encode(
        args.text,
        basis=args.basis,
        extra_blacklist=args.blacklist or [],
    )
    print(json.dumps(record.to_dict(), indent=2))
    return 0


def cmd_decode(args: argparse.Namespace) -> int:
    if args.path == "-":
        data = json.load(sys.stdin)
    else:
        data = json.loads(Path(args.path).read_text())
    record = record_from_dict(data)
    print(decode(record, mode=args.mode))
    return 0


def cmd_roundtrip(args: argparse.Namespace) -> int:
    record = encode(args.text, basis=args.basis)
    print("== ENCODED ==")
    print(json.dumps(record.to_dict(), indent=2))
    print()
    print("== DECODED (prose) ==")
    print(decode(record, mode="prose"))
    print()
    print("== DECODED (primitive) ==")
    print(decode(record, mode="primitive"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="walkie", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_enc = sub.add_parser("encode", help="encode text → record")
    p_enc.add_argument("text")
    p_enc.add_argument("--basis", default="vrgb-default")
    p_enc.add_argument("--blacklist", nargs="*", default=[])
    p_enc.set_defaults(func=cmd_encode)

    p_dec = sub.add_parser("decode", help="decode record → text")
    p_dec.add_argument("path", help="record path, or '-' for stdin")
    p_dec.add_argument("--mode", choices=["prose", "primitive", "both"], default="prose")
    p_dec.set_defaults(func=cmd_decode)

    p_rt = sub.add_parser("roundtrip", help="encode then decode for inspection")
    p_rt.add_argument("text")
    p_rt.add_argument("--basis", default="vrgb-default")
    p_rt.set_defaults(func=cmd_roundtrip)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
