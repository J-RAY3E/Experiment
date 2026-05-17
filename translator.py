#!/usr/bin/env python3
"""CLI entry point for the RISC translator pipeline.

Modes:
    asm  - Assemble .asm file directly to binary
    hl   - Translate high-level code to assembly, then assemble to binary

Usage:
    python -m src.translator asm <input.asm> <output.bin>
    python -m src.translator hl  <input.txt> <output.bin>
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.assembler import write_binary
from src.hl import HL

def main():
    if len(sys.argv) < 4:
        print("Usage:")
        print("  python -m src.translator asm <input.asm> <output.bin>")
        print("  python -m src.translator hl  <input.txt> <output.bin>")
        sys.exit(1)
    mode, src_path, bin_path = sys.argv[1], sys.argv[2], sys.argv[3]
    lst_path = bin_path + ".lst"
    if mode == "asm":
        with open(src_path, encoding="utf-8") as f:
            src = f.read()
    elif mode == "hl":
        with open(src_path, encoding="utf-8") as f:
            src = HL().run(f.read())
    else:
        print(f"Unknown mode: {mode}"); sys.exit(1)
    n = write_binary(src, bin_path, lst_path)
    print(f"OK: {n} instructions -> {os.path.basename(bin_path)}")

if __name__ == "__main__":
    main()
