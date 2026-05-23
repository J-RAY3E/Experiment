from enum import Enum, auto
from typing import Any, Callable, Dict, Optional

from src.ISA import OPCODE_NAMES

OPCODE_SHIFT = 26
OPCODE_MASK = 0x3F

FETCH_TOKEN = "FETCH"
HALT_TOKEN = "HALT"

UNKNOWN_OPCODE = "???"

SRC_RS1 = "rs1"
SRC_RS2 = "rs2"
SRC_IMM = "imm"
SRC_ZERO = "zero"
SRC_REG = "reg"
SRC_PC = "pc"

SRC_INC = "inc"
SRC_IR_U26 = "ir_u26"
SRC_IR_U21 = "ir_u21"
SRC_IMM_SHL11 = "imm_shl11"

REG_SRC_ALU = "alu"
REG_SRC_MEM = "mem"
REG_SRC_PC = "pc"
REG_SRC_IMM = "imm_shl11"

ALU_ADD = "ADD"
ALU_SUB = "SUB"
ALU_MUL = "MUL"
ALU_DIV = "DIV"
ALU_REM = "REM"
ALU_MULH = "MULH"
ALU_AND = "AND"
ALU_OR = "OR"
ALU_XOR = "XOR"
ALU_NOT = "NOT"
ALU_SLL = "SLL"
ALU_SRL = "SRL"
ALU_SRA = "SRA"
ALU_SLT = "SLT"
ALU_V_OP = "V_OP"

MEM_VEC_BYTES = 4

FORMAT_R = "R_FORMAT"
FORMAT_I = "I_FORMAT"
FORMAT_L = "L_FORMAT"
FORMAT_S = "S_FORMAT"
FORMAT_B = "B_FORMAT"
FORMAT_J = "J_FORMAT"
FORMAT_JL = "JL_FORMAT"
FORMAT_JR = "JR_FORMAT"
FORMAT_U = "U_FORMAT"
FORMAT_V = "V_FORMAT"
FORMAT_VL = "VL_FORMAT"

R_FORMAT = {
    "ADD", "SUB", "MUL", "DIV", "REM", "MULH", "AND",
    "OR", "XOR", "NOT", "SLL", "SRL", "SRA", "SLT", "NOP"
}
I_FORMAT = {"ADDI", "ANDI", "ORI", "XORI", "SLLI", "SRLI", "SRAI", "SLTI"}
L_FORMAT = {"LW", "LB"}
S_FORMAT = {"SW", "SB"}
B_FORMAT = {"BEQ", "BNE", "BLT", "BLE", "BGT", "BGE", "BGTU", "BLEU"}
J_FORMAT = {"J"}
JL_FORMAT = {"JAL"}
JR_FORMAT = {"JR"}
U_FORMAT = {"LUI"}
V_FORMAT = {"VADD", "VSUB", "VMUL", "VDIV", "VCMP"}
VL_FORMAT = {"VLD", "VST"}

OPCODE_FORMATS = {
    FORMAT_R: R_FORMAT,
    FORMAT_I: I_FORMAT,
    FORMAT_L: L_FORMAT,
    FORMAT_S: S_FORMAT,
    FORMAT_B: B_FORMAT,
    FORMAT_J: J_FORMAT,
    FORMAT_JL: JL_FORMAT,
    FORMAT_JR: JR_FORMAT,
    FORMAT_U: U_FORMAT,
    FORMAT_V: V_FORMAT,
    FORMAT_VL: VL_FORMAT,
}

ALU_OPS = {
    "ADD": ALU_ADD,
    "SUB": ALU_SUB,
    "MUL": ALU_MUL,
    "DIV": ALU_DIV,
    "REM": ALU_REM,
    "MULH": ALU_MULH,
    "AND": ALU_AND,
    "OR": ALU_OR,
    "XOR": ALU_XOR,
    "NOT": ALU_NOT,
    "SLL": ALU_SLL,
    "SRL": ALU_SRL,
    "SRA": ALU_SRA,
    "SLT": ALU_SLT,
    "ADDI": ALU_ADD,
    "ANDI": ALU_AND,
    "ORI": ALU_OR,
    "XORI": ALU_XOR,
    "SLLI": ALU_SLL,
    "SRLI": ALU_SRL,
    "SRAI": ALU_SRA,
    "SLTI": ALU_SLT,
}

