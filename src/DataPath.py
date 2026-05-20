"""DataPath: register files, ALU, data memory, and MMIO for the RISC-IV processor.

Implements the hardware-level datapath that the ControlUnit drives via
control signals on each tick.  Key components:

- RegisterFile       — 32 × 32-bit scalar registers (R0 hardwired to 0)
- VectorRegisterFile — 8 × 128-bit vector registers (4 × int32 lanes)
- ALU                — combinational arithmetic / logic unit
- DataMemory         — word-addressed data RAM with MMIO intercepts
- DataPath           — top-level wiring of the above + latch registers
"""

from src.ISA import (
    OPCODE_NAMES, REG_NAMES,
    IN_PORT, OUT_PORT,
    NUM_REGS, NUM_VREGS, VLANES, DATA_MEM_SIZE,
    WORD_MASK, SIGN_BIT, REG_MASK,
    IMM11_MASK, IMM11_SIGN, IMM21_MASK, IMM26_MASK,
    OPCODE_SHIFT, OPCODE_MASK, RD_SHIFT, RS1_SHIFT, RS2_SHIFT,
)

BYTE_MASK = 0xFF
BYTE_SIGN = 0x80
SHIFT_MASK = 0x1F
SIGN_EXT_NEG = ~0x7FFFFFFF


class RegisterFile:

    def __init__(self):
        self.regs = [0] * NUM_REGS

    def read(self, addr):
        return 0 if addr == 0 else self.regs[addr]

    def write(self, addr, value):
        if addr != 0:
            self.regs[addr] = value & WORD_MASK

    def dump(self):
        return {REG_NAMES[i]: self.regs[i] for i in range(NUM_REGS)}


class VectorRegisterFile:

    def __init__(self):
        self.regs = [[0] * VLANES for _ in range(NUM_VREGS)]

    def read(self, addr):
        return list(self.regs[addr & (NUM_VREGS - 1)])

    def write(self, addr, values):
        self.regs[addr & (NUM_VREGS - 1)] = [v & WORD_MASK for v in values]


def _to_signed(v):

    return v if not (v & SIGN_BIT) else v | SIGN_EXT_NEG


