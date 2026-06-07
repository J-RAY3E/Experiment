import re
import struct
import sys
from pathlib import Path
from typing import Any

from src.control_path import ControlPath
from src.data_path import DataPath
from src.isa import REG, REG_NAMES, STACK_BASE, decode


def load_binary(bin_path: str, lst_path: str | None = None) -> tuple[list[int], dict[int, int], int]:
    """Load a binary file into instruction and data word lists.

    Returns:
        instr_words: instruction memory (list indexed by binary address)
        data_map:    data memory map {logical_address: word_value}
        data_base:   base address of data section (for gp register)
    """
    with open(bin_path, "rb") as f:
        raw = f.read()
    words = [struct.unpack("<I", raw[i : i + 4])[0] for i in range(0, len(raw), 4)]

    instr_words: list[int] = []
    data_map: dict[int, int] = {}
    data_base: int = 0

    if lst_path and Path(lst_path).exists():
        with open(lst_path, encoding="utf-8") as f:
            content = f.read()
        lines = content.strip().split("\n")
        all_addrs: list[int] = []
        instr_by_addr: dict[int, int] = {}
        data_by_addr: dict[int, int] = {}
        for line in lines:
            m = re.match(r"^([0-9A-Fa-f]+)\s+-\s+([0-9A-Fa-f]+)\s+-\s+(.+)$", line)
            if not m:
                continue
            addr = int(m.group(1), 16)
            word = int(m.group(2), 16)
            rest = m.group(3).strip()
            all_addrs.append(addr)
            if rest.startswith(".WORD") or rest.startswith(".STRING_LEN") or rest.startswith(".CHAR"):
                data_by_addr[addr] = word
            else:
                instr_by_addr[addr] = word
        if instr_by_addr:
            data_base = 0
            max_addr = max(all_addrs)
            instr_words = [instr_by_addr.get(i, 0) for i in range(max_addr + 1)]
            for a, w in data_by_addr.items():
                data_map[a] = w

    if not instr_words:
        instr_words = list(words)

    return instr_words, data_map, data_base


