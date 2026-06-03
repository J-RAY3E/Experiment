from src.ISA import (
    DATA_MEM_SIZE, IN_PORT, NUM_REGS, NUM_VREGS, OUT_PORT,
    RD_SHIFT, REG_MASK, REG_NAMES, RS1_SHIFT, RS2_SHIFT,
    SIGN_BIT, VLANES, WORD_MASK, decode,
)
from src.ControlPath import (
    MI,
    A_RS1, B_RS2, B_IMM, B_ZERO,
    PC_BRANCH, PC_U26, PC_U21, PC_REG,
    REG_ALU, REG_MEM, REG_PC, REG_IMM_SHL11,
)

BYTE_MASK   = 0xFF
BYTE_SIGN   = 0x80
SHIFT_MASK  = 0x1F
SIGN_EXT_NEG = ~0x7FFFFFFF


def _to_signed(v: int) -> int:
    return v if not (v & SIGN_BIT) else v | SIGN_EXT_NEG


# ── RegisterFile ─────────────────────────────────────────────────────────────
class RegisterFile:
    def __init__(self) -> None:
        self.regs = [0] * NUM_REGS

    def read(self, addr: int) -> int:
        return 0 if addr == 0 else self.regs[addr]

    def write(self, addr: int, value: int) -> None:
        if addr != 0:
            self.regs[addr] = value & WORD_MASK

    def dump(self) -> dict:
        return {REG_NAMES[i]: self.regs[i] for i in range(NUM_REGS)}


# ── VectorRegisterFile ────────────────────────────────────────────────────────
class VectorRegisterFile:
    def __init__(self) -> None:
        self.regs = [[0] * VLANES for _ in range(NUM_VREGS)]

    def read(self, addr: int) -> list[int]:
        return list(self.regs[addr & (NUM_VREGS - 1)])

    def write(self, addr: int, values: list[int]) -> None:
        self.regs[addr & (NUM_VREGS - 1)] = [v & WORD_MASK for v in values]


# ── ALU ───────────────────────────────────────────────────────────────────────
class ALU:
    _OPS = {
        "ADD":  lambda a, b: (a + b) & WORD_MASK,
        "SUB":  lambda a, b: (a - b) & WORD_MASK,
        "MUL":  lambda a, b: (a * b) & WORD_MASK,
        "MULH": lambda a, b: ((a * b) >> 32) & WORD_MASK,
        "DIV":  lambda a, b: (_to_signed(a) // _to_signed(b)) & WORD_MASK if b else 0,
        "REM":  lambda a, b: (_to_signed(a) % _to_signed(b)) & WORD_MASK if b else 0,
        "AND":  lambda a, b: a & b,
        "OR":   lambda a, b: a | b,
        "XOR":  lambda a, b: a ^ b,
        "NOT":  lambda a, b: (~a) & WORD_MASK,
        "SLL":  lambda a, b: (a << (b & SHIFT_MASK)) & WORD_MASK,
        "SRL":  lambda a, b: (a >> (b & SHIFT_MASK)) & WORD_MASK,
        "SRA":  lambda a, b: (_to_signed(a) >> (b & SHIFT_MASK)) & WORD_MASK,
        "SLT":  lambda a, b: 1 if _to_signed(a) < _to_signed(b) else 0,
    }

    def execute(self, op: str, a: int, b: int) -> int:
        fn = self._OPS.get(op)
        return fn(a & WORD_MASK, b & WORD_MASK) if fn else 0


# ── DataMemory ────────────────────────────────────────────────────────────────
class DataMemory:
    def __init__(self, size: int = DATA_MEM_SIZE) -> None:
        self.mem = [0] * size
        self._read_input = None
        self._write_output = None

    def _addr(self, addr: int) -> int:
        return addr & WORD_MASK

    def load_word(self, addr: int) -> int:
        addr = self._addr(addr)
        if addr == IN_PORT:
            return self._read_input() if self._read_input else 0
        return self.mem[addr] if 0 <= addr < len(self.mem) else 0

    def load_byte(self, addr: int) -> int:
        val = self.load_word(addr) & BYTE_MASK
        # sign-extend byte
        return (val | ~BYTE_MASK) & WORD_MASK if val & BYTE_SIGN else val

    def store_word(self, addr: int, value: int) -> None:
        addr = self._addr(addr)
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem):
            self.mem[addr] = value & WORD_MASK

    def store_byte(self, addr: int, value: int) -> None:
        addr = self._addr(addr)
        if addr == OUT_PORT:
            if self._write_output:
                self._write_output(value & BYTE_MASK)
        elif 0 <= addr < len(self.mem):
            self.mem[addr] = (self.mem[addr] & ~BYTE_MASK) | (value & BYTE_MASK)


