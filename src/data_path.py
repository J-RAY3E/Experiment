from collections.abc import Callable
from typing import Any

from src.control_path import (
    B_IMM,
    B_RS2,
    B_ZERO,
    MI,
    REG_ALU,
    REG_IMM_SHL11,
    REG_IMM_U21,
    REG_IMM_U26,
    REG_MEM,
    REG_PC,
)
from src.isa import (
    DATA_MEM_SIZE,
    IN_PORT,
    NUM_REGS,
    NUM_VREGS,
    OUT_PORT,
    REG_NAMES,
    SIGN_BIT,
    VLANES,
    WORD_MASK,
    decode,
)

BYTE_MASK = 0xFF
BYTE_SIGN = 0x80
SHIFT_MASK = 0x1F
SIGN_EXT_NEG = ~0x7FFFFFFF


def _to_signed(v: int) -> int:
    return v if not (v & SIGN_BIT) else v | SIGN_EXT_NEG


class BranchComparator:
    """Evaluating conditions between two register values."""

    def evaluate(self, r1: int, r2: int) -> dict[str, bool]:
        u1, u2 = r1 & WORD_MASK, r2 & WORD_MASK
        s1, s2 = _to_signed(r1), _to_signed(r2)
        return {"eq": u1 == u2, "lt": s1 < s2, "ltu": u1 < u2}


class RegisterFile:
    def __init__(self) -> None:
        self.regs = [0] * NUM_REGS

    def read(self, addr: int) -> int:
        return 0 if addr == 0 else self.regs[addr]

    def write(self, addr: int, value: int) -> None:
        if addr != 0:
            self.regs[addr] = value & WORD_MASK


class VectorRegisterFile:
    def __init__(self) -> None:
        self.regs = [[0] * VLANES for _ in range(NUM_VREGS)]

    def read(self, addr: int) -> list[int]:
        return list(self.regs[addr & (NUM_VREGS - 1)])

    def write(self, addr: int, values: list[int], lane: int | None = None) -> None:
        idx = addr & (NUM_VREGS - 1)
        if lane is not None:
            self.regs[idx][lane] = values[0] & WORD_MASK
        else:
            self.regs[idx] = [v & WORD_MASK for v in values]


class ALU:
    """Unidad Aritmético-Lógica con despacho profesional de operaciones."""

    def execute(self, op: str, a: int, b: int) -> int:
        val_a = a & WORD_MASK
        val_b = b & WORD_MASK

        if op == "ADD":
            return (val_a + val_b) & WORD_MASK
        if op == "SUB":
            return (val_a - val_b) & WORD_MASK
        if op == "MUL":
            return (val_a * val_b) & WORD_MASK
        if op == "MULH":
            s1 = _to_signed(val_a)
            s2 = _to_signed(val_b)
            return ((s1 * s2) >> 32) & WORD_MASK
        if op == "DIV":
            return (_to_signed(val_a) // _to_signed(val_b)) & WORD_MASK if val_b != 0 else 0
        if op == "REM":
            return (_to_signed(val_a) % _to_signed(val_b)) & WORD_MASK if val_b != 0 else 0
        if op == "AND":
            return val_a & val_b
        if op == "OR":
            return val_a | val_b
        if op == "XOR":
            return val_a ^ val_b
        if op == "NOT":
            return (~val_a) & WORD_MASK
        if op == "SLL":
            return (val_a << (val_b & SHIFT_MASK)) & WORD_MASK
        if op == "SRL":
            return (val_a >> (val_b & SHIFT_MASK)) & WORD_MASK
        if op == "SRA":
            return (_to_signed(val_a) >> (val_b & SHIFT_MASK)) & WORD_MASK
        if op == "SLT":
            return 1 if _to_signed(val_a) < _to_signed(val_b) else 0

        return 0


class DataMemory:
    def __init__(self, size: int = DATA_MEM_SIZE) -> None:
        self.mem = [0] * size
        self._read_input: Callable[[], int] | None = None
        self._write_output: Callable[[int], None] | None = None

    def load_word(self, addr: int) -> int:
        addr &= WORD_MASK
        if addr == IN_PORT:
            return self._read_input() if self._read_input else 0
        return self.mem[addr] if 0 <= addr < len(self.mem) else 0

    def load_byte(self, addr: int) -> int:
        val = self.load_word(addr) & BYTE_MASK
        return (val | ~BYTE_MASK) & WORD_MASK if val & BYTE_SIGN else val

    def store_word(self, addr: int, value: int) -> None:
        addr &= WORD_MASK
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem):
            self.mem[addr] = value & WORD_MASK

    def store_byte(self, addr: int, value: int) -> None:
        addr &= WORD_MASK
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem):
            self.mem[addr] = (self.mem[addr] & ~BYTE_MASK) | (value & BYTE_MASK)