class Machine:
    """
    RISC-IV processor simulator.

    tick-accurate: each call to tick() advances the machine by exactly one
    micro-step (one µROM entry).  The journal records every micro-step.
    """

    def __init__(self, bin_path: str, lst_path: str | None = None, input_text: str = "") -> None:
        instr_words, data_map, data_base = load_binary(bin_path, lst_path)
        self.instr_mem: list[int] = instr_words
        self.dp = DataPath(input_text)
        for addr, w in data_map.items():
            self.dp.mem.mem[addr] = w
        self.dp.regs.write(REG["gp"], data_base)
        self.dp.regs.write(REG["sp"], STACK_BASE)
        self.cp = ControlPath()
        self.halted = False
        self.tick_count = 0
        self.snapshots: list[dict[str, Any]] = []

    def _snapshot(self, mi_name: str) -> None:
        d = self.dp
        self.snapshots.append(
            {
                "tick": self.tick_count,
                "upc": self.cp.upc,
                "phase": mi_name,
                "pc": d.pc,
                "ir": d.ir,
                "a": d.a,
                "b": d.b,
                "alu_out": d.alu_out,
                "mdr": d.mdr,
            }
        )

    def tick(self) -> None:
        if self.halted:
            return
        self.tick_count += 1

        ir = self.dp.ir
        mi = self.cp.current_mi(ir)
        mi_name = self.cp.phase_name
        inst_word: int | None = None
        if mi.ir_we and 0 <= self.dp.pc < len(self.instr_mem):
            inst_word = self.instr_mem[self.dp.pc]

        done = self.dp.tick(mi, inst_word)
        self._snapshot(mi_name)
        self.cp.advance(self.dp.ir)

        if done:
            self.halted = True

    def run(self, max_ticks: int = 200000) -> str:
        while not self.halted and self.tick_count < max_ticks:
            self.tick()
        return "".join(chr(c) if isinstance(c, int) and 0 <= c < 256 else str(c) for c in self.dp.output_buffer)

    def get_journal(self) -> str:
        lines: list[str] = []
        for s in self.snapshots:
            tick = s["tick"]
            upc = s["upc"]
            pc = s["pc"]
            ir = s["ir"]
            d_ctx = decode(ir)
            mnem = d_ctx["name"]

            saved_upc = self.cp.seq.upc
            self.cp.seq.upc = s["upc"]
            mi = self.cp.seq.current_mi(ir)
            self.cp.seq.upc = saved_upc
            sigs = []
            if mi.ir_we:
                sigs.append("ir_we")
            if mi.pc_inc:
                sigs.append("pc+1")
            if mi.mar_we:
                sigs.append("mar_we")
            if mi.mem_rd:
                sigs.append("mem_rd")
            if mi.mem_wr:
                sigs.append("mem_wr")
            if mi.reg_we:
                sigs.append("reg_we")
            sigs_str = ",".join(sigs) if sigs else "none"

            r_parts = [f"PC={pc}", f"AR={self.dp.mar}", f"DR={self.dp.mdr}"]
            for i in range(16):
                name = REG_NAMES[i].upper()
                val = self.dp.regs.read(i)
                r_parts.append(f"{name}={val}")
            regs_str = " ".join(r_parts)

            out_str = "".join(chr(c) for c in self.dp.output_buffer if 0 <= c < 256)

            line = (
                f"Tick: {tick:06d} | uPC: {upc:02X} | MIR: {mi.mir_word:08X} | "
                f"PC: {pc:04X} | IR: {ir:08X} | Micro: {s['phase']} | "
                f"Signals: {sigs_str} | Exec: {mnem} | "
                f"Regs: {regs_str} | Out: {out_str!r}"
            )
            lines.append(line)
        return "\n".join(lines)

    def dump_registers(self) -> dict[str, int]:
        return {REG_NAMES[i]: self.dp.regs.regs[i] for i in range(len(REG_NAMES))}

    def write_outputs(self, target_prefix: str) -> None:
        import struct

        cmem_data = struct.pack(f"<{len(self.instr_mem)}I", *self.instr_mem)
        with open(target_prefix + ".cmem", "wb") as f:
            f.write(cmem_data)
        hex_str = " ".join(f"{w:08X}" for w in self.instr_mem)
        with open(target_prefix + ".hex", "w", encoding="utf-8") as f:
            f.write(hex_str + "\n")
        words = [w for w in self.dp.mem.mem if w != 0]
        mem_data = struct.pack(f"<{len(words)}I", *words) if words else b""
        with open(target_prefix + ".mem", "wb") as f:
            f.write(mem_data)
        mem_hex = " ".join(f"{w:08X}" for w in words)
        with open(target_prefix + ".mem.hex", "w", encoding="utf-8") as f:
            f.write(mem_hex + "\n" if mem_hex else "\n")


def main(target_prefix: str = "", input_path: str = "", limit: int = 200000) -> str | None:
    if target_prefix:
        bin_path = target_prefix + ".bin"
        lst_path: str | None = target_prefix + ".lst"
        if lst_path is not None and not Path(lst_path).exists():
            lst_path = None
        input_text = open(input_path).read() if input_path else ""
        m = Machine(bin_path, lst_path, input_text)
        out = m.run(max_ticks=limit)
        m.write_outputs(target_prefix)
        return out

    if len(sys.argv) < 2:
        print("Usage: python -m src.Machine <binary.bin> [input.txt] [max_ticks]")
        sys.exit(1)

    bin_path = sys.argv[1]
    lst_candidate = bin_path.replace(".bin", ".lst")
    lst_path = lst_candidate if Path(lst_candidate).exists() else None
    input_text = open(sys.argv[2]).read() if len(sys.argv) > 2 else ""
    max_ticks = int(sys.argv[3]) if len(sys.argv) > 3 else 200000

    m = Machine(bin_path, lst_path, input_text)
    out = m.run(max_ticks=max_ticks)

    print(f"Output:\n{out!r}\n")
    journal_lines = m.get_journal().split("\n")
    print(f"Journal (last 40 of {len(journal_lines)} micro-steps):")
    for line in journal_lines[-40:]:
        print(line)

    print(f"\nTotal micro-ticks: {m.tick_count}")
    print("\nRegisters (non-zero):")
    for k, v in m.dump_registers().items():
        if v:
            print(f"  {k:4}: {v} (0x{v:08X})")
    return None


if __name__ == "__main__":
    main()