class ALU:
    """Combinational arithmetic / logic unit — one result per call."""
    def execute(self, op, a, b):
        a, b = a & WORD_MASK, b & WORD_MASK
        if op == "ADD":
            return (a + b) & WORD_MASK
        if op == "SUB":
            return (a - b) & WORD_MASK
        if op == "MUL":
            return (a * b) & WORD_MASK
        if op == "MULH":
            return ((a * b) >> WORD_MASK.bit_length()) & WORD_MASK
        if op == "DIV":
            return (_to_signed(a) // _to_signed(b)) & WORD_MASK if b else 0
        if op == "REM":
            return (_to_signed(a) % _to_signed(b)) & WORD_MASK if b else 0
        if op == "AND":
            return a & b
        if op == "OR":
            return a | b
        if op == "XOR":
            return a ^ b
        if op == "NOT":
            return (~a) & WORD_MASK
        if op == "SLL":
            return (a << (b & SHIFT_MASK)) & WORD_MASK
        if op == "SRL":
            return (a >> (b & SHIFT_MASK)) & WORD_MASK
        if op == "SRA":
            return (_to_signed(a) >> (b & SHIFT_MASK)) & WORD_MASK
        if op == "SLT":
            return 1 if _to_signed(a) < _to_signed(b) else 0
        return 0


class DataMemory:


    def __init__(self, size=DATA_MEM_SIZE):
        self.mem = [0] * size
        self._read_input = None
        self._write_output = None

    def load_word(self, addr):
        addr = addr & WORD_MASK
        if addr == IN_PORT:
            if self._read_input is not None:
                return self._read_input()
            return 0
        if addr == OUT_PORT:
            return 0
        if 0 <= addr < len(self.mem):
            return self.mem[addr]
        return 0

    def load_byte(self, addr):
        val = self.load_word(addr) & BYTE_MASK
        if val & BYTE_SIGN:
            val = val | ~(BYTE_MASK)
        return val & WORD_MASK

    def store_word(self, addr, value):
        addr = addr & WORD_MASK
        if addr == OUT_PORT:
            if self._write_output is not None:
                self._write_output(value & BYTE_MASK)
            return
        if addr == IN_PORT:
            return
        if 0 <= addr < len(self.mem):
            self.mem[addr] = value & WORD_MASK

    def store_byte(self, addr, value):
        addr = addr & WORD_MASK
        val = value & BYTE_MASK
        if addr == OUT_PORT:
            if self._write_output is not None:
                self._write_output(val)
            return
        if 0 <= addr < len(self.mem):
            self.mem[addr] = (self.mem[addr] & ~BYTE_MASK) | val


class DataPath:


    def __init__(self, input_stream=""):
        self.regs = RegisterFile()
        self.vregs = VectorRegisterFile()
        self.alu = ALU()
        self.mem = DataMemory()

        # PC and pipeline latches
        self.pc = 0
        self.ir = 0
        self.alu_out = 0
        self.mdr = 0
        self.a = 0
        self.b = 0

        self.input_buffer = list(input_stream)
        self.input_pos = 0
        self.output_buffer = []

        self.mem._read_input = self._read_next_char
        self.mem._write_output = self._write_char


    def _read_next_char(self):
        if self.input_pos < len(self.input_buffer):
            ch = ord(self.input_buffer[self.input_pos])
            self.input_pos += 1
            return ch
        return 0  # EOF → 0

    def _write_char(self, val):
        self.output_buffer.append(val)

    def flush_output(self):
        out = "".join(chr(c) for c in self.output_buffer if 0 <= c < 256)
        self.output_buffer = []
        return out


    def _sext_imm11(self, ir):
        imm = ir & IMM11_MASK
        return imm | ~IMM11_MASK if imm & IMM11_SIGN else imm

    def tick(self, sigs, inst_word=None):

        ir = self.ir
        v_en = sigs.get("v_en", False)
        alu_op = sigs.get("alu_op")
        rd = (ir >> RD_SHIFT) & REG_MASK
        halted = False
        vec_a = None
        vec_b = None

        # === Phase 1: Fetch (IR latch) ===
        if sigs.get("ir_we") and inst_word is not None:
            ir = inst_word
            self.ir = ir
            rd = (ir >> RD_SHIFT) & REG_MASK

        # === Phase 2: Read A latch ===
        a_val = 0
        if sigs.get("a_sel") == "rs1":
            rs1 = (ir >> RS1_SHIFT) & REG_MASK
            if v_en:
                vec_a = self.vregs.read(rs1)
                a_val = vec_a[0]
            else:
                a_val = self.regs.read(rs1)
            self.a = a_val

        # === Phase 3: Read B latch / immediate ===
        b_val = 0
        b_sel = sigs.get("b_sel")
        if b_sel == "rs2":
            rs2 = (ir >> RS2_SHIFT) & REG_MASK
            if v_en:
                vec_b = self.vregs.read(rs2)
                b_val = vec_b[0]
            else:
                b_val = self.regs.read(rs2)
            self.b = b_val
        elif b_sel == "imm":
            b_val = self._sext_imm11(ir)
        elif b_sel == "zero":
            b_val = 0

        # === Phase 4: ALU ===
        self._vld_tmp = None
        if sigs.get("alu_exec") and alu_op:
            if v_en:
                if vec_a is None:
                    vec_a = [self.a] * VLANES
                if vec_b is None:
                    scalar_b = self.b if b_sel == "rs2" else b_val
                    vec_b = [scalar_b] * VLANES
                
                result = [0] * VLANES
                for i in range(VLANES):
                    result[i] = self.alu.execute(alu_op, vec_a[i], vec_b[i])
                
                self.alu_out = result[0]
                if sigs.get("reg_we"):
                    self.vregs.write(rd, result)
            else:
                a_op = self.a
                b_op = self.b if b_sel == "rs2" else b_val
                self.alu_out = self.alu.execute(alu_op, a_op, b_op)

        # === Phase 5: Memory ===
        addr = self.alu_out
        if sigs.get("mem_rd"):
            vec_n = sigs.get("mem_vec", 0)
            if vec_n == VLANES:
                self._vld_tmp = [
                    self.mem.load_word((addr + i) & WORD_MASK) for i in range(VLANES)
                ]
                self.mdr = self._vld_tmp[0]
            elif sigs.get("mem_byte"):
                self.mdr = self.mem.load_byte(addr)
            else:
                self.mdr = self.mem.load_word(addr)

        if sigs.get("mem_wr"):
            vec_n = sigs.get("mem_vec", 0)
            if vec_n == VLANES:
                vals = self.vregs.read(rd)
                for i in range(VLANES):
                    self.mem.store_word((addr + i) & WORD_MASK, vals[i])
            else:
                data = self.regs.read(rd)
                if sigs.get("mem_byte"):
                    self.mem.store_byte(addr, data)
                else:
                    self.mem.store_word(addr, data)

        # === Phase 6: Register file write-back ===
        if sigs.get("reg_we"):
            reg_src = sigs.get("reg_src")
            if reg_src == "alu":
                if v_en:
                    self.vregs.write(rd, [self.alu_out] * VLANES)
                else:
                    self.regs.write(rd, self.alu_out)
            elif reg_src == "mem":
                vec_n = sigs.get("mem_vec", 0)
                if vec_n == VLANES and self._vld_tmp is not None:
                    self.vregs.write(rd, self._vld_tmp)
                else:
                    self.regs.write(rd, self.mdr)
            elif reg_src == "pc":
                self.regs.write(rd, self.pc)
            elif reg_src == "imm_shl11":
                self.regs.write(rd, (ir & IMM21_MASK) << IMM11_MASK.bit_length())

        # === Phase 7: PC update ===
        pc_src = sigs.get("pc_src")
        if sigs.get("pc_we") and pc_src:
            if pc_src == "inc":
                self.pc = (self.pc + 1) & WORD_MASK
            elif pc_src == "ir_u26":
                self.pc = ir & IMM26_MASK
            elif pc_src == "ir_u21":
                self.pc = ir & IMM21_MASK
            elif pc_src == "reg":
                self.pc = self.regs.read(rd)
            elif pc_src == "branch":
                self._do_branch(ir)

        # === Phase 8: Halt check ===
        if sigs.get("halt"):
            halted = True

        return halted

    def _do_branch(self, ir):
        rs1 = (ir >> RS1_SHIFT) & REG_MASK
        rs2 = (ir >> RS2_SHIFT) & REG_MASK
        off = self._sext_imm11(ir)
        a_val = self.regs.read(rs1)
        b_val = self.regs.read(rs2)
        a_s = _to_signed(a_val)
        b_s = _to_signed(b_val)
        name = OPCODE_NAMES.get((ir >> OPCODE_SHIFT) & OPCODE_MASK, "")
        taken = {
            "BEQ": a_val == b_val, "BNE": a_val != b_val,
            "BLT": a_s < b_s, "BLE": a_s <= b_s,
            "BGT": a_s > b_s, "BGE": a_s >= b_s,
            "BGTU": a_val > b_val, "BLEU": a_val <= b_val,
        }.get(name, False)
        if taken:
            self.pc = (self.pc + off) & WORD_MASK

    def dump_state(self):
        return {
            "pc": self.pc, "ir": self.ir,
            "a": self.a, "b": self.b,
            "alu_out": self.alu_out, "mdr": self.mdr,
        }
