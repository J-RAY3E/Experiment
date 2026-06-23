from dataclasses import dataclass

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


_UROM: list[MI] = [
    # 00 FETCH
    MI(ir_we=True, pc_inc=True, br_type=2),
    # 01 R_EX
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="ADD", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 02 I_EX  (reserved - dispatched individually)
    MI(br_type=3),
    # 03 L_EX1
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, br_type=0),
    # 04 L_EX2
    MI(mem_rd=True, br_type=1, addr=17),
    # 05 S_EX1
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, br_type=1, addr=18),
    # 06 B_EX  (branch)
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, alu_op="ADD", reg_src=REG_ALU, pc_src=True, br_type=3),
    # 07 J_EX
    MI(reg_src=REG_IMM_U26, pc_src=True, br_type=3),
    # 08 JL_EX1
    MI(reg_we=True, reg_src=REG_PC, br_type=1, addr=24),
    # 09 JR_EX
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", reg_src=REG_ALU, pc_src=True, br_type=3),
    # 0A U_EX
    MI(reg_we=True, reg_src=REG_IMM_SHL11, br_type=3),
    # 0B NOP_EX
    MI(br_type=3),
    # 0C HALT_EX
    MI(halt=True),
    # 0D V_EX  (reserved - dispatched individually)
    MI(br_type=3),
    # 0E VLD_EX
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=25),
    # 0F (reserved)
    MI(br_type=3),
    # 10 VST_EX1
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, vbase_we=True, vbase_sel=False, br_type=1, addr=20),
    # 11 L_EX3
    MI(reg_we=True, reg_src=REG_MEM, br_type=3),
    # 12 S_EX2
    MI(mem_wr=True, br_type=3),
    # 13 VLD_W3
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=3, br_type=3),
    # 14 VST_W0
    MI(mem_wr=True, mem_data_src=1, lane_sel=0, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=21),
    # 15 VST_W1
    MI(mem_wr=True, mem_data_src=1, lane_sel=1, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=22),
    # 16 VST_W2
    MI(mem_wr=True, mem_data_src=1, lane_sel=2, addr_sel=True, vbase_we=True, vbase_sel=True, br_type=1, addr=23),
    # 17 VST_W3
    MI(mem_wr=True, mem_data_src=1, lane_sel=3, addr_sel=True, br_type=3),
    # 18 JL_EX2
    MI(reg_src=REG_IMM_U21, pc_src=True, br_type=3),
    # 19 VLD_W0
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=0, vbase_we=True, vbase_sel=True, br_type=1, addr=26),
    # 1A VLD_W1
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=1, vbase_we=True, vbase_sel=True, br_type=1, addr=27),
    # 1B VLD_W2
    MI(mem_rd=True, addr_sel=True, v_reg_we=True, v_reg_src=1, lane_sel=2, vbase_we=True, vbase_sel=True, br_type=1, addr=19),
    # 1C R_EX_SUB
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SUB", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 1D R_EX_MUL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="MUL", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 1E R_EX_MULH
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="MULH", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 1F R_EX_DIV
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="DIV", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 20 R_EX_REM
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="REM", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 21 R_EX_AND
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="AND", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 22 R_EX_OR
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="OR", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 23 R_EX_XOR
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="XOR", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 24 R_EX_NOT
    MI(a_sel=A_RS1, b_sel=B_ZERO, alu_exec=True, alu_op="NOT", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 25 R_EX_SLL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SLL", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 26 R_EX_SRL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SRL", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 27 R_EX_SRA
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SRA", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 28 R_EX_SLT
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SLT", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 29 I_EX_ADDI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2A I_EX_ANDI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="AND", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2B I_EX_ORI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="OR", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2C I_EX_XORI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="XOR", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2D I_EX_SLLI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="SLL", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2E I_EX_SRLI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="SRL", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 2F I_EX_SRAI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="SRA", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 30 I_EX_SLTI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="SLT", reg_we=True, reg_src=REG_ALU, br_type=3),
    # 31 L_EX1_BYTE
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, br_type=1, addr=50),
    # 32 L_EX2_BYTE
    MI(mem_rd=True, mem_byte=True, br_type=1, addr=17),
    # 33 S_EX1_BYTE
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, alu_op="ADD", mar_we=True, br_type=1, addr=52),
    # 34 S_EX2_BYTE
    MI(mem_wr=True, mem_byte=True, br_type=3),
    # 35 V_EX_ADD
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="ADD", br_type=3),
    # 36 V_EX_SUB
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SUB", br_type=3),
    # 37 V_EX_MUL
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="MUL", br_type=3),
    # 38 V_EX_DIV
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="DIV", br_type=3),
    # 39 V_EX_CMP
    MI(valu_exec=True, v_reg_we=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, alu_op="SUB", br_type=3),
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
    "R_EX_SUB",
    "R_EX_MUL",
    "R_EX_MULH",
    "R_EX_DIV",
    "R_EX_REM",
    "R_EX_AND",
    "R_EX_OR",
    "R_EX_XOR",
    "R_EX_NOT",
    "R_EX_SLL",
    "R_EX_SRL",
    "R_EX_SRA",
    "R_EX_SLT",
    "I_EX_ADDI",
    "I_EX_ANDI",
    "I_EX_ORI",
    "I_EX_XORI",
    "I_EX_SLLI",
    "I_EX_SRLI",
    "I_EX_SRAI",
    "I_EX_SLTI",
    "L_EX1_BYTE",
    "L_EX2_BYTE",
    "S_EX1_BYTE",
    "S_EX2_BYTE",
    "V_EX_ADD",
    "V_EX_SUB",
    "V_EX_MUL",
    "V_EX_DIV",
    "V_EX_CMP",
]

DISPATCH = {
    "ADD": 1,
    "SUB": 28,
    "MUL": 29,
    "MULH": 30,
    "DIV": 31,
    "REM": 32,
    "AND": 33,
    "OR": 34,
    "XOR": 35,
    "NOT": 36,
    "SLL": 37,
    "SRL": 38,
    "SRA": 39,
    "SLT": 40,
    "ADDI": 41,
    "ANDI": 42,
    "ORI": 43,
    "XORI": 44,
    "SLLI": 45,
    "SRLI": 46,
    "SRAI": 47,
    "SLTI": 48,
    "LW": 3,
    "LB": 49,
    "SW": 5,
    "SB": 51,
    "BEQ": 6,
    "BNE": 6,
    "BLT": 6,
    "BLE": 6,
    "BGT": 6,
    "BGE": 6,
    "BGTU": 6,
    "BLEU": 6,
    "J": 7,
    "JAL": 8,
    "JR": 9,
    "LUI": 10,
    "NOP": 11,
    "HALT": 12,
    "VADD": 53,
    "VSUB": 54,
    "VMUL": 55,
    "VDIV": 56,
    "VCMP": 57,
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
        return _UROM[self.ar]

    def advance(self, ir: int) -> None:
        mi = _UROM[self.ar]
        if mi.halt:
            return
        if mi.br_type == 0:
            self.ar += 1
        elif mi.br_type == 1:
            self.ar = mi.addr
        elif mi.br_type == 2:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            self.ar = DISPATCH.get(name, DISPATCH["NOP"])
        elif mi.br_type == 3:
            self.ar = 0
