"""
ControlPath: Horizontal microcoded control unit for RISC-IV.

The µROM is a static list of MicroInstruction (MI) records — one per address.
The Microsequencer holds a µPC (micro-program counter) register and steps
through the ROM one entry per clock tick.

µROM layout:
  addr  name       description
  ----  ---------  -------------------------------------------
   0    FETCH      Load IR, increment PC, then dispatch
   1    R_EX       R-type ALU execute + register write
   2    I_EX       I-type ALU execute + register write
   3    L_EX1      Load: compute address, read memory
   4    L_EX2      Load: write MDR → register
   5    S_EX       Store: compute address, write memory
   6    B_EX       Branch: compare registers, conditionally set PC
   7    J_EX       Jump: set PC from 26-bit field
   8    JL_EX      Jump-and-link: save PC, jump to 21-bit target
   9    JR_EX      Jump-register: set PC from register
  10    U_EX       LUI: write 21-bit immediate << 11 to register
  11    NOP_EX     No-op: return to FETCH immediately
  12    HALT_EX    Halt: stop execution
  13    V_EX       Vector ALU (4 lanes simultaneously)
  14    VLD_EX1    Vector load: compute address, read 4 words
  15    VLD_EX2    Vector load: write words to vector register
  16    VST_EX     Vector store: compute address, write 4 words
"""

from dataclasses import dataclass, replace

from src.ISA import OPCODE_MASK, OPCODE_NAMES, OPCODE_SHIFT

# ── Mux select constants ─────────────────────────────────────────────────────
# a_sel
A_NONE: int = 0
A_RS1:  int = 1

# b_sel
B_NONE: int = 0
B_RS2:  int = 1
B_IMM:  int = 2
B_ZERO: int = 3

# pc_src
PC_NONE:   int = 0
PC_INC:    int = 1  # (handled by pc_inc flag, kept for completeness)
PC_BRANCH: int = 2
PC_U26:    int = 3
PC_U21:    int = 4
PC_REG:    int = 5

# reg_src
REG_NONE:       int = 0
REG_ALU:        int = 1
REG_MEM:        int = 2
REG_PC:         int = 3
REG_IMM_SHL11:  int = 4

# next_upc sentinels
NEXT_FETCH:    int = 0   # return to FETCH (addr 0)
NEXT_DISPATCH: int = -1  # microsequencer dispatches on opcode format


# ── MicroInstruction word ────────────────────────────────────────────────────
@dataclass
class MI:
    """
    One horizontal micro-instruction stored in the µROM.

    Each field corresponds to one control signal (or mux select) in the
    hardware datapath.  All fields have hardware-meaningful defaults.
    """
    # ── Fetch / PC ────────────────────────────────────────────────────────
    ir_we:     bool = False    # load IR from instr_mem[PC]
    pc_inc:    bool = False    # PC ← PC + 1
    pc_src:    int  = PC_NONE  # mux: which value drives the PC next
    # ── ALU ──────────────────────────────────────────────────────────────
    a_sel:     int  = A_NONE   # mux: ALU operand A source
    b_sel:     int  = B_NONE   # mux: ALU operand B source
    alu_op:    str  = ""       # ALU operation (empty = determined by opcode decoder)
    alu_exec:  bool = False    # enable ALU computation this tick
    # ── Memory ────────────────────────────────────────────────────────────
    mar_we:    bool = False    # load MAR from ALU_OUT
    mem_rd:    bool = False    # memory read enable
    mem_wr:    bool = False    # memory write enable
    mem_byte:  bool = False    # byte (vs word) access mode
    mem_vec:   bool = False    # vector (4-word) access mode
    check_out: bool = False    # signal: address may be OUT_PORT
    # ── Register file ─────────────────────────────────────────────────────
    reg_we:    bool = False    # register file write enable
    reg_src:   int  = REG_NONE # mux: register write-data source
    # ── Vector extension ──────────────────────────────────────────────────
    v_en:      bool = False    # enable vector register file access
    # ── Control ───────────────────────────────────────────────────────────
    halt:      bool = False    # halt the machine
    # ── Microsequencer ────────────────────────────────────────────────────
    next_upc:  int  = NEXT_FETCH   # next µPC: NEXT_FETCH, NEXT_DISPATCH, or literal addr


# ── Instruction format classification ────────────────────────────────────────
OPCODE_FORMATS: dict[str, set[str]] = {
    "R":    {"ADD", "SUB", "MUL", "DIV", "REM", "MULH",
             "AND", "OR", "XOR", "NOT", "SLL", "SRL", "SRA", "SLT"},
    "I":    {"ADDI", "ANDI", "ORI", "XORI", "SLLI", "SRLI", "SRAI", "SLTI"},
    "L":    {"LW", "LB"},
    "S":    {"SW", "SB"},
    "B":    {"BEQ", "BNE", "BLT", "BLE", "BGT", "BGE", "BGTU", "BLEU"},
    "J":    {"J"},
    "JL":   {"JAL"},
    "JR":   {"JR"},
    "U":    {"LUI"},
    "NOP":  {"NOP"},
    "HALT": {"HALT"},
    "V":    {"VADD", "VSUB", "VMUL", "VDIV", "VCMP"},
    "VLD":  {"VLD"},
    "VST":  {"VST"},
}

