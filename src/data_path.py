from collections.abc import Callable
from typing import Any

from src.control_unit import (
    A_PC,
    B_IMM,
    B_IMM21,
    B_IMM26,
    B_ZERO,
    MI,
    REG_ALU,
    REG_IMM20,
    REG_IMM21,
    REG_IMM26,
    REG_MEM,
    REG_PC,
    ControlPath,
)
from src.isa import (
    DATA_MEM_SIZE,
    IN_PORT,
    NUM_REGS,
    OUT_PORT,
    SIGN_BIT,
    WORD_MASK,
    decode,
)

BYTE_MASK = 0xFF
BYTE_SIGN = 0x80
SHIFT_MASK = 0x1F
SIGN_EXT_NEG = ~0x7FFFFFFF

ALU_OP_MAP = {
    "ADD": "ADD",
    "SUB": "SUB",
    "MUL": "MUL",
    "DIV": "DIV",
    "REM": "REM",
    "MULH": "MULH",
    "AND": "AND",
    "OR": "OR",
    "XOR": "XOR",
    "NOT": "NOT",
    "SLL": "SLL",
    "SRL": "SRL",
    "SRA": "SRA",
    "SLT": "SLT",
    "ADDI": "ADD",
    "ANDI": "AND",
    "ORI": "OR",
    "XORI": "XOR",
    "SLLI": "SLL",
    "SRLI": "SRL",
    "SRAI": "SRA",
    "SLTI": "SLT",
}


def _to_signed(v: int) -> int:
    return v if not (v & SIGN_BIT) else v | SIGN_EXT_NEG


class RegisterFile:
    def __init__(self) -> None:
        self.regs = [0] * NUM_REGS

    def read(self, addr: int) -> int:
        return 0 if addr == 0 else self.regs[addr]

    def write(self, addr: int, value: int) -> None:
        if addr != 0:
            self.regs[addr] = value & WORD_MASK


class ALU:
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
        if 0 <= addr < len(self.mem) - 3:
            return (
                self.mem[addr] | (self.mem[addr + 1] << 8) | (self.mem[addr + 2] << 16) | (self.mem[addr + 3] << 24)
            ) & WORD_MASK
        return 0

    def load_byte(self, addr: int) -> int:
        addr &= WORD_MASK
        if addr == IN_PORT:
            return self._read_input() if self._read_input else 0
        val = self.mem[addr] if 0 <= addr < len(self.mem) else 0
        return (val | ~BYTE_MASK) & WORD_MASK if val & BYTE_SIGN else val

    def store_word(self, addr: int, value: int) -> None:
        addr &= WORD_MASK
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem) - 3:
            self.mem[addr] = value & 0xFF
            self.mem[addr + 1] = (value >> 8) & 0xFF
            self.mem[addr + 2] = (value >> 16) & 0xFF
            self.mem[addr + 3] = (value >> 24) & 0xFF

    def store_byte(self, addr: int, value: int) -> None:
        addr &= WORD_MASK
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem):
            self.mem[addr] = value & 0xFF


class DataPath:
    def __init__(self, input_stream: str = "", cp: ControlPath | None = None) -> None:
        self.regs = RegisterFile()
        self.alu = ALU()
        self.mem = DataMemory()
        self.cp = cp or ControlPath()

        self.pc: int = 0
        self.ir: int = 0
        self.a: int = 0
        self.b: int = 0
        self.mar: int = 0
        self.mdr: int = 0
        self.alu_out: int = 0
        self.feedback_bus: int = 0

        self._ctx: dict[str, Any] = decode(0)

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

    def tick(self, mi: MI, inst_word: int | None = None) -> bool:
        if mi.ir_we:
            if inst_word is not None:
                self.ir = inst_word
            self._ctx = decode(self.ir)
            self.pc = (self.pc + 4) & WORD_MASK
            return False

        if mi.halt:
            return True

        ctx = self._ctx
        name = ctx.get("name", "")
        rs1, rs2, rd = ctx["rs1"], ctx["rs2"], ctx["rd"]

        r1_data = self.regs.read(rs1)
        r2_data = self.regs.read(rs2)
        self.cp.evaluate_branch(name, r1_data, r2_data)

        self.a = self.pc if mi.a_sel == A_PC else r1_data
        if mi.b_sel == B_IMM:
            self.b = ctx["imm_s"]
        elif mi.b_sel == B_IMM26:
            imm = ctx["imm_u26"]
            if imm & (1 << 25):
                imm |= 0xFC000000  # sign-extend 26→32 bits
            self.b = imm
        elif mi.b_sel == B_IMM21:
            imm = ctx["imm_u21"]
            if imm & (1 << 20):
                imm |= 0xFFF00000  # sign-extend 21→32 bits
            self.b = imm
        elif mi.b_sel == B_ZERO:
            self.b = 0
        else:
            self.b = r2_data

        if mi.alu_exec:
            name = self._ctx.get("name", "")
            alu_op = ALU_OP_MAP.get(name, "ADD")
            self.alu_out = self.alu.execute(alu_op, self.a, self.b)

        if mi.mar_we:
            self.mar = self.alu_out

        mem_addr = self.mar

        if mi.mem_rd:
            mem_byte = mi.mem_byte or ctx.get("name", "") == "LB"
            self.mdr = self.mem.load_byte(mem_addr) if mem_byte else self.mem.load_word(mem_addr)

        if mi.mem_wr:
            data = r2_data
            mem_byte = mi.mem_byte or ctx.get("name", "") == "SB"
            if mem_byte:
                self.mem.store_byte(mem_addr, data)
            else:
                self.mem.store_word(mem_addr, data)

        if mi.reg_src == REG_ALU:
            self.feedback_bus = self.alu_out
        elif mi.reg_src == REG_MEM:
            self.feedback_bus = self.mdr
        elif mi.reg_src == REG_PC:
            self.feedback_bus = self.pc
        elif mi.reg_src == REG_IMM20:
            self.feedback_bus = (ctx["imm_u20"] << 12) & WORD_MASK
        elif mi.reg_src == REG_IMM26:
            self.feedback_bus = ctx["imm_u26"]
        elif mi.reg_src == REG_IMM21:
            self.feedback_bus = ctx["imm_u21"]

        if mi.reg_we:
            self.regs.write(rd, self.feedback_bus)

        if mi.pc_src:
            if not self.cp.take_pc:
                return False
            self.pc = self.feedback_bus

        return False
