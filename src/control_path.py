from dataclasses import dataclass

from src.isa import OPCODE_MASK, OPCODE_SHIFT, SIGN_BIT, WORD_MASK

BRANCH_NAMES = {"BEQ", "BNE", "BLT", "BGE", "BLTU", "BGEU", "BGT", "BLE", "BGTU", "BLEU"}
SIGN_EXT_NEG = ~0x7FFFFFFF

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
REG_IMM20: int = 4
REG_IMM26: int = 5
REG_IMM21: int = 6


@dataclass
class MI:
    ir_we: bool = False
    pc_src: bool = False

    a_sel: int = A_NONE
    b_sel: int = B_NONE
    alu_exec: bool = False

    mar_we: bool = False
    mem_rd: bool = False
    mem_wr: bool = False
    mem_byte: bool = False

    reg_we: bool = False
    reg_src: int = REG_NONE

    halt: bool = False
    br_type: int = 3
    addr: int = 0

    @property
    def mir_word(self) -> int:
        w = 0
        if self.ir_we:
            w |= 1 << 0
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
        if self.halt:
            w |= 1 << 19
        w |= (self.br_type & 0x3) << 20
        w |= (self.addr & 0xFF) << 22
        return w


_MAP: list[int] = [2] * 64

_MAP[0x00] = 2  # NOP
_MAP[0x01] = 3  # LW
_MAP[0x02] = 5  # SW
_MAP[0x03] = 6  # LB
_MAP[0x04] = 8  # SB
_MAP[0x05] = 9  # LUI
_MAP[0x06] = 10  # ADD
_MAP[0x07] = 11  # SUB
_MAP[0x08] = 12  # MUL
_MAP[0x09] = 13  # DIV
_MAP[0x0A] = 14  # REM
_MAP[0x0B] = 15  # MULH
_MAP[0x0C] = 16  # AND
_MAP[0x0D] = 17  # OR
_MAP[0x0E] = 18  # XOR
_MAP[0x0F] = 19  # NOT
_MAP[0x10] = 20  # SLL
_MAP[0x11] = 21  # SRL
_MAP[0x12] = 22  # SRA
_MAP[0x13] = 23  # SLT
_MAP[0x14] = 24  # ADDI
_MAP[0x15] = 25  # ANDI
_MAP[0x16] = 26  # ORI
_MAP[0x17] = 27  # XORI
_MAP[0x18] = 28  # SLLI
_MAP[0x19] = 29  # SRLI
_MAP[0x1A] = 30  # SRAI
_MAP[0x1B] = 31  # SLTI
_MAP[0x20] = 32  # BEQ
_MAP[0x21] = 33  # BNE
_MAP[0x22] = 34  # BLT
_MAP[0x23] = 35  # BLE
_MAP[0x24] = 36  # BGT
_MAP[0x25] = 37  # BGE
_MAP[0x26] = 38  # BGTU
_MAP[0x27] = 39  # BLEU
_MAP[0x28] = 40  # J
_MAP[0x29] = 41  # JAL
_MAP[0x2A] = 43  # JR
_MAP[0x3F] = 44  # HALT