# Opcode name → instruction format
_NAME_TO_FMT: dict[str, str] = {
    name: fmt
    for fmt, names in OPCODE_FORMATS.items()
    for name in names
}

# Opcode name → ALU operation code (for R/I/L/S types)
_ALU_OPS: dict[str, str] = {
    # R-type: operation matches mnemonic
    "ADD": "ADD", "SUB": "SUB", "MUL": "MUL", "DIV": "DIV",
    "REM": "REM", "MULH": "MULH",
    "AND": "AND", "OR": "OR",  "XOR": "XOR", "NOT": "NOT",
    "SLL": "SLL", "SRL": "SRL", "SRA": "SRA", "SLT": "SLT",
    # I-type: immediate variants map to base ALU ops
    "ADDI": "ADD", "ANDI": "AND", "ORI": "OR",  "XORI": "XOR",
    "SLLI": "SLL", "SRLI": "SRL", "SRAI": "SRA", "SLTI": "SLT",
    # L/S types: address = base + offset (always ADD)
    "LW": "ADD", "LB": "ADD", "SW": "ADD", "SB": "ADD",
    # Vector ALU: operation passed separately via v_en path
    "VADD": "ADD", "VSUB": "SUB", "VMUL": "MUL",
    "VDIV": "DIV", "VCMP": "SUB",
    "VLD":  "ADD", "VST":  "ADD",
}


# ── µROM ─────────────────────────────────────────────────────────────────────
# Static table of control words indexed by µPC address.
# Fields with alu_op="" are patched at runtime by the opcode decoder (combinational
# logic in hardware that wires opcode bits into the ALU control lines).
_UROM: list[MI] = [
    # 0  FETCH   — load IR from instr_mem[PC], increment PC, then dispatch
    MI(ir_we=True, pc_inc=True, next_upc=NEXT_DISPATCH),

    # 1  R_EX    — R-type: ALU(rs1, rs2) → rd
    MI(a_sel=A_RS1, b_sel=B_RS2, alu_exec=True,
       reg_we=True, reg_src=REG_ALU, next_upc=NEXT_FETCH),

    # 2  I_EX    — I-type: ALU(rs1, imm) → rd
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True,
       reg_we=True, reg_src=REG_ALU, next_upc=NEXT_FETCH),

    # 3  L_EX1   — Load step 1: addr = rs1 + imm; MAR = ALU_OUT
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, next_upc=4),

    # 4  L_EX2   — Load step 2: MDR = MEM[MAR]
    MI(mem_rd=True, next_upc=17),

    # 5  S_EX1   — Store step 1: addr = rs1 + imm; MAR = ALU_OUT
    MI(a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, next_upc=18),

    # 6  B_EX    — Branch: compare rs1, rs2; conditionally update PC
    MI(a_sel=A_RS1, b_sel=B_RS2, pc_src=PC_BRANCH, next_upc=NEXT_FETCH),

    # 7  J_EX    — Jump: PC = imm26 (absolute)
    MI(pc_src=PC_U26, next_upc=NEXT_FETCH),

    # 8  JL_EX   — Jump-and-link: rd = PC; PC = imm21
    MI(reg_we=True, reg_src=REG_PC, pc_src=PC_U21, next_upc=NEXT_FETCH),

    # 9  JR_EX   — Jump-register: PC = rd
    MI(pc_src=PC_REG, next_upc=NEXT_FETCH),

    # 10 U_EX    — LUI: rd = zero_ext(imm21) << 11
    MI(reg_we=True, reg_src=REG_IMM_SHL11, next_upc=NEXT_FETCH),

    # 11 NOP_EX  — No-op: nothing, return to FETCH
    MI(next_upc=NEXT_FETCH),

    # 12 HALT_EX — Halt: stop execution (no next_upc advance)
    MI(halt=True),

    # 13 V_EX    — Vector ALU: Vd[i] = ALU(Vs1[i], Vs2[i]) for i in 0..3
    MI(v_en=True, a_sel=A_RS1, b_sel=B_RS2, alu_exec=True,
       reg_we=True, reg_src=REG_ALU, next_upc=NEXT_FETCH),

    # 14 VLD_EX1 — Vector load step 1: addr = rs1 + imm; MAR = ALU_OUT
    MI(v_en=True, a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, next_upc=15),

    # 15 VLD_EX2 — Vector load step 2: load 4 words from MEM[MAR] to MDR
    MI(v_en=True, mem_rd=True, mem_vec=True, next_upc=19),

    # 16 VST_EX1 — Vector store step 1: addr = rs1 + imm; MAR = ALU_OUT
    MI(v_en=True, a_sel=A_RS1, b_sel=B_IMM, alu_exec=True, mar_we=True, next_upc=20),

    # 17 L_EX3   — Load step 3: rd = MDR
    MI(reg_we=True, reg_src=REG_MEM, next_upc=NEXT_FETCH),

    # 18 S_EX2   — Store step 2: MEM[MAR] = rd
    MI(mem_wr=True, check_out=True, next_upc=NEXT_FETCH),

    # 19 VLD_EX3 — Vector load step 3: Vd = loaded words
    MI(v_en=True, reg_we=True, reg_src=REG_MEM, next_upc=NEXT_FETCH),

    # 20 VST_EX2 — Vector store step 2: store 4 words from Vd to MEM[MAR]
    MI(v_en=True, mem_wr=True, mem_vec=True, next_upc=NEXT_FETCH),
]

