from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.hl_logic import HL
from src.machine import main as machine_main
from src.translator import main as translator_main


def _cmd_compile(args: argparse.Namespace) -> int:
    hl = HL()
    asm_text = hl.run(args.input.read_text(encoding="utf-8"))
    if args.output.suffix == ".asm":
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(asm_text, encoding="utf-8")
        return 0
    asm_tmp = args.output.with_suffix(".asm")
    asm_tmp.parent.mkdir(parents=True, exist_ok=True)
    asm_tmp.write_text(asm_text, encoding="utf-8")
    target_prefix = str(args.output.with_suffix(""))
    return translator_main(str(asm_tmp), target_prefix)

def _cmd_asm(args: argparse.Namespace) -> int:
    target_prefix = str(args.output.with_suffix(""))
    return translator_main(str(args.input), target_prefix)

def _cmd_run(args: argparse.Namespace) -> int:
    target_prefix = str(args.binary.with_suffix(""))
    input_path = str(args.input) if args.input is not None else ""
    out = machine_main(
        target_prefix=target_prefix,
        input_path=input_path,
        limit=args.max_ticks,
    )
    if out is not None:
        print(f"Output:\n{out!r}")
    return 0

def _to_path(value: str) -> Path:
    return Path(value)

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="src.cli", description="RISC-IV lab CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_compile = sub.add_parser("compile", help="High-level .alg -> .bin")
    p_compile.add_argument("input", type=_to_path)
    p_compile.add_argument("output", type=_to_path)
    p_compile.set_defaults(func=_cmd_compile)

    p_asm = sub.add_parser("asm", help="Assembler .asm -> .bin")
    p_asm.add_argument("input", type=_to_path)
    p_asm.add_argument("output", type=_to_path)
    p_asm.set_defaults(func=_cmd_asm)

    p_run = sub.add_parser("run", help="Run .bin simulation")
    p_run.add_argument("binary", type=_to_path)
    p_run.add_argument("input", nargs="?", type=_to_path, default=None)
    p_run.add_argument("max_ticks", nargs="?", type=int, default=200000)
    p_run.set_defaults(func=_cmd_run)

    return parser

def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))

if __name__ == "__main__":
    sys.exit(main())