# ── DataPath ──────────────────────────────────────────────────────────────────
class DataPath:
    """
    Datapath: register file, vector registers, ALU, and data memory.

    tick(mi, inst_word) advances the datapath by one micro-step according to
    the control signals in the MI word returned by the ControlPath.
    """

    def __init__(self, input_stream: str = "") -> None:
        self.regs  = RegisterFile()
        self.vregs = VectorRegisterFile()
        self.alu   = ALU()
        self.mem   = DataMemory()

        # Visible pipeline registers
        self.pc:      int = 0
        self.ir:      int = 0
        self.a:       int = 0
        self.b:       int = 0
        self.alu_out: int = 0
        self.mar:     int = 0
        self.mdr:     int = 0

        # Cached decode of current IR (updated on every FETCH)
        self._ctx: dict = {}
        # Temporary for vector loads
        self._vld_tmp: list[int] = []

        # Stream I/O
        self.input_buffer:  list[str] = list(input_stream)
        self.input_pos:     int       = 0
        self.output_buffer: list[int] = []

        self.mem._read_input   = self._read_next_char
        self.mem._write_output = self._write_char

    # ── I/O ──────────────────────────────────────────────────────────────
    def _read_next_char(self) -> int:
        if self.input_pos < len(self.input_buffer):
            ch = ord(self.input_buffer[self.input_pos])
            self.input_pos += 1
            return ch
        return 0

    def _write_char(self, val: int) -> None:
        self.output_buffer.append(val)

    # ── Branch helper ─────────────────────────────────────────────────────
    def _do_branch(self, ctx: dict) -> None:
        rs1, rs2 = ctx["rs1"], ctx["rs2"]
        a_u = self.regs.read(rs1)
        b_u = self.regs.read(rs2)
        a_s, b_s = _to_signed(a_u), _to_signed(b_u)
        taken = {
            "BEQ":  a_u == b_u, "BNE":  a_u != b_u,
            "BLT":  a_s <  b_s, "BLE":  a_s <= b_s,
            "BGT":  a_s >  b_s, "BGE":  a_s >= b_s,
            "BGTU": a_u >  b_u, "BLEU": a_u <= b_u,
        }.get(ctx["name"], False)
        if taken:
            self.pc = (self.pc + ctx["imm_s"]) & WORD_MASK

    # ── Main tick ─────────────────────────────────────────────────────────
    def tick(self, mi: MI, inst_word: int | None = None) -> bool:
        """
        Execute one micro-step.

        Returns True if the halt signal is set (machine should stop).
        """
        # ── FETCH step ───────────────────────────────────────────────────
        if mi.ir_we:
            if inst_word is not None:
                self.ir = inst_word
            # Decode IR and cache — only updated here (on FETCH)
            self._ctx = decode(self.ir)
            if mi.pc_inc:
                self.pc = (self.pc + 1) & WORD_MASK
            return False

        if mi.halt:
            return True

        # ── Execute steps ────────────────────────────────────────────────
        ctx   = self._ctx
        rd    = ctx["rd"]
        rs1   = ctx["rs1"]
        rs2   = ctx["rs2"]
        v_en  = mi.v_en

        # ALU operand A
        if mi.a_sel == A_RS1:
            self.a = self.vregs.read(rs1)[0] if v_en else self.regs.read(rs1)

        # ALU operand B
        if   mi.b_sel == B_RS2:
            self.b = self.vregs.read(rs2)[0] if v_en else self.regs.read(rs2)
        elif mi.b_sel == B_IMM:
            self.b = ctx["imm_s"]
        elif mi.b_sel == B_ZERO:
            self.b = 0

        # ALU execute
        if mi.alu_exec and mi.alu_op:
            if v_en:
                v_a = self.vregs.read(rs1)
                v_b = (self.vregs.read(rs2) if mi.b_sel == B_RS2
                       else [self.b] * VLANES)
                res = [self.alu.execute(mi.alu_op, v_a[i], v_b[i])
                       for i in range(VLANES)]
                self.alu_out = res[0]
                # Vector ALU write-back happens here (single step)
                if mi.reg_we and mi.reg_src == REG_ALU:
                    self.vregs.write(rd, res)
            else:
                self.alu_out = self.alu.execute(mi.alu_op, self.a, self.b)

        # Memory read
        if mi.mem_rd:
            if mi.mem_vec:
                self._vld_tmp = [
                    self.mem.load_word((self.alu_out + i) & WORD_MASK)
                    for i in range(VLANES)
                ]
                self.mdr = self._vld_tmp[0]
            elif mi.mem_byte:
                self.mdr = self.mem.load_byte(self.alu_out)
            else:
                self.mdr = self.mem.load_word(self.alu_out)

        # Memory write
        if mi.mem_wr:
            if mi.mem_vec:
                vals = self.vregs.read(rd)
                for i in range(VLANES):
                    self.mem.store_word((self.alu_out + i) & WORD_MASK, vals[i])
            else:
                data = self.regs.read(rd)
                if mi.mem_byte:
                    self.mem.store_byte(self.alu_out, data)
                else:
                    self.mem.store_word(self.alu_out, data)

        # Register write-back (scalar; vector ALU write done above)
        if mi.reg_we and not (v_en and mi.reg_src == REG_ALU):
            if mi.reg_src == REG_ALU:
                self.regs.write(rd, self.alu_out)
            elif mi.reg_src == REG_MEM:
                if mi.mem_vec:
                    self.vregs.write(rd, self._vld_tmp)
                else:
                    self.regs.write(rd, self.mdr)
            elif mi.reg_src == REG_PC:
                self.regs.write(rd, self.pc)
            elif mi.reg_src == REG_IMM_SHL11:
                self.regs.write(rd, ctx["imm_u21"] << 11)

        # PC update (branch / jump)
        if   mi.pc_src == PC_BRANCH:
            self._do_branch(ctx)
        elif mi.pc_src == PC_U26:
            self.pc = ctx["imm_u26"]
        elif mi.pc_src == PC_U21:
            self.pc = ctx["imm_u21"]
        elif mi.pc_src == PC_REG:
            self.pc = self.regs.read(rd)

        return False