_UROM: list[MI] = [
    MI(a_sel=A_PC, b_sel=B_ZERO, alu_exec=True, mar_we=True, br_type=0),  # 0: FETCH
    MI(ir_we=True, br_type=2),  # 1: DECODE
    MI(br_type=3),  # 2: NOP
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, mem_rd=True, br_type=0),  # 3: LW_EXEC
    MI(reg_we=True, reg_src=REG_MEM, br_type=3),  # 4: LW_WB
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, mem_wr=True, br_type=3),  # 5: SW
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, mem_rd=True, mem_byte=True, br_type=0),  # 6: LB_EXEC
    MI(reg_we=True, reg_src=REG_MEM, br_type=3),  # 7: LB_WB
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, mem_wr=True, mem_byte=True, br_type=3),  # 8: SB
    MI(reg_we=True, reg_src=REG_IMM20, br_type=3),  # 9: LUI
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 10: ADD
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 11: SUB
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 12: MUL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 13: DIV
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 14: REM
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 15: MULH
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 16: AND
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 17: OR
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 18: XOR
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 19: NOT
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 20: SLL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 21: SRL
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 22: SRA
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 23: SLT
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 24: ADDI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 25: ANDI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 26: ORI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 27: XORI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 28: SLLI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 29: SRLI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 30: SRAI
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_we=True, reg_src=REG_ALU, br_type=3),  # 31: SLTI
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 32: BEQ
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 33: BNE
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 34: BLT
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 35: BLE
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 36: BGT
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 37: BGE
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 38: BGTU
    MI(a_sel=A_PC, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 39: BLEU
    MI(pc_src=True, br_type=3),  # 40: J
    MI(reg_we=True, reg_src=REG_PC, br_type=0),  # 41: JAL_EXEC
    MI(pc_src=True, br_type=3),  # 42: JAL_WB
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, reg_src=REG_ALU, pc_src=True, br_type=3),  # 43: JR
    MI(halt=True),  # 44: HALT
]

_PHASE_NAMES: list[str] = [
    "FETCH",
    "DECODE",
    "NOP",
    "LW_EXEC",
    "LW_WB",
    "SW",
    "LB_EXEC",
    "LB_WB",
    "SB",
    "LUI",
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
    "ADDI",
    "ANDI",
    "ORI",
    "XORI",
    "SLLI",
    "SRLI",
    "SRAI",
    "SLTI",
    "BEQ",
    "BNE",
    "BLT",
    "BLE",
    "BGT",
    "BGE",
    "BGTU",
    "BLEU",
    "J",
    "JAL_EXEC",
    "JAL_WB",
    "JR",
    "HALT",
]


class ControlPath:
    def __init__(self) -> None:
        self.ar: int = 0
        self._take_pc: bool = True

    @property
    def halted(self) -> bool:
        return _UROM[self.ar].halt

    @staticmethod
    def _to_signed(v: int) -> int:
        return v if not (v & SIGN_BIT) else v | SIGN_EXT_NEG

    @property
    def phase_name(self) -> str:
        if 0 <= self.ar < len(_PHASE_NAMES):
            return _PHASE_NAMES[self.ar]
        return f"UPC_{self.ar}"

    @property
    def upc(self) -> int:
        return self.ar

    @upc.setter
    def upc(self, value: int) -> None:
        self.ar = value

    def current_mi(self) -> MI:
        return _UROM[self.ar]

    @property
    def take_pc(self) -> bool:
        return self._take_pc

    def evaluate_branch(self, name: str, r1: int, r2: int) -> None:
        u1, u2 = r1 & WORD_MASK, r2 & WORD_MASK
        s1, s2 = ControlPath._to_signed(r1), ControlPath._to_signed(r2)
        eq = u1 == u2
        lt = s1 < s2
        ltu = u1 < u2
        if name in BRANCH_NAMES:
            if name == "BEQ":
                self._take_pc = eq
            elif name == "BNE":
                self._take_pc = not eq
            elif name == "BLT":
                self._take_pc = lt
            elif name == "BGE":
                self._take_pc = not lt
            elif name == "BLTU":
                self._take_pc = ltu
            elif name == "BGEU":
                self._take_pc = not ltu
            elif name == "BLE":
                self._take_pc = lt or eq
            elif name == "BGT":
                self._take_pc = not (lt or eq)
            elif name == "BLEU":
                self._take_pc = ltu or eq
            elif name == "BGTU":
                self._take_pc = not (ltu or eq)
            else:
                self._take_pc = True
        else:
            self._take_pc = True

    def advance(self, ir: int) -> None:
        mi = _UROM[self.ar]
        if mi.halt:
            return
        if mi.br_type == 0:
            self.ar += 1
        elif mi.br_type == 1:
            self.ar = mi.addr
        elif mi.br_type == 2:
            opcode = (ir >> OPCODE_SHIFT) & OPCODE_MASK
            self.ar = _MAP[opcode]
        elif mi.br_type == 3:
            self.ar = 0