DEFAULT_SIGNALS: Dict[str, Any] = {
    "ir_we": False,
    "pc_we": False,
    "pc_src": None,
    "a_sel": None,
    "b_sel": None,
    "alu_op": None,
    "alu_exec": False,
    "reg_we": False,
    "reg_src": None,
    "mem_rd": False,
    "mem_wr": False,
    "mem_byte": False,
    "check_out": False,
    "v_en": False,
    "mem_vec": 0,
    "halt": False,
}

class Phase(Enum):
    FETCH = auto()    # IF  — Instruction Fetch stage
    EXECUTE = auto()  # ID/EX — Decode + Execute stage (Ibex 2-stage model)
    VecOp = auto()   # Multi-cycle vector operation (extends DI_EX for SIMD)
    HALT = auto()

class InstructionFormat(Enum):
    R = auto()
    I_FMT = auto()
    L = auto()
    S = auto()
    B = auto()
    J = auto()
    JL = auto()
    JR = auto()
    U = auto()
    V = auto()
    VL = auto()

    @classmethod
    def from_opcode_name(cls, name: str) -> Optional["InstructionFormat"]:
        for fmt_name, opcode_set in OPCODE_FORMATS.items():
            if name in opcode_set:
                # Need to map I_FORMAT to I_FMT in the Enum
                enum_name = fmt_name.split("_")[0]
                if enum_name == "I":
                    enum_name = "I_FMT"
                return cls[enum_name]
        return None

MicrocodeEntry = Callable[[str, Dict[str, Any]], Dict[str, Any]]

MICROCODE_ROM: Dict[Any, MicrocodeEntry] = {
    (Phase.FETCH, FETCH_TOKEN): lambda name, s: {
        **s,
        "ir_we": True,
        "pc_we": True,
        "pc_src": SRC_INC,
    },

    # DI_EX: when a HALT opcode is decoded, signal halt
    (Phase.EXECUTE, HALT_TOKEN): lambda name, s: {
        **s,
        "halt": True,
    },

    (Phase.HALT, HALT_TOKEN): lambda name, s: {
        **s,
        "halt": True,
    },

    InstructionFormat.R: lambda name, s: s if name == "NOP" else {
        **s,
        "alu_op": name,
        "alu_exec": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_ZERO if name == "NOT" else SRC_RS2,
        "reg_we": True,
        "reg_src": REG_SRC_ALU,
    },

    InstructionFormat.I_FMT: lambda name, s: {
        **s,
        "alu_op": ALU_OPS.get(name, ALU_ADD),
        "alu_exec": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_IMM,
        "reg_we": True,
        "reg_src": REG_SRC_ALU,
    },

    InstructionFormat.L: lambda name, s: {
        **s,
        "alu_op": ALU_ADD,
        "alu_exec": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_IMM,
        "mem_rd": True,
        "reg_we": True,
        "reg_src": REG_SRC_MEM,
        "mem_byte": (name == "LB"),
    },

    InstructionFormat.S: lambda name, s: {
        **s,
        "alu_op": ALU_ADD,
        "alu_exec": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_IMM,
        "mem_wr": True,
        "check_out": True,
        "mem_byte": (name == "SB"),
    },

    InstructionFormat.B: lambda name, s: {
        **s,
        "a_sel": SRC_RS1,
        "b_sel": SRC_RS2,
        "pc_we": True,
        "pc_src": "branch",
    },

    InstructionFormat.J: lambda name, s: {
        **s,
        "pc_we": True,
        "pc_src": SRC_IR_U26,
    },

    InstructionFormat.JL: lambda name, s: {
        **s,
        "reg_we": True,
        "reg_src": REG_SRC_PC,
        "pc_we": True,
        "pc_src": SRC_IR_U21,
    },

    InstructionFormat.JR: lambda name, s: {
        **s,
        "pc_we": True,
        "pc_src": SRC_REG,
    },

    InstructionFormat.U: lambda name, s: {
        **s,
        "reg_we": True,
        "reg_src": SRC_IMM_SHL11,
    },

    InstructionFormat.V: lambda name, s: {
        **s,
        "v_en": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_RS2,
        "alu_exec": True,
        "alu_op": ALU_V_OP,
        "reg_we": True,
        "reg_src": REG_SRC_ALU,
    },

    InstructionFormat.VL: lambda name, s: {
        **s,
        "v_en": True,
        "alu_op": ALU_ADD,
        "alu_exec": True,
        "a_sel": SRC_RS1,
        "b_sel": SRC_IMM,
        "mem_rd": (name == "VLD"),
        "mem_wr": (name == "VST"),
        "mem_vec": MEM_VEC_BYTES,
        **({"reg_we": True, "reg_src": REG_SRC_MEM} if name == "VLD" else {}),
    },
}

