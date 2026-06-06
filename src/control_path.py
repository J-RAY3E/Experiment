"""
ControlPath: Horizontal microcoded control unit for RISC-IV.
"""

from dataclasses import dataclass, replace
from typing import Any

from src.isa import OPCODE_MASK, OPCODE_NAMES, OPCODE_SHIFT

# ── Mux select constants ─────────────────────────────────────────────────────
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
    ir_we: bool = False  # load IR from instr_mem[PC]
    pc_inc: bool = False  # PC ← PC + 1
    pc_src: bool = False  # MUX_PC: 0=PC+1, 1=load from feedback_bus

    a_sel: int = A_NONE  # MUX_ALU_SRC1 select
    b_sel: int = B_NONE  # MUX_ALU_SRC2 select
    alu_op: str = ""  # ALU operation
    alu_exec: bool = False  # enable ALU computation

    mar_we: bool = False  # load MAR from ALU_OUT
    mem_rd: bool = False  # memory read enable
    mem_wr: bool = False  # memory write enable
    mem_byte: bool = False  # byte access mode
    check_out: bool = False  # address may be OUT_PORT

    reg_we: bool = False  # register file write enable
    reg_src: int = REG_NONE  # MUX_WB select (feedback bus source)

    valu_exec: bool = False  # enable vector ALU execution
    mem_data_src: int = 0  # MUX store data: 0=scalar(r2), 1=vector(VRF)
    v_reg_we: bool = False  # write enable for VRF
    v_reg_src: int = 0  # MUX VRF input: 0=ALU_V_Out, 1=MDR
    lane_sel: int = 0  # lane selector 0..3 for per-lane VRF writes

    vbase_we: bool = False  # write enable for Vbase register
    addr_sel: bool = False  # MUX address: 0=MAR, 1=Vbase
    vbase_sel: bool = False  # MUX Vbase input: 0=MAR, 1=Vbase+1

    halt: bool = False  # halt the machine

    @property
    def mir_word(self) -> int:
        """Compact 64-bit representation of control signals for logging."""
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
        # Upper 32 bits (new vector signals)
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
    # 0: FETCH
    MI(ir_we=True, pc_inc=True, br_type=2),
    # 1: R_EX -> ALU(r1, r2) -> RF(rd)
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2: I_EX -> ALU(r1, imm) -> RF(rd)
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),
    # 3: L_EX1 -> addr = r1 + imm; MAR = ALU_OUT
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, br_type=0),
    # 4: L_EX2 -> MDR = MEM[MAR]
    MI(mem_rd=True, br_type=1, addr=17),
    # 5: S_EX1 -> addr = r1 + imm; MAR = ALU_OUT
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, br_type=1, addr=18),
    # 6: B_EX -> ALU_OUT = PC + imm; feedback_bus = ALU_OUT; PC = feedback_bus (if cond)
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),
    # 7: J_EX -> feedback_bus = imm_u26; PC = feedback_bus
    MI(reg_src=REG_IMM_U26, pc_src=True, br_type=3),
    # 8: JL_EX1 -> Link: RF[rd] = PC (already PC+1); Step to Jump
    MI(reg_we=True, reg_src=REG_PC, br_type=1, addr=24),
    # 9: JR_EX -> ALU(r1, imm) -> feedback_bus; PC = feedback_bus
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),
    # 10: U_EX -> RF[rd] = imm << 11
    MI(reg_we=True, reg_src=REG_IMM_SHL11, br_type=3),
    # 11: NOP_EX
    MI(br_type=3),
    # 12: HALT_EX
    MI(halt=True),
    # 13: V_EX — vector ALU: lanes compute, result → VRF
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, br_type=3),
    # 14: VLD_EX — addr = rs1 + imm → MAR, vbase = MAR, jump to VLD_W0 (25)
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=25),
    # 15: (reserved)
    MI(br_type=3),
    # 16: VST_EX1 — address = rs1 + imm → MAR, vbase = MAR
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=20),
    # 17: L_EX3 -> RF[rd] = MDR
    MI(reg_we=True, reg_src=REG_MEM, br_type=3),
    # 18: S_EX2 -> MEM[MAR] = r2
    MI(mem_wr=True, check_out=True, br_type=3),
    # 19: VLD_W3 — MDR = MEM[vbase], VRF[rd][3] = MDR (last lane)
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=3, br_type=3),
    # 20: VST_W0 — MEM[vbase] = VRF[rd][0], vbase++
    MI(mem_wr=True, mem_data_src=1, lane_sel=0, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=21),
    # 21: VST_W1 — MEM[vbase] = VRF[rd][1], vbase++
    MI(mem_wr=True, mem_data_src=1, lane_sel=1, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=22),
    # 22: VST_W2 — MEM[vbase] = VRF[rd][2], vbase++
    MI(mem_wr=True, mem_data_src=1, lane_sel=2, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=23),
    # 23: VST_W3 — MEM[vbase] = VRF[rd][3]
    MI(mem_wr=True, mem_data_src=1, lane_sel=3, addr_sel=True, br_type=3),
    # 24: JL_EX2 -> feedback_bus = imm_u21; PC = feedback_bus
    MI(reg_src=REG_IMM_U21, pc_src=True, br_type=3),
    # 25: VLD_W0 — MDR = MEM[vbase], VRF[rd][0] = MDR, vbase++
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=0, vbase_we=True, vbase_sel=True, br_type=1, addr=26),
    # 26: VLD_W1 — MDR = MEM[vbase], VRF[rd][1] = MDR, vbase++
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=1, vbase_we=True, vbase_sel=True, br_type=1, addr=27),
    # 27: VLD_W2 — MDR = MEM[vbase], VRF[rd][2] = MDR, vbase++
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


class Microsequencer:
    def __init__(self) -> None:
        self.upc: int = 0

    def current_mi(self, ir: int) -> MI:
        mi = _UROM[self.upc]
        patches: dict[str, Any] = {}
        if mi.alu_exec:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            if not mi.alu_op:
                patches["alu_op"] = _ALU_OPS.get(name, "ADD")
            if mi.mem_rd or mi.mem_wr:
                patches["mem_byte"] = name in ("LB", "SB")
            if name == "NOT":
                patches["b_sel"] = B_ZERO
        return replace(mi, **patches) if patches else mi

    def advance(self, ir: int) -> None:
        mi = _UROM[self.upc]
        if mi.halt:
            return
        if mi.br_type == 0:
            self.upc += 1
        elif mi.br_type == 1:
            self.upc = mi.addr
        elif mi.br_type == 2:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            fmt = _NAME_TO_FMT.get(name, "NOP")
            self.upc = DISPATCH.get(fmt, DISPATCH["NOP"])
        elif mi.br_type == 3:
            self.upc = 0


class ControlPath:
    def __init__(self) -> None:
        self.seq = Microsequencer()

    @property
    def halted(self) -> bool:
        return _UROM[self.seq.upc].halt

    @property
    def phase_name(self) -> str:
        return UROM_NAMES[self.seq.upc] if self.seq.upc < len(UROM_NAMES) else f"U{self.seq.upc}"

    @property
    def upc(self) -> int:
        return self.seq.upc

    def current_mi(self, ir: int) -> MI:
        return self.seq.current_mi(ir)

    def advance(self, ir: int) -> None:
        self.seq.advance(ir)
