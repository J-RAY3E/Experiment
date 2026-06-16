from dataclasses import dataclass, replace
from typing import Any

from src.isa import OPCODE_MASK, OPCODE_NAMES, OPCODE_SHIFT

A_NONE: int = 0
A_RS1: int = 1
A_PC: int = 2

B_NONE: int = 0
B_RS2: int = 1
B_IMM: int = 2
B_ZERO: int = 3

REG_NONE: int = 0
REG_ALU: int = 1
REG_MEM: int = 2
REG_PC: int = 3
REG_IMM_SHL11: int = 4
REG_IMM_U26: int = 5
REG_IMM_U21: int = 6


@dataclass
class MI:
    ir_we: bool = False
    pc_inc: bool = False
    pc_src: bool = False

    a_sel: int = A_NONE
    b_sel: int = B_NONE
    alu_op: str = ""
    alu_exec: bool = False

    mar_we: bool = False
    mem_rd: bool = False
    mem_wr: bool = False
    mem_byte: bool = False

    reg_we: bool = False
    reg_src: int = REG_NONE

    valu_exec: bool = False
    mem_data_src: int = 0
    v_reg_we: bool = False
    v_reg_src: int = 0
    lane_sel: int = 0

    vbase_we: bool = False
    addr_sel: bool = False
    vbase_sel: bool = False

    halt: bool = False

    @property
    def mir_word(self) -> int:
        w = 0
        if self.ir_we:
            w |= 1 << 0
        if self.pc_inc:
            w |= 1 << 1
        if self.pc_src:
            w |= 1 << 2
        w |= (self.a_sel & 0x3) << 5
        w |= (self.b_sel & 0x3) << 7
        if self.alu_exec:
            w |= 1 << 9
        if self.mar_we:
            w |= 1 << 10
        if self.mem_rd:
            w |= 1 << 11
        if self.mem_wr:
            w |= 1 << 12
        if self.mem_byte:
            w |= 1 << 13
        if self.reg_we:
            w |= 1 << 14
        w |= (self.reg_src & 0x7) << 15
        if self.valu_exec:
            w |= 1 << 18
        if self.halt:
            w |= 1 << 19
        if self.vbase_we:
            w |= 1 << 3
        if self.addr_sel:
            w |= 1 << 4
        if self.vbase_sel:
            w |= 1 << 30
        w |= (self.br_type & 0x3) << 20
        w |= (self.addr & 0xFF) << 22
        if self.v_reg_we:
            w |= 1 << 32
        if self.v_reg_src:
            w |= 1 << 33
        w |= (self.lane_sel & 0x3) << 34
        if self.mem_data_src:
            w |= 1 << 36
        return w

    br_type: int = 3
    addr: int = 0


OPCODE_FORMATS: dict[str, set[str]] = {
    "R": {
        "ADD",
        "SUB",
        "MUL",
        "DIV",
        "REM",
        "MULH",
        "AND",
        "OR",
        "XOR",
        "NOT",
        "SLL",
        "SRL",
        "SRA",
        "SLT",
    },
    "I": {"ADDI", "ANDI", "ORI", "XORI", "SLLI", "SRLI", "SRAI", "SLTI"},
    "L": {"LW", "LB"},
    "S": {"SW", "SB"},
    "B": {"BEQ", "BNE", "BLT", "BLE", "BGT", "BGE", "BGTU", "BLEU"},
    "J": {"J"},
    "JL": {"JAL"},
    "JR": {"JR"},
    "U": {"LUI"},
    "NOP": {"NOP"},
    "HALT": {"HALT"},
    "V": {"VADD", "VSUB", "VMUL", "VDIV", "VCMP"},
    "VLD": {"VLD"},
    "VST": {"VST"},
}

_NAME_TO_FMT: dict[str, str] = {n: f for f, ns in OPCODE_FORMATS.items() for n in ns}