class StateRegister:
    def __init__(self):
        self._state = Phase.FETCH

    def state(self) -> Phase:
        return self._state

    def clock(self, reset: bool = False, next_state: Optional[Phase] = None) -> None:
        if reset:
            self._state = Phase.FETCH
        elif next_state is not None:
            self._state = next_state

class ControlPath:
    def __init__(self):
        self.state_reg = StateRegister()
        self.vec_lane = 0

    def state(self) -> Phase:
        return self.state_reg.state()

    def next_phase(self, opcode: int, conditions: Optional[Dict[str, Any]] = None) -> Phase:
        current = self.state_reg.state()
        op = (opcode >> OPCODE_SHIFT) & OPCODE_MASK
        name = OPCODE_NAMES.get(op, UNKNOWN_OPCODE)

        if conditions is None:
            conditions = {}

        # IF → ID/EX (Ibex 2-stage: fetch one cycle, decode+execute next)
        if current == Phase.FETCH:
            return Phase.EXECUTE

        # ID/EX → IF (or Halt if HALT opcode decoded)
        if current == Phase.EXECUTE:
            if name == HALT_TOKEN:
                return Phase.HALT
            return Phase.FETCH

        if current == Phase.VecOp:
            if conditions.get("vec_done", False):
                return Phase.FETCH
            return Phase.VecOp

        if current == Phase.HALT:
            return Phase.HALT

        return Phase.FETCH

    def _resolve_entry(self, current: Phase, name: str) -> Optional[MicrocodeEntry]:
        # IF stage: always use the fetch microcode entry
        if current == Phase.FETCH:
            return MICROCODE_ROM.get((Phase.FETCH, FETCH_TOKEN))

        # ID/EX stage: look for an exact (phase, opcode) entry first (e.g. HALT),
        # then fall back to the instruction-format entry which encodes both
        # decode (operand selection) and execute (ALU/Mem/WB) in one block.
        exact = MICROCODE_ROM.get((current, name))
        if exact is not None:
            return exact

        fmt = InstructionFormat.from_opcode_name(name)
        if fmt is not None:
            return MICROCODE_ROM.get(fmt)

        return None

    def control_signals(self, ir: int) -> Dict[str, Any]:
        op = (ir >> OPCODE_SHIFT) & OPCODE_MASK
        name = OPCODE_NAMES.get(op, UNKNOWN_OPCODE)
        current = self.state_reg.state()

        signs = DEFAULT_SIGNALS.copy()
        entry = self._resolve_entry(current, name)

        if entry is None:
            # Add debugging information
            print(f"DEBUG: No entry for opcode '{name}' (op={op}) in phase '{current.name}' (ir={ir:08X})")
            raise ValueError(f"No microcode entry for opcode '{name}' in phase '{current.name}'")

        return entry(name, signs)
