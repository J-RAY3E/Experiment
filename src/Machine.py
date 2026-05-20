"""Machine: top-level processor model that wires DataPath + ControlPath.

Loads a binary program, simulates tick-by-tick, and produces a journal
of execution states.

Usage:
    python Machine.py <binary.bin> [input.txt]
"""

import struct
import os
import re
import sys

from src.ISA import (
    REG, REG_NAMES,STACK_BASE, decode,
)
from src.DataPath import DataPath
from src.ControlPath import ControlPath


def load_binary(bin_path, lst_path=None):
    with open(bin_path, "rb") as f:
        raw = f.read()

    words = [struct.unpack("<I", raw[i:i + 4])[0] for i in range(0, len(raw), 4)]
    instr_words = []
    data_words = []
    data_base = 0

    if lst_path and os.path.exists(lst_path):
        with open(lst_path, encoding="utf-8") as f:
            content = f.read()
        max_addr = -1
        for m in re.finditer(r"^([0-9A-Fa-f]+)\s+-", content, re.M):
            addr = int(m.group(1), 16)
            if addr > max_addr:
                max_addr = addr

        orgs = re.findall(r"\.org\s+(\d+)", content)
        if orgs and max_addr >= 0:
            for o in orgs:
                ov = int(o)
                if ov > max_addr:
                    data_base = ov
                    break

        if max_addr >= 0:
            n_instr = max_addr + 1
            instr_words = words[:min(n_instr, len(words))]
            data_words = words[min(n_instr, len(words)):]

    if not instr_words:
        instr_words = list(words)
        data_words = []

    return instr_words, data_words, data_base


class Machine:
    def __init__(self, bin_path, lst_path=None, input_text=""):
        instr_words, data_words, data_base = load_binary(bin_path, lst_path)
        self.instr_mem = instr_words
        self.dp = DataPath(input_text)

        for i, w in enumerate(data_words):
            self.dp.mem.mem[data_base + i] = w

        self.dp.regs.write(REG["gp"], data_base)
        self.dp.regs.write(REG["sp"], STACK_BASE)

        self.cp = ControlPath()
        self.halted = False
        self.tick_count = 0
        self.cycle_snapshots = []


    def _log_state(self):
        """Capture a snapshot of the processor state for the journal."""
        d = self.dp
        self.cycle_snapshots.append({
            "tick": self.tick_count,
            "phase": self.cp.state().name,
            "pc": d.pc,
            "ir": d.ir,
            "a": d.a,
            "b": d.b,
            "alu_out": d.alu_out,
            "mdr": d.mdr,
        })


    def tick(self):
        if self.halted:
            return
        self.tick_count += 1
        d = self.dp

        ir = d.ir
        next_phase = self.cp.next_phase(ir, {})
        sigs = self.cp.control_signals(ir)

        inst_word = None
        if sigs.get("ir_we"):
            pc = d.pc
            inst_word = self.instr_mem[pc] if pc < len(self.instr_mem) else 0

        # Apply signals to datapath
        halted = d.tick(sigs, inst_word)

        # Advance state register
        self.cp.state_reg.clock(next_state=next_phase)

        if halted:
            self.halted = True

        self._log_state()

    def run(self, max_ticks=100_000):
        while not self.halted and self.tick_count < max_ticks:
            self.tick()
        return self._collect_output()

    def _collect_output(self):
        parts = []
        for c in self.dp.output_buffer:
            if isinstance(c, int) and 0 <= c < 256:
                parts.append(chr(c))
            elif isinstance(c, str):
                parts.append(c)
        return "".join(parts)


    def get_journal(self):
        lines = []
        for s in self.cycle_snapshots:
            ir = s["ir"]
            dcd = decode(ir)
            name = dcd["name"]
            phase = s["phase"]
            pc = s["pc"]
            tick = s["tick"]

            line = (
                f"tick={tick:>6} phase={phase:>7} "
                f"pc={pc:04X} ir={ir:08X} {name:>5}"
            )

            if phase == "Execute" and name not in ("NOP", "HALT", "J"):
                line += f" a={s['a']:08X} b={s['b']:08X}"
            if phase == "Execute" and name in (
                "ADD", "SUB", "MUL", "ADDI", "ANDI", "ORI", "XORI", "LUI",
                "SLLI", "SRLI", "SRAI", "SLTI", "DIV", "REM", "MULH",
                "AND", "OR", "XOR", "NOT", "SLL", "SRL", "SRA", "SLT",
            ):
                line += f" alu={s['alu_out']:08X}"

            lines.append(line)
        return "\n".join(lines)

    def dump_registers(self):
        """Return dict of register name → value."""
        return {REG_NAMES[i]: self.dp.regs.regs[i] for i in range(len(REG_NAMES))}


def main():
    if len(sys.argv) < 2:
        print("Usage: python Machine.py <binary.bin> [input.txt]")
        sys.exit(1)

    bin_path = sys.argv[1]
    lst_path = bin_path.replace(".bin", ".lst") if bin_path.endswith(".bin") else bin_path + ".lst"
    if not os.path.exists(lst_path):
        lst_path = bin_path + ".lst"
    if not os.path.exists(lst_path):
        lst_path = None

    input_text = ""
    if len(sys.argv) > 2:
        with open(sys.argv[2], encoding="utf-8") as f:
            input_text = f.read()

    m = Machine(bin_path, lst_path, input_text)
    out = m.run()
    print("Output:")
    print(repr(out))
    print(f"\nJournal (last 30):")
    lines = m.get_journal().split("\n")
    for line in lines[-30:]:
        print(line)
    print(f"\nTotal ticks: {m.tick_count}")
    print("\nRegisters:")
    for k, v in m.dump_registers().items():
        if v:
            print(f"  {k}: {v} (0x{v:08X})")


if __name__ == "__main__":
    main()
