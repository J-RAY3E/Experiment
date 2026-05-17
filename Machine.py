import struct, os, re
from ISA import OPCODES, OPCODE_NAMES, REG, REG_NAMES, decode
from DataPath import DataPath
from ControlPath import ControlPath, Phase

def load_binary(bin_path, lst_path=None):
    with open(bin_path, "rb") as f:
        raw = f.read()
    words = [struct.unpack("<I", raw[i:i+4])[0] for i in range(0, len(raw), 4)]
    instr_words = []
    data_words = []
    data_base = 0
    if lst_path and os.path.exists(lst_path):
        with open(lst_path) as f:
            content = f.read()
        max_addr = -1
        for m in re.finditer(r"^([0-9A-Fa-f]+)\s+-", content, re.M):
            addr = int(m.group(1), 16)
            if addr > max_addr:
                max_addr = addr
        orgs = re.findall(r"\.org\s+(\d+)", content)
        if orgs:
            data_base = int(orgs[-1])
        if max_addr >= 0:
            n_instr = max_addr + 1
            instr_words = words[:min(n_instr, len(words))]
            data_words = words[min(n_instr, len(words)):]
    if not instr_words:
        instr_words = list(words)
        data_words = []
    return instr_words, data_words, data_base

class Machine:
    def __init__(self, bin_path, lst_path=None, input_text=""):
        instr_words, data_words, data_base = load_binary(bin_path, lst_path)
        self.instr_mem = instr_words
        self.dp = DataPath(input_text)
        for i, w in enumerate(data_words):
            self.dp.mem.mem[data_base + i] = w
        self.dp.regs.write(REG["gp"], data_base)
        self.dp.regs.write(REG["sp"], 0x1000)
        self.cp = ControlPath()
        self.halted = False
        self.tick_count = 0
        self.cycle_snapshots = []
        self.vec_lane = 0

    def log_state(self):
        d = self.dp
        self.cycle_snapshots.append({
            "tick": self.tick_count,
            "phase": self.cp.state().name,
            "pc": d.pc,
            "ir": d.ir,
            "a": d.a, "b": d.b,
            "alu_out": d.alu_out,
            "mdr": d.mdr,
        })

    def tick(self):
        if self.halted:
            return
        self.tick_count += 1
        d = self.dp

        ir = d.ir
        op = (ir >> 26) & 0x3F
        iname = OPCODE_NAMES.get(op, '???')

        next_phase = self.cp.next_phase(ir, {})

        sigs = self.cp.control_signals(ir)

        inst_word = None
        if sigs.get("ir_we"):
            pc = d.pc
            inst_word = self.instr_mem[pc] if pc < len(self.instr_mem) else 0

        halted = d.tick(sigs, inst_word)

        if sigs.get("pc_src") == "branch":
            pass

        # Clock the state register
        self.cp.state_reg.clock(next_state=next_phase)

        if halted:
            self.halted = True

        self.log_state()

    def run(self, max_ticks=100000):
        while not self.halted and self.tick_count < max_ticks:
            self.tick()
        out = ""
        for c in self.dp.output_buffer:
            if isinstance(c, int) and 0 <= c < 256:
                out += chr(c)
            elif isinstance(c, str):
                out += c
        return out

    def get_journal(self):
        lines = []
        PHASE_SKIP_A = {"NOP","HALT","J","VADD","VSUB","VMUL","VDIV","VCMP","VLD","VST"}
        PHASE_SKIP_AB = PHASE_SKIP_A | {"BEQ","BNE","BLT","BLE","BGT","BGE","BGTU","BLEU"}
        for s in self.cycle_snapshots:
            ir = s["ir"]
            dcd = decode(ir)
            pc = s["pc"]
            name = dcd["name"]
            a = s["a"]; b = s["b"]; ao = s["alu_out"]
            l = f"tick={s['tick']:>6} phase={s['phase']:>6} pc={pc:04X} ir={ir:08X} {name:>5}"
            if name not in PHASE_SKIP_AB:
                l += f" a={a:08X} b={b:08X}"
            if name in ("ADD","SUB","MUL","ADDI","ANDI","ORI","XORI","LUI"):
                l += f" alu={ao:08X}"
            lines.append(l)
        return "\n".join(lines)

    def dump_registers(self):
        return {REG_NAMES[i]: self.dp.regs.regs[i] for i in range(32)}

def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python Machine.py <binary.bin> [input.txt]")
        sys.exit(1)
    bin_path = sys.argv[1]
    lst_path = bin_path.replace(".bin", ".lst") if bin_path.endswith(".bin") else bin_path + ".lst"
    if not os.path.exists(lst_path):
        lst_path = None
    input_text = ""
    if len(sys.argv) > 2:
        with open(sys.argv[2]) as f:
            input_text = f.read()
    m = Machine(bin_path, lst_path, input_text)
    out = m.run()
    print("Output:")
    print(repr(out))
    print("\nJournal (last 20):")
    lines = m.get_journal().split("\n")
    for l in lines[-20:]:
        print(l)
    print(f"\nTotal ticks: {m.tick_count}")
    print("\nRegisters:")
    for k, v in m.dump_registers().items():
        if v: print(f"  {k}: {v} (0x{v:08X})")

if __name__ == "__main__":
    main()
