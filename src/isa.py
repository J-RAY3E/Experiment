from __future__ import annotations

from typing import Any

OPCODE_MASK = 0x3F
REG_MASK = 0x1F
IMM11_MASK = 0x7FF
IMM11_SIGN = 0x400
IMM12_MASK = 0xFFF
IMM12_SIGN = 0x800
IMM20_MASK = 0xFFFFF
IMM21_MASK = 0x1FFFFF
IMM26_MASK = 0x3FFFFFF
WORD_MASK = 0xFFFFFFFF
SIGN_BIT = 0x80000000

OPCODE_SHIFT = 26
RD_SHIFT = 21
RS1_SHIFT = 16
RS2_SHIFT = 11

IN_PORT = 0xFFFFFFF0
OUT_PORT = 0xFFFFFFF4

NUM_REGS = 32
DATA_MEM_SIZE = 32768
STACK_BASE = 0x8000

OPCODES = {
    "NOP": 0x00,
    "LW": 0x01,
    "SW": 0x02,
    "LB": 0x03,
    "SB": 0x04,
    "LUI": 0x05,
    "ADD": 0x06,
    "SUB": 0x07,
    "MUL": 0x08,
    "DIV": 0x09,
    "REM": 0x0A,
    "MULH": 0x0B,
    "AND": 0x0C,
    "OR": 0x0D,
    "XOR": 0x0E,
    "NOT": 0x0F,
    "SLL": 0x10,
    "SRL": 0x11,
    "SRA": 0x12,
    "SLT": 0x13,
    "ADDI": 0x14,
    "ANDI": 0x15,
    "ORI": 0x16,
    "XORI": 0x17,
    "SLLI": 0x18,
    "SRLI": 0x19,
    "SRAI": 0x1A,
    "SLTI": 0x1B,
    "BEQ": 0x20,
    "BNE": 0x21,
    "BLT": 0x22,
    "BLE": 0x23,
    "BGT": 0x24,
    "BGE": 0x25,
    "BGTU": 0x26,
    "BLEU": 0x27,
    "J": 0x28,
    "JAL": 0x29,
    "JR": 0x2A,
    "HALT": 0x3F,
}

OPCODE_NAMES = {v: k for k, v in OPCODES.items()}

REG_NAMES = [
    "zero",
    "ra",
    "sp",
    "gp",
    "a0",
    "a1",
    "a2",
    "a3",
    "a4",
    "a5",
    "a6",
    "a7",
    "t0",
    "t1",
    "t2",
    "t3",
    "t4",
    "t5",
    "s0",
    "s1",
    "s2",
    "s3",
    "s4",
    "s5",
    "s6",
    "s7",
    "s8",
    "s9",
    "s10",
    "s11",
    "t6",
    "tp",
]

REG = {n: i for i, n in enumerate(REG_NAMES)}

R_FORMAT = {"ADD", "SUB", "MUL", "DIV", "REM", "MULH", "AND", "OR", "XOR", "NOT", "SLL", "SRL", "SRA", "SLT", "NOP"}
I_FORMAT = {"ADDI", "ANDI", "ORI", "XORI", "SLLI", "SRLI", "SRAI", "SLTI"}
L_FORMAT = {"LW", "LB"}
S_FORMAT = {"SW", "SB"}
B_FORMAT = {"BEQ", "BNE", "BLT", "BLE", "BGT", "BGE", "BGTU", "BLEU"}
J_FORMAT = {"J"}
JL_FORMAT = {"JAL"}
JR_FORMAT = {"JR"}
U_FORMAT = {"LUI"}

HALT_WORD = OPCODES["HALT"] << OPCODE_SHIFT


def _sext11(imm: int) -> int:
    return imm | ~IMM11_MASK if imm & IMM11_SIGN else imm


def _sext12(imm: int) -> int:
    return imm | ~IMM12_MASK if imm & IMM12_SIGN else imm


def decode(word: int) -> dict[str, Any]:
    op = (word >> OPCODE_SHIFT) & OPCODE_MASK
    name = OPCODE_NAMES.get(op, "???")
    imm12 = word & IMM12_MASK
    imm11 = word & IMM11_MASK
    imm11_only = name in B_FORMAT or name in S_FORMAT
    return {
        "opcode": op,
        "name": name,
        "word": word,
        "rd": (word >> RD_SHIFT) & REG_MASK,
        "rs1": (word >> RS1_SHIFT) & REG_MASK,
        "rs2": (word >> RS2_SHIFT) & REG_MASK,
        "imm": imm11 if imm11_only else imm12,
        "imm_s": _sext11(imm11) if imm11_only else _sext12(imm12),
        "imm_u20": word & IMM20_MASK,
        "imm_u21": word & IMM21_MASK,
        "imm_u26": word & IMM26_MASK,
    }
