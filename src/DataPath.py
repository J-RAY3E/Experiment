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
    DATA_MEM_SIZE,
    IMM11_MASK,
    IMM11_SIGN,
    IMM21_MASK,
    IMM26_MASK,
    IN_PORT,
    NUM_REGS,
    NUM_VREGS,
    OPCODE_MASK,
    OPCODE_NAMES,
    OPCODE_SHIFT,
    OUT_PORT,
    RD_SHIFT,
    REG_MASK,
    REG_NAMES,
    RS1_SHIFT,
    RS2_SHIFT,
    SIGN_BIT,
    VLANES,
    WORD_MASK,
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

    def _fetch(self, sigs, inst_word, ir, rd):
        if sigs.get("ir_we") and inst_word is not None:
            ir = inst_word
            self.ir = ir
            rd = (ir >> RD_SHIFT) & REG_MASK
        return ir, rd

    def _read_latches(self, sigs, ir, v_en):
        a_val = 0
        b_val = 0
        vec_a, vec_b = None, None

        if sigs.get("a_sel") == "rs1":
            rs1 = (ir >> RS1_SHIFT) & REG_MASK
            if v_en:
                vec_a = self.vregs.read(rs1)
                a_val = vec_a[0]
            else:
                a_val = self.regs.read(rs1)
            self.a = a_val

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
        return a_val, b_val, vec_a, vec_b

    def _alu_phase(self, sigs, v_en, vec_a, vec_b, a_val, b_val, rd):
        alu_op = sigs.get("alu_op")
        self._vld_tmp = None
        if sigs.get("alu_exec") and alu_op:
            if v_en:
                if vec_a is None:
                    vec_a = [self.a] * VLANES
                if vec_b is None:
                    b_sel = sigs.get("b_sel")
                    scalar_b = self.b if b_sel == "rs2" else b_val
                    vec_b = [scalar_b] * VLANES

                result = [0] * VLANES
                for i in range(VLANES):
                    result[i] = self.alu.execute(alu_op, vec_a[i], vec_b[i])

                self.alu_out = result[0]
                if sigs.get("reg_we"):
                    self.vregs.write(rd, result)
            else:
                b_sel = sigs.get("b_sel")
                a_op = self.a
                b_op = self.b if b_sel == "rs2" else b_val
                self.alu_out = self.alu.execute(alu_op, a_op, b_op)

    def _memory_phase(self, sigs, rd, ir):
        addr = self.alu_out
        if sigs.get("mem_rd"):
            vec_n = sigs.get("mem_vec", 0)
            if vec_n == VLANES:
                self._vld_tmp = [self.mem.load_word((addr + i) & WORD_MASK) for i in range(VLANES)]
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

    def _write_back_phase(self, sigs, rd, ir, v_en):
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

    def _pc_phase(self, sigs, ir, rd):
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

    def tick_di_ex(self, sigs, inst_word=None):
        """ID/EX stage (Ibex 2-stage model): Decode + Execute in one clock cycle.

        This mirrors the Ibex processor's ID/EX stage, where instruction
        decoding and execution are fully combined:

          1. Decode  — extract rs1 / rs2 / imm from IR into operand latches A, B
          2. Execute — ALU operation (combinational)
          3. Memory  — optional load/store access
          4. Write-Back — result written to register file
          5. PC update — branch / jump target resolved

        The IR is already loaded by the preceding IF tick; `ir_we` is False here.
        """
        ir, rd = self._fetch(sigs, inst_word, self.ir, (self.ir >> RD_SHIFT) & REG_MASK)
        v_en = sigs.get("v_en", False)
        # --- Decode: read operands from register file ---
        a_val, b_val, vec_a, vec_b = self._read_latches(sigs, ir, v_en)
        # --- Execute: ALU ---
        self._alu_phase(sigs, v_en, vec_a, vec_b, a_val, b_val, rd)
        # --- Execute: Memory access ---
        self._memory_phase(sigs, rd, ir)
        # --- Write-Back: commit result to register file ---
        self._write_back_phase(sigs, rd, ir, v_en)
        # --- PC update: resolve branch/jump ---
        self._pc_phase(sigs, ir, rd)
        return sigs.get("halt", False)

    def tick(self, sigs, inst_word=None):
        """Clock the datapath for one cycle.

        Dispatches to the appropriate stage sub-routine based on the active
        control signals.  Following the Ibex 2-stage model:

          IF    (ir_we=True)  — load IR from instruction memory, advance PC.
          DI_EX (ir_we=False) — decode operands, execute ALU, access memory,
                                 write back, and update PC for branches/jumps.

        Both stages are fully contained in a single `dp.tick()` call driven by
        the ControlPath's microcode signals.
        """
        if sigs.get("ir_we"):
            # IF stage: latch the instruction word and increment PC
            ir, rd = self._fetch(sigs, inst_word, self.ir, (self.ir >> RD_SHIFT) & REG_MASK)
            self._pc_phase(sigs, ir, rd)
            return sigs.get("halt", False)
        # DI_EX stage: decode + execute
        return self.tick_di_ex(sigs, inst_word)

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
