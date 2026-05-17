from enum import Enum, auto
from ISA import OPCODES, OPCODE_NAMES, REG, decode

R_FORMAT = {"ADD","SUB","MUL","DIV","REM","MULH","AND","OR","XOR","NOT","SLL","SRL","SRA","SLT","NOP"}
I_FORMAT = {"ADDI","ANDI","ORI","XORI","SLLI","SRLI","SRAI","SLTI"}
L_FORMAT = {"LW","LB"}
S_FORMAT = {"SW","SB"}
B_FORMAT = {"BEQ","BNE","BLT","BLE","BGT","BGE","BGTU","BLEU"}
J_FORMAT = {"J"}
JL_FORMAT = {"JAL"}
JR_FORMAT = {"JR"}
U_FORMAT = {"LUI"}
V_FORMAT = {"VADD","VSUB","VMUL","VDIV","VCMP"}
VL_FORMAT = {"VLD","VST"}
R_ILV_FORMAT = R_FORMAT | I_FORMAT | L_FORMAT | V_FORMAT

ALU_OPS = {
    "ADD":"ADD","SUB":"SUB","MUL":"MUL","DIV":"DIV","REM":"REM","MULH":"MULH",
    "AND":"AND","OR":"OR","XOR":"XOR","NOT":"NOT",
    "SLL":"SLL","SRL":"SRL","SRA":"SRA","SLT":"SLT",
    "ADDI":"ADD","ANDI":"AND","ORI":"OR","XORI":"XOR",
    "SLLI":"SLL","SRLI":"SRL","SRAI":"SRA","SLTI":"SLT",
}

class Phase(Enum):
    Fetch = auto()
    Execute = auto()
    VecOp = auto()
    Halt = auto()

class StateRegister:
    def __init__(self):
        self._state = Phase.Fetch

    def state(self):
        return self._state

    def clock(self, reset=False, next_state=None):
        if reset:
            self._state = Phase.Fetch
        elif next_state is not None:
            self._state = next_state

class ControlPath:
    def __init__(self):
        self.state_reg = StateRegister()
        self.vec_lane = 0

    def state(self):
        return self.state_reg.state()

    def next_phase(self, opcode, conditions=None):
        current = self.state_reg.state()
        op = (opcode >> 26) & 0x3F
        name = OPCODE_NAMES.get(op, "???")
        if conditions is None:
            conditions = {}

        if current == Phase.Fetch:
            return Phase.Execute

        elif current == Phase.Execute:
            if name == "HALT":
                return Phase.Halt
            return Phase.Fetch

        elif current == Phase.VecOp:
            if conditions.get("vec_done", False):
                return Phase.Fetch
            return Phase.VecOp

        elif current == Phase.Halt:
            return Phase.Halt

        return Phase.Fetch

    def control_signals(self, ir):
        op = (ir >> 26) & 0x3F
        name = OPCODE_NAMES.get(op, "???")
        current = self.state_reg.state()

        sigs = {
            "ir_we": False, "pc_we": False, "pc_src": None,
            "a_sel": None, "b_sel": None,
            "alu_op": None, "alu_exec": False,
            "reg_we": False, "reg_src": None,
            "mem_rd": False, "mem_wr": False, "mem_byte": False,
            "check_out": False,
            "v_en": False, "mem_vec": 0,
            "halt": False,
        }

        if current == Phase.Fetch:
            sigs["ir_we"] = True
            sigs["pc_we"] = True
            sigs["pc_src"] = "inc"

        elif current == Phase.Execute:
            if name in R_FORMAT:
                if name == "NOP":
                    pass
                else:
                    sigs["alu_op"] = name
                    sigs["alu_exec"] = True
                    sigs["a_sel"] = "rs1"
                    sigs["b_sel"] = "rs2"
                    sigs["reg_we"] = True
                    sigs["reg_src"] = "alu"
                if name == "NOT":
                    sigs["b_sel"] = "zero"

            elif name in I_FORMAT:
                sigs["alu_op"] = ALU_OPS.get(name, "ADD")
                sigs["alu_exec"] = True
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "imm"
                sigs["reg_we"] = True
                sigs["reg_src"] = "alu"

            elif name in L_FORMAT:
                sigs["alu_op"] = "ADD"
                sigs["alu_exec"] = True
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "imm"
                sigs["mem_rd"] = True
                sigs["reg_we"] = True
                sigs["reg_src"] = "mem"
                if name == "LB":
                    sigs["mem_byte"] = True

            elif name in S_FORMAT:
                sigs["alu_op"] = "ADD"
                sigs["alu_exec"] = True
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "imm"
                sigs["mem_wr"] = True
                sigs["check_out"] = True
                if name == "SB":
                    sigs["mem_byte"] = True

            elif name in B_FORMAT:
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "rs2"
                sigs["pc_we"] = True
                sigs["pc_src"] = "branch"

            elif name in J_FORMAT:
                sigs["pc_we"] = True
                sigs["pc_src"] = "ir_u26"

            elif name in JL_FORMAT:
                sigs["reg_we"] = True
                sigs["reg_src"] = "pc"
                sigs["pc_we"] = True
                sigs["pc_src"] = "ir_u21"

            elif name in JR_FORMAT:
                sigs["pc_we"] = True
                sigs["pc_src"] = "reg"

            elif name in U_FORMAT:
                sigs["reg_we"] = True
                sigs["reg_src"] = "imm_shl11"

            elif name in V_FORMAT:
                sigs["v_en"] = True
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "rs2"
                sigs["alu_exec"] = True
                sigs["alu_op"] = "V_OP"
                sigs["reg_we"] = True
                sigs["reg_src"] = "alu"

            elif name in VL_FORMAT:
                sigs["v_en"] = True
                sigs["alu_op"] = "ADD"
                sigs["alu_exec"] = True
                sigs["a_sel"] = "rs1"
                sigs["b_sel"] = "imm"
                if name == "VLD":
                    sigs["mem_rd"] = True
                    sigs["mem_vec"] = 4
                    sigs["reg_we"] = True
                    sigs["reg_src"] = "mem"
                else:
                    sigs["mem_wr"] = True
                    sigs["mem_vec"] = 4

            elif name == "HALT":
                sigs["halt"] = True

        elif current == Phase.Halt:
            sigs["halt"] = True

        return sigs