# Human-readable name for each µROM address (for journal output)
UROM_NAMES: list[str] = [
    "FETCH",
    "R_EX", "I_EX", "L_EX1", "L_EX2", "S_EX1",
    "B_EX", "J_EX", "JL_EX", "JR_EX", "U_EX",
    "NOP_EX", "HALT_EX",
    "V_EX", "VLD_EX1", "VLD_EX2", "VST_EX1",
    "L_EX3", "S_EX2", "VLD_EX3", "VST_EX2"
]

# Dispatch table: instruction format → µROM start address
DISPATCH: dict[str, int] = {
    "R":    1,
    "I":    2,
    "L":    3,
    "S":    5,
    "B":    6,
    "J":    7,
    "JL":   8,
    "JR":   9,
    "U":    10,
    "NOP":  11,
    "HALT": 12,
    "V":    13,
    "VLD":  14,
    "VST":  16,
}


# ── Microsequencer ────────────────────────────────────────────────────────────
class Microsequencer:
    """
    Holds the micro-program counter (µPC) and advances it each clock cycle.

    The µPC indexes into _UROM.  When next_upc == NEXT_DISPATCH the sequencer
    reads the current IR, looks up the instruction format, and jumps to the
    corresponding execute microprogram.
    """

    def __init__(self) -> None:
        self.upc: int = 0  # start at FETCH

    @property
    def phase_name(self) -> str:
        """Human-readable name of the current µROM address."""
        idx = self.upc
        return UROM_NAMES[idx] if 0 <= idx < len(UROM_NAMES) else f"U{idx}"

    def current_mi(self, ir: int) -> MI:
        """
        Return the MI at the current µPC, with opcode-specific patches applied.

        Patches are combinational overrides driven by opcode bits — they are
        not stored in the µROM itself, mirroring real hardware design where
        opcode bits are wired directly to certain control lines.
        """
        mi = _UROM[self.upc]
        patches: dict = {}

        if mi.alu_exec:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            # Patch 1: alu_op — driven by opcode decoder (combinational)
            if not mi.alu_op:
                patches["alu_op"] = _ALU_OPS.get(name, "ADD")
            # Patch 2: mem_byte — driven by opcode bit (LB/SB vs LW/SW)
            if mi.mem_rd or mi.mem_wr:
                patches["mem_byte"] = name in ("LB", "SB")
            # Patch 3: b_sel for NOT — NOT uses rs1 only (b = 0)
            if name == "NOT":
                patches["b_sel"] = B_ZERO

        return replace(mi, **patches) if patches else mi

    def advance(self, ir: int) -> None:
        """
        Advance µPC based on the next_upc field of the current MI.

        If next_upc == NEXT_DISPATCH, decode the IR opcode to find the
        instruction format and jump to the corresponding µROM address.
        """
        mi = _UROM[self.upc]
        if mi.halt:
            return  # stay in HALT_EX forever
        if mi.next_upc == NEXT_DISPATCH:
            name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
            fmt  = _NAME_TO_FMT.get(name, "NOP")
            self.upc = DISPATCH.get(fmt, DISPATCH["NOP"])
        else:
            self.upc = mi.next_upc


# ── ControlPath (top-level interface used by Machine) ─────────────────────────
class ControlPath:
    """Microcoded control unit.  Machine calls current_mi() then advance()."""

    def __init__(self) -> None:
        self.seq = Microsequencer()

    @property
    def halted(self) -> bool:
        return _UROM[self.seq.upc].halt

    @property
    def phase_name(self) -> str:
        return self.seq.phase_name

    @property
    def upc(self) -> int:
        return self.seq.upc

    def current_mi(self, ir: int) -> MI:
        """Return the patched MI for the current µPC and given IR."""
        return self.seq.current_mi(ir)

    def advance(self, ir: int) -> None:
        """Advance µPC (call after dp.tick so the new IR is visible)."""
        self.seq.advance(ir)