class DataPath:
    def __init__(self, input_stream: str = "") -> None:
        self.regs = RegisterFile()
        self.vregs = VectorRegisterFile()
        self.alu = ALU()
        self.comp = BranchComparator()
        self.mem = DataMemory()

        self.pc: int = 0
        self.ir: int = 0
        self.a: int = 0
        self.b: int = 0
        self.mar: int = 0
        self.mdr: int = 0
        self.alu_out: int = 0
        self.feedback_bus: int = 0
        self.br_flags: dict[str, bool] = {"eq": True, "lt": False, "ltu": False}
        self.vbase: int = 0

        self._ctx: dict[str, Any] = {}

        self.input_buffer: list[str] = list(input_stream)
        self.input_pos: int = 0
        self.output_buffer: list[int] = []

        self.mem._read_input = self._read_next_char
        self.mem._write_output = self._write_char

    def _read_next_char(self) -> int:
        if self.input_pos < len(self.input_buffer):
            ch = ord(self.input_buffer[self.input_pos])
            self.input_pos += 1
            return ch
        return 0

    def _write_char(self, val: int) -> None:
        self.output_buffer.append(val)

    def dump_registers(self) -> dict[str, int]:
        return {REG_NAMES[i]: self.regs.read(i) for i in range(NUM_REGS)}

    def tick(self, mi: MI, inst_word: int | None = None) -> bool:
        if mi.ir_we:
            if inst_word is not None:
                self.ir = inst_word
            self._ctx = decode(self.ir)
            if mi.pc_inc:
                self.pc = (self.pc + 1) & WORD_MASK
            return False

        if mi.halt:
            return True

        ctx = self._ctx
        rs1, rs2, rd = ctx["rs1"], ctx["rs2"], ctx["rd"]
        imm_s = ctx["imm_s"]

        r1_data = self.regs.read(rs1)
        r2_data = self.regs.read(rs2)
        self.br_flags = self.comp.evaluate(r1_data, r2_data)

        self.a = self.pc if mi.a_sel == 2 else r1_data
        self.b = imm_s if mi.b_sel == B_IMM else (0 if mi.b_sel == B_ZERO else r2_data)

        v_alu_out: list[int] | None = None
        if mi.alu_exec and mi.alu_op:
            if mi.valu_exec:
                v_a = self.vregs.read(rs1)
                v_b = self.vregs.read(rs2) if mi.b_sel == B_RS2 else [self.b] * VLANES
                v_alu_out = [self.alu.execute(mi.alu_op, v_a[i], v_b[i]) for i in range(VLANES)]
                self.alu_out = v_alu_out[0]
            else:
                self.alu_out = self.alu.execute(mi.alu_op, self.a, self.b)

        if mi.mar_we:
            self.mar = self.alu_out

        mem_addr = self.vbase if mi.addr_sel else self.mar

        if mi.vbase_we:
            if mi.vbase_sel:
                self.vbase = (self.vbase + 1) & WORD_MASK
            else:
                self.vbase = self.mar

        if mi.mem_rd:
            self.mdr = self.mem.load_byte(mem_addr) if mi.mem_byte else self.mem.load_word(mem_addr)

        if mi.mem_wr:
            if mi.mem_data_src == 1:
                vals = self.vregs.read(rd)
                self.mem.store_word(mem_addr, vals[mi.lane_sel])
            else:
                data = r2_data
                if mi.mem_byte:
                    self.mem.store_byte(mem_addr, data)
                else:
                    self.mem.store_word(mem_addr, data)

        if mi.reg_src == REG_ALU:
            self.feedback_bus = self.alu_out
        elif mi.reg_src == REG_MEM:
            self.feedback_bus = self.mdr
        elif mi.reg_src == REG_PC:
            self.feedback_bus = self.pc
        elif mi.reg_src == REG_IMM_SHL11:
            self.feedback_bus = (ctx["imm_u21"] << 11) & WORD_MASK
        elif mi.reg_src == REG_IMM_U26:
            self.feedback_bus = ctx["imm_u26"]
        elif mi.reg_src == REG_IMM_U21:
            self.feedback_bus = ctx["imm_u21"]

        if mi.v_reg_we:
            if mi.v_reg_src == 1:
                self.vregs.write(rd, [self.mdr], lane=mi.lane_sel)
            elif v_alu_out is not None:
                self.vregs.write(rd, v_alu_out)

        if mi.reg_we:
            self.regs.write(rd, self.feedback_bus)

        if mi.pc_src:
            name = ctx["name"]
            if name in {"BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU", "BLE", "BGT", "BLEU", "BGTU"}:
                take_branch = False
                if name == "BEQ":
                    take_branch = self.br_flags["eq"]
                elif name == "BNE":
                    take_branch = not self.br_flags["eq"]
                elif name == "BLT":
                    take_branch = self.br_flags["lt"]
                elif name == "BGE":
                    take_branch = not self.br_flags["lt"]
                elif name == "BLTU":
                    take_branch = self.br_flags["ltu"]
                elif name == "BGEU":
                    take_branch = not self.br_flags["ltu"]
                elif name == "BLE":
                    take_branch = self.br_flags["lt"] or self.br_flags["eq"]
                elif name == "BGT":
                    take_branch = not (self.br_flags["lt"] or self.br_flags["eq"])
                elif name == "BLEU":
                    take_branch = self.br_flags["ltu"] or self.br_flags["eq"]
                elif name == "BGTU":
                    take_branch = not (self.br_flags["ltu"] or self.br_flags["eq"])
                if not take_branch:
                    return False
            self.pc = self.feedback_bus

        return False
