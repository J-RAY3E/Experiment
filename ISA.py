OPCODES = {
    "NOP":0,"LW":1,"SW":2,"LB":3,"SB":4,"LUI":5,
    "ADD":6,"SUB":7,"MUL":8,"DIV":9,"REM":0xA,"MULH":0xB,
    "AND":0xC,"OR":0xD,"XOR":0xE,"NOT":0xF,
    "SLL":0x10,"SRL":0x11,"SRA":0x12,"SLT":0x13,
    "ADDI":0x14,"ANDI":0x15,"ORI":0x16,"XORI":0x17,
    "SLLI":0x18,"SRLI":0x19,"SRAI":0x1A,"SLTI":0x1B,
    "BEQ":0x20,"BNE":0x21,"BLT":0x22,"BLE":0x23,
    "BGT":0x24,"BGE":0x25,"BGTU":0x26,"BLEU":0x27,
    "J":0x28,"JAL":0x29,"JR":0x2A,
    "VADD":0x30,"VSUB":0x31,"VMUL":0x32,"VDIV":0x33,
    "VLD":0x34,"VST":0x35,"VCMP":0x36,"HALT":0x3F,
}

OPCODE_NAMES = {v:k for k,v in OPCODES.items()}

REG_NAMES = [
    "zero","ra","sp","gp","a0","a1","a2","a3",
    "a4","a5","a6","a7","t0","t1","t2","t3",
    "t4","t5","s0","s1","s2","s3","s4","s5",
    "s6","s7","s8","s9","s10","s11","t6","tp",
]

REG = {n:i for i,n in enumerate(REG_NAMES)}

# Instruction format sets
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

# Combined for type checking
R_IL_FORMAT = R_FORMAT | I_FORMAT | L_FORMAT
R_ILV_FORMAT = R_IL_FORMAT | V_FORMAT

def _sext11(imm):
    if imm & 0x400:
        return imm | ~0x7FF
    return imm

def decode(word):
    op = (word >> 26) & 0x3F
    name = OPCODE_NAMES.get(op, "???")
    d = {"opcode": op, "name": name, "word": word}
    d["rd"] = (word >> 21) & 0x1F
    d["rs1"] = (word >> 16) & 0x1F
    d["rs2"] = (word >> 11) & 0x1F
    imm11 = word & 0x7FF
    d["imm"] = imm11
    d["imm_s"] = _sext11(imm11)
    d["imm_u21"] = word & 0x1FFFFF
    d["imm_u26"] = word & 0x3FFFFFF
    return d

def encode(opcode, rd=0, rs1=0, rs2=0, imm=0):
    name = OPCODE_NAMES.get(opcode, "")
    s1 = (rd & 0x1F) << 21
    s2 = (rs1 & 0x1F) << 16
    s3 = (rs2 & 0x1F) << 11
    im = imm & 0x7FF

    if name in R_FORMAT | V_FORMAT:
        if name == "NOT":
            return (opcode << 26) | s1 | s2
        if name == "NOP":
            return 0
        return (opcode << 26) | s1 | s2 | s3

    if name in I_FORMAT | L_FORMAT | VL_FORMAT:
        return (opcode << 26) | s1 | s2 | im

    if name in S_FORMAT:
        return (opcode << 26) | s1 | s2 | im

    if name in B_FORMAT:
        return (opcode << 26) | s2 | s3 | im

    if name in U_FORMAT:
        return (opcode << 26) | s1 | (imm & 0x1FFFFF)

    if name in J_FORMAT:
        return (opcode << 26) | (imm & 0x3FFFFFF)

    if name in JL_FORMAT:
        return (opcode << 26) | s1 | (imm & 0x1FFFFF)

    if name in JR_FORMAT:
        return (opcode << 26) | s1

    if name == "HALT":
        return 0xFC000000

    return (opcode << 26) | s1 | s2 | s3 | im

def sign_extend(value, bits=11):
    if value & (1 << (bits - 1)):
        return value - (1 << bits)
    return value
