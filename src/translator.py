#!/usr/bin/env python3
"""CLI entry point: assemble .asm source to binary.

Usage:
    python -m src.translator <input.asm> <output.bin>

Output:
    <output.bin>       — binary machine code (32-bit little-endian words)
    <output.bin>.lst   — human-readable listing: addr - hexword - mnemonic
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.assembler import write_binary


def main() -> None:
    if len(sys.argv) < 3:
        print("Usage: python -m src.translator <input.asm> <output.bin>")
        sys.exit(1)
    src_path, bin_path = sys.argv[1], sys.argv[2]
    lst_path = bin_path.replace(".bin", ".lst") if bin_path.endswith(".bin") else bin_path + ".lst"
    with open(src_path, encoding="utf-8") as f:
        src = f.read()
    n = write_binary(src, bin_path, lst_path)
    print(f"OK: {n} words → {os.path.basename(bin_path)}  (listing: {os.path.basename(lst_path)})")


if __name__ == "__main__":
    main()