_ALU_OPS: dict[str, str] = {
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
    "LW": "ADD",
    "LB": "ADD",
    "SW": "ADD",
    "SB": "ADD",
    "BEQ": "ADD",
    "BNE": "ADD",
    "VADD": "ADD",
    "VSUB": "SUB",
    "VMUL": "MUL",
    "VDIV": "DIV",
    "VCMP": "SUB",
    "VLD": "ADD",
    "VST": "ADD",
}
_UROM: list[MI] = [
    MI(ir_we=True, pc_inc=True, br_type=2),
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, br_type=0),
    MI(mem_rd=True, br_type=1, addr=17),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, br_type=1, addr=18),
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),
    MI(reg_src=REG_IMM_U26, pc_src=True, br_type=3),
    MI(reg_we=True, reg_src=REG_PC, br_type=1, addr=24),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),
    MI(reg_we=True, reg_src=REG_IMM_SHL11, br_type=3),
    MI(br_type=3),
    MI(halt=True),
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, br_type=3),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=25),
    MI(br_type=3),
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=20),
    MI(reg_we=True, reg_src=REG_MEM, br_type=3),
    MI(mem_wr=True, br_type=3),
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=3, br_type=3),
    MI(mem_wr=True, mem_data_src=1, lane_sel=0, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=21),
    MI(mem_wr=True, mem_data_src=1, lane_sel=1, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=22),
    MI(mem_wr=True, mem_data_src=1, lane_sel=2, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=23),
    MI(mem_wr=True, mem_data_src=1, lane_sel=3, addr_sel=True, br_type=3),
    MI(reg_src=REG_IMM_U21, pc_src=True, br_type=3),
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=0, vbase_we=True, vbase_sel=True, br_type=1, addr=26),
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=1, vbase_we=True, vbase_sel=True, br_type=1, addr=27),
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=2, vbase_we=True, vbase_sel=True, br_type=1, addr=19),
]

UROM_NAMES = [
    "FETCH",
    "R_EX",
    "I_EX",
    "L_EX1",
    "L_EX2",
    "S_EX1",
    "B_EX",
    "J_EX",
    "JL_EX1",
    "JR_EX",
    "U_EX",
    "NOP_EX",
    "HALT_EX",
    "V_EX",
    "VLD_EX",
    "(reserved)",
    "VST_EX1",
    "L_EX3",
    "S_EX2",
    "VLD_W3",
    "VST_W0",
    "VST_W1",
    "VST_W2",
    "VST_W3",
    "JL_EX2",
    "VLD_W0",
    "VLD_W1",
    "VLD_W2",
]

DISPATCH = {
    "R": 1,
    "I": 2,
    "L": 3,
    "S": 5,
    "B": 6,
    "J": 7,
    "JL": 8,
    "JR": 9,
    "U": 10,
    "NOP": 11,
    "HALT": 12,
    "V": 13,
    "VLD": 14,
    "VST": 16,
}


class ControlPath:
    def __init__(self) -> None:
        self.ar: int = 0

    @property
    def halted(self) -> bool:
        return _UROM[self.ar].halt

    @property
    def phase_name(self) -> str:
        return UROM_NAMES[self.ar] if self.ar < len(UROM_NAMES) else f"U{self.ar}"

    @property
    def upc(self) -> int:
        return self.ar

    @upc.setter
    def upc(self, value: int) -> None:
        self.ar = value

    def current_mi(self, ir: int) -> MI:
        """Read uROM at AR, then decode variable signals from instruction opcode."""
        mi = _UROM[self.ar]
        if not mi.alu_exec and not mi.mem_rd and not mi.mem_wr:
            return mi

        name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
        decoded: dict[str, Any] = {}

        if mi.alu_exec and not mi.alu_op:
            decoded["alu_op"] = _ALU_OPS.get(name, "ADD")

        if mi.mem_rd or mi.mem_wr:
            decoded["mem_byte"] = name in ("LB", "SB")

        if name == "NOT":
            decoded["b_sel"] = B_ZERO

        return replace(mi, **decoded)

    def advance(self, ir: int) -> None:
        """
        MUX: select next AR value based on br_type from current uROM word.

        br_type=0 → AR+1       (sequential)
        br_type=1 → uROM.addr  (jump to microword)
        br_type=2 → MAPPER     (dispatch: opcode → start address)
        br_type=3 → 0          (back to FETCH)
        """
        mi = _UROM[self.ar]
        if mi.halt:
            return
        if mi.br_type == 0:
            self.ar += 1
        elif mi.br_type == 1:
            self.ar = mi.addr
        elif mi.br_type == 2:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            fmt = _NAME_TO_FMT.get(name, "NOP")
            self.ar = DISPATCH.get(fmt, DISPATCH["NOP"])
        elif mi.br_type == 3:
            self.ar = 0
