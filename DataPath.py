from ISA import REG, REG_NAMES, OPCODE_NAMES, decode, sign_extend

IN_PORT = 0xFFF0
OUT_PORT = 0xFFF4
IN_PORT_LEGACY = 0xFFFFFFF0
OUT_PORT_LEGACY = 0xFFFFFFF4

class RegisterFile:
    def __init__(self):
        self.regs = [0] * 32

    def read(self, addr):
        return 0 if addr == 0 else self.regs[addr]

    def write(self, addr, value):
        if addr != 0:
            self.regs[addr] = value & 0xFFFFFFFF

    def dump(self):
        return {REG_NAMES[i]: self.regs[i] for i in range(32)}

class VectorRegisterFile:
    def __init__(self):
        self.regs = [[0]*4 for _ in range(8)]

    def read(self, addr):
        return list(self.regs[addr & 7])

    def write(self, addr, values):
        self.regs[addr & 7] = [v & 0xFFFFFFFF for v in values]

class ALU:
    def execute(self, op, a, b):
        a, b = a & 0xFFFFFFFF, b & 0xFFFFFFFF
        if op == "ADD": return (a + b) & 0xFFFFFFFF
        if op == "SUB": return (a - b) & 0xFFFFFFFF
        if op == "MUL": return (a * b) & 0xFFFFFFFF
        if op == "MULH": return ((a * b) >> 32) & 0xFFFFFFFF
        if op == "DIV": return (a // b) & 0xFFFFFFFF if b != 0 else 0
        if op == "REM": return (a % b) & 0xFFFFFFFF if b != 0 else 0
        if op == "AND": return a & b
        if op == "OR":  return a | b
        if op == "XOR": return a ^ b
        if op == "NOT": return (~a) & 0xFFFFFFFF
        if op == "SLL": return (a << (b & 0x1F)) & 0xFFFFFFFF
        if op == "SRL": return (a >> (b & 0x1F)) & 0xFFFFFFFF
        if op == "SRA":
            val = a
            if val & 0x80000000:
                val = val | ~0x7FFFFFFF
            return (val >> (b & 0x1F)) & 0xFFFFFFFF
        if op == "SLT":
            sa = a if not (a & 0x80000000) else a | ~0x7FFFFFFF
            sb = b if not (b & 0x80000000) else b | ~0x7FFFFFFF
            return 1 if sa < sb else 0
        return 0

class DataMemory:
    def __init__(self, size=8192):
        self.mem = [0] * size
        self.out_val = None
        self.in_val = 0

    def load_word(self, addr):
        addr = addr & 0xFFFFFFFF
        if addr in (IN_PORT, IN_PORT_LEGACY):
            return self.in_val if hasattr(self, 'in_val') else 0
        if addr in (OUT_PORT, OUT_PORT_LEGACY):
            return 0
        if 0 <= addr < len(self.mem):
            return self.mem[addr]
        return 0

    def load_byte(self, addr):
        val = self.load_word(addr) & 0xFF
        if val & 0x80:
            val = val | ~0x7F
        return val & 0xFFFFFFFF

    def store_word(self, addr, value):
        addr = addr & 0xFFFFFFFF
        if addr in (OUT_PORT, OUT_PORT_LEGACY):
            self.out_val = value & 0xFF
            return
        if 0 <= addr < len(self.mem):
            self.mem[addr] = value & 0xFFFFFFFF

    def store_byte(self, addr, value):
        addr = addr & 0xFFFFFFFF
        val = value & 0xFF
        if addr in (OUT_PORT, OUT_PORT_LEGACY):
            self.out_val = val
            return
        if 0 <= addr < len(self.mem):
            self.mem[addr] = (self.mem[addr] & ~0xFF) | val

class DataPath:
    def __init__(self, input_stream=""):
        self.regs = RegisterFile()
        self.vregs = VectorRegisterFile()
        self.alu = ALU()
        self.mem = DataMemory()
        self.pc = 0
        self.ir = 0
        self.alu_out = 0
        self.mdr = 0
        self.a = 0
        self.b = 0
        self.input_stream = list(reversed(list(input_stream)))
        self.mem.in_val = ord(self.input_stream.pop()) if self.input_stream else 0
        self.output_buffer = []

    def read_input(self):
        if self.input_stream:
            self.mem.in_val = ord(self.input_stream.pop())
        else:
            self.mem.in_val = 0
        return self.mem.in_val

    def flush_output(self):
        out = "".join(chr(c) for c in self.output_buffer if 0 <= c < 256)
        self.output_buffer = []
        return out

    def sig_sext(self, ir):
        imm11 = ir & 0x7FF
        if imm11 & 0x400:
            return imm11 | ~0x7FF
        return imm11

    def sig_read_a(self, ir, v_en=False):
        rs1 = (ir >> 16) & 0x1F
        if v_en:
            return self.vregs.read(rs1)
        return self.regs.read(rs1)

    def sig_read_b(self, ir, b_sel, v_en=False):
        if b_sel == "rs2":
            rs2 = (ir >> 11) & 0x1F
            if v_en:
                return self.vregs.read(rs2)
            return self.regs.read(rs2)
        elif b_sel == "imm":
            return self.sig_sext(ir)
        elif b_sel == "zero":
            return 0
        return 0

    def tick(self, sigs, inst_word=None):
        ir = self.ir
        v_en = sigs.get("v_en", False)
        alu_op = sigs.get("alu_op")
        rd = (ir >> 21) & 0x1F
        halted = False
        vec_a = None; vec_b = None

        if sigs.get("ir_we") and inst_word is not None:
            ir = inst_word
            self.ir = ir
            rd = (ir >> 21) & 0x1F

        a_val = 0
        if sigs.get("a_sel") == "rs1":
            rs1 = (ir >> 16) & 0x1F
            if v_en and alu_op == "V_OP":
                vec_a = self.vregs.read(rs1)
                a_val = vec_a[0]
            else:
                a_val = self.regs.read(rs1)
            self.a = a_val

        b_val = 0
        b_sel = sigs.get("b_sel")
        if b_sel == "rs2":
            rs2 = (ir >> 11) & 0x1F
            if v_en and alu_op == "V_OP":
                vec_b = self.vregs.read(rs2)
                b_val = vec_b[0]
            else:
                b_val = self.regs.read(rs2)
            self.b = b_val
        elif b_sel == "imm":
            imm11 = ir & 0x7FF
            b_val = imm11 | ~0x7FF if imm11 & 0x400 else imm11

        self._vld_tmp = None
        if sigs.get("alu_exec") and alu_op:
            if alu_op == "V_OP":
                if vec_a is None: vec_a = [a_val]*4
                if vec_b is None: vec_b = [b_val]*4
                iname = OPCODE_NAMES.get((ir >> 26) & 0x3F, '???')
                result = [0]*4
                for i in range(4):
                    if iname == "VADD": result[i] = (vec_a[i] + vec_b[i]) & 0xFFFFFFFF
                    elif iname == "VSUB": result[i] = (vec_a[i] - vec_b[i]) & 0xFFFFFFFF
                    elif iname == "VMUL": result[i] = (vec_a[i] * vec_b[i]) & 0xFFFFFFFF
                    elif iname == "VDIV": result[i] = (vec_a[i] // vec_b[i]) & 0xFFFFFFFF if vec_b[i] != 0 else 0
                    elif iname == "VCMP":
                        sa = vec_a[i] if not (vec_a[i] & 0x80000000) else vec_a[i] | ~0x7FFFFFFF
                        sb = vec_b[i] if not (vec_b[i] & 0x80000000) else vec_b[i] | ~0x7FFFFFFF
                        result[i] = 1 if sa < sb else 0
                self.alu_out = result[0]
                if sigs.get("reg_we"):
                    self.vregs.write(rd, result)
            else:
                a_op = self.a if not isinstance(a_val, list) else a_val[0]
                b_op = self.b if b_sel == "rs2" else (b_val if not isinstance(b_val, list) else b_val[0])
                self.alu_out = self.alu.execute(alu_op, a_op, b_op)

        addr = self.alu_out
        if sigs.get("mem_rd"):
            vec_n = sigs.get("mem_vec", 0)
            if vec_n == 4:
                self._vld_tmp = [self.mem.load_word((addr + i) & 0xFFFFFFFF) for i in range(4)]
                self.mdr = self._vld_tmp[0]
            elif sigs.get("mem_byte"):
                self.mdr = self.mem.load_byte(addr)
            else:
                self.mdr = self.mem.load_word(addr)

        if sigs.get("mem_wr"):
            vec_n = sigs.get("mem_vec", 0)
            if vec_n == 4:
                vals = self.vregs.read(rd)
                for i in range(4):
                    self.mem.store_word((addr + i) & 0xFFFFFFFF, vals[i])
            else:
                data = self.regs.read(rd)
                if sigs.get("mem_byte"):
                    self.mem.store_byte(addr, data)
                else:
                    self.mem.store_word(addr, data)
                if sigs.get("check_out") and addr in (OUT_PORT, OUT_PORT_LEGACY):
                    self.output_buffer.append(data & 0xFF)

        if sigs.get("reg_we"):
            reg_src = sigs.get("reg_src")
            if reg_src == "alu":
                if v_en and alu_op == "V_OP":
                    pass
                elif v_en:
                    self.vregs.write(rd, [self.alu_out]*4)
                else:
                    self.regs.write(rd, self.alu_out)
            elif reg_src == "mem":
                vec_n = sigs.get("mem_vec", 0)
                if vec_n == 4 and self._vld_tmp is not None:
                    self.vregs.write(rd, self._vld_tmp)
                else:
                    self.regs.write(rd, self.mdr)
            elif reg_src == "pc":
                self.regs.write(rd, self.pc)
            elif reg_src == "imm_shl11":
                self.regs.write(rd, (ir & 0x1FFFFF) << 11)

        pc_src = sigs.get("pc_src")
        if sigs.get("pc_we") and pc_src:
            if pc_src == "inc":
                self.pc = (self.pc + 1) & 0xFFFFFFFF
            elif pc_src == "ir_u26":
                self.pc = ir & 0x3FFFFFF
            elif pc_src == "ir_u21":
                self.pc = ir & 0x1FFFFF
            elif pc_src == "reg":
                self.pc = self.regs.read(rd)
            elif pc_src == "branch":
                self._branch(ir)

        if sigs.get("halt"):
            halted = True

        return halted

    def _branch(self, ir):
        rs1 = (ir >> 16) & 0x1F
        rs2 = (ir >> 11) & 0x1F
        off = self.sig_sext(ir)
        a_val = self.regs.read(rs1)
        b_val = self.regs.read(rs2)
        a_s = a_val if not (a_val & 0x80000000) else a_val | ~0x7FFFFFFF
        b_s = b_val if not (b_val & 0x80000000) else b_val | ~0x7FFFFFFF
        name = OPCODE_NAMES.get((ir >> 26) & 0x3F, "")
        taken = {
            "BEQ": a_val == b_val, "BNE": a_val != b_val,
            "BLT": a_s < b_s, "BLE": a_s <= b_s,
            "BGT": a_s > b_s, "BGE": a_s >= b_s,
            "BGTU": a_val > b_val, "BLEU": a_val <= b_val,
        }.get(name, False)
        if taken:
            self.pc = (self.pc + off) & 0xFFFFFFFF

    def dump_state(self):
        return {
            "pc": self.pc, "ir": self.ir,
            "a": self.a, "b": self.b,
            "alu_out": self.alu_out, "mdr": self.mdr,
        }
