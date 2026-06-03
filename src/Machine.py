import os
import re
import struct
import sys

from src.ControlPath import ControlPath, UROM_NAMES
from src.DataPath import DataPath
from src.ISA import REG, REG_NAMES, STACK_BASE, decode


def load_binary(bin_path: str, lst_path: str | None = None):
    """Load a binary file into instruction and data word lists."""
    with open(bin_path, "rb") as f:
        raw = f.read()
    words = [struct.unpack("<I", raw[i : i + 4])[0] for i in range(0, len(raw), 4)]

    instr_words: list[int] = []
    data_words:  list[int] = []
    data_base:   int       = 0

    if lst_path and os.path.exists(lst_path):
        with open(lst_path, encoding="utf-8") as f:
            content = f.read()
        addresses = [
            int(m.group(1), 16)
            for m in re.finditer(r"^([0-9A-Fa-f]+)\s+-", content, re.M)
        ]
        max_addr = max(addresses) if addresses else -1
        if max_addr >= 0:
            orgs = re.findall(r"\.org\s+(\d+)", content)
            for o in orgs:
                if int(o) > max_addr:
                    data_base = int(o)
                    break
            n = max_addr + 1
            instr_words = words[: min(n, len(words))]
            data_words  = words[min(n, len(words)) :]

    if not instr_words:
        instr_words, data_words = list(words), []

    return instr_words, data_words, data_base


class Machine:
    """
    RISC-IV processor simulator.

    tick-accurate: each call to tick() advances the machine by exactly one
    micro-step (one µROM entry).  The journal records every micro-step.
    """

    def __init__(self, bin_path: str, lst_path: str | None = None,
                 input_text: str = "") -> None:
        instr_words, data_words, data_base = load_binary(bin_path, lst_path)
        self.instr_mem: list[int] = instr_words
        self.dp = DataPath(input_text)
        for i, w in enumerate(data_words):
            self.dp.mem.mem[data_base + i] = w
        self.dp.regs.write(REG["gp"], data_base)
        self.dp.regs.write(REG["sp"], STACK_BASE)
        self.cp         = ControlPath()
        self.halted     = False
        self.tick_count = 0
        self.snapshots: list[dict] = []

    # ── Snapshot ──────────────────────────────────────────────────────────
    def _snapshot(self, mi_name: str) -> None:
        d = self.dp
        self.snapshots.append({
            "tick":    self.tick_count,
            "upc":     self.cp.upc,
            "phase":   mi_name,
            "pc":      d.pc,
            "ir":      d.ir,
            "a":       d.a,
            "b":       d.b,
            "alu_out": d.alu_out,
            "mdr":     d.mdr,
        })

    # ── Single micro-tick ─────────────────────────────────────────────────
    def tick(self) -> None:
        if self.halted:
            return
        self.tick_count += 1

        ir       = self.dp.ir
        mi       = self.cp.current_mi(ir)
        mi_name  = self.cp.phase_name

        # On FETCH: read the instruction word from instr_mem at current PC
        inst_word: int | None = None
        if mi.ir_we and 0 <= self.dp.pc < len(self.instr_mem):
            inst_word = self.instr_mem[self.dp.pc]

        done = self.dp.tick(mi, inst_word)

        # Advance µPC using the IR that was just loaded (new ir after FETCH)
        self.cp.advance(self.dp.ir)

        self._snapshot(mi_name)

        if done:
            self.halted = True

    # ── Run ───────────────────────────────────────────────────────────────
    def run(self, max_ticks: int = 200000) -> str:
        while not self.halted and self.tick_count < max_ticks:
            self.tick()
        return "".join(
            chr(c) if isinstance(c, int) and 0 <= c < 256 else str(c)
            for c in self.dp.output_buffer
        )

    # ── Journal ───────────────────────────────────────────────────────────
    def get_journal(self) -> str:
        lines: list[str] = []
        for s in self.snapshots:
            ir    = s["ir"]
            phase = s["phase"]
            tick  = s["tick"]
            upc   = s["upc"]
            pc    = s["pc"]
            name  = decode(ir)["name"]
            line  = (
                f"TICK: {tick:>6}  UPC: {upc:>2}  PHASE: {phase:<8}"
                f"  PC: {pc:04X}  IR: {ir:08X}  CMD: {name:>5}"
            )
            if phase not in ("FETCH", "NOP_EX", "HALT_EX", "J_EX"):
                line += f"  A: {s['a']:08X}  B: {s['b']:08X}"
            if phase in (
                "R_EX", "I_EX", "L_EX1", "S_EX",
                "V_EX", "VLD_EX1", "VST_EX",
            ):
                line += f"  ALU: {s['alu_out']:08X}"
            if phase in ("L_EX2", "VLD_EX2"):
                line += f"  MDR: {s['mdr']:08X}"
            lines.append(line)
        return "\n".join(lines)

    # ── Register dump ─────────────────────────────────────────────────────
    def dump_registers(self) -> dict:
        return {REG_NAMES[i]: self.dp.regs.regs[i] for i in range(len(REG_NAMES))}


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m src.Machine <binary.bin> [input.txt] [max_ticks]")
        sys.exit(1)

    bin_path  = sys.argv[1]
    lst_path  = bin_path.replace(".bin", ".lst")
    if not os.path.exists(lst_path):
        lst_path = None
    input_text = open(sys.argv[2]).read() if len(sys.argv) > 2 else ""
    max_ticks  = int(sys.argv[3]) if len(sys.argv) > 3 else 200000

    m   = Machine(bin_path, lst_path, input_text)
    out = m.run(max_ticks=max_ticks)

    print(f"Output:\n{repr(out)}\n")
    journal_lines = m.get_journal().split("\n")
    print(f"Journal (last 40 of {len(journal_lines)} micro-steps):")
    for line in journal_lines[-40:]:
        print(line)

    print(f"\nTotal micro-ticks: {m.tick_count}")
    print("\nRegisters (non-zero):")
    for k, v in m.dump_registers().items():
        if v:
            print(f"  {k:4}: {v} (0x{v:08X})")


if __name__ == "__main__":
    main()
