"""Two-pass assembler: converts RISC assembly text to 32-bit binary machine code.

Usage:
    data, listing = assemble(source_text)       # returns bytes + listing lines
    count = write_binary(source, bin_path, lst_path)  # writes files directly

The assembler handles:
- R-type, I-type, B-type, U-type, J-type, JAL-type, JR-type, V-type instructions
- Pseudo-instructions: LI, MV, JMP, BEQZ, BNEZ, BGTZ, BLTZ
- Directives: .org, .word, .string (Pascal-style)
- Labels and PC-relative branch offset calculation
- Two-pass design: pass 1 collects labels, pass 2 encodes instructions

Encoding format (32-bit fixed length):
    R-type: [op(6) | rd(5) | rs1(5) | rs2(5) | 0(11)]
    I-type: [op(6) | rd(5) | rs1(5) | 0(5) | imm(11)]
    B-type: [op(6) | 0(5) | rs1(5) | rs2(5) | offset(11)]
    U-type: [op(6) | rd(5) | imm(21)]
    J-type: [op(6) | target(26)]
See docs/language.md for full specification.
"""

import struct, re

OPCODES = {
    "ADD":6,"SUB":7,"MUL":8,"DIV":9,"REM":0xA,"MULH":0xB,
    "AND":0xC,"OR":0xD,"XOR":0xE,"NOT":0xF,
    "SLL":0x10,"SRL":0x11,"SRA":0x12,"SLT":0x13,"NOP":0,
    "ADDI":0x14,"ANDI":0x15,"ORI":0x16,"XORI":0x17,
    "SLLI":0x18,"SRLI":0x19,"SRAI":0x1A,"SLTI":0x1B,
    "LW":1,"SW":2,"LB":3,"SB":4,"LUI":5,
    "BEQ":0x20,"BNE":0x21,"BLT":0x22,"BLE":0x23,
    "BGT":0x24,"BGE":0x25,"BGTU":0x26,"BLEU":0x27,
    "J":0x28,"JAL":0x29,"JR":0x2A,
    "VADD":0x30,"VSUB":0x31,"VMUL":0x32,"VDIV":0x33,
    "VLD":0x34,"VST":0x35,"VCMP":0x36,"HALT":0x3F,
}
R = {"ADD","SUB","MUL","DIV","REM","MULH","AND","OR","XOR","NOT","SLL","SRL","SRA","SLT","NOP"}
I = {"ADDI","ANDI","ORI","XORI","SLLI","SRLI","SRAI","SLTI"}
L = {"LW","LB"}   ; S = {"SW","SB"}
B = {"BEQ","BNE","BLT","BLE","BGT","BGE","BGTU","BLEU"}
V = {"VADD","VSUB","VMUL","VDIV","VCMP"}
P = {"LI","MV","JMP","BEQZ","BNEZ","BGTZ","BLTZ"}
REG = dict(zip(["zero","ra","sp","gp","a0","a1","a2","a3","a4","a5","a6","a7",
    "t0","t1","t2","t3","t4","t5","s0","s1","s2","s3","s4","s5","s6","s7",
    "s8","s9","s10","s11","t6","tp"], range(32)))

def rnum(s):
    s = s.strip().lower()
    if s in REG: return REG[s]
    m = re.match(r"r(\d+)$", s, re.I)
    if m: return int(m.group(1))
    raise ValueError(f"bad reg {s}")

def vnum(s):
    return int(s.strip().upper().lstrip("V"))

def imm(s):
    s = s.strip()
    return int(s,16) if s.startswith("0x") or s.startswith("0X") else int(s,10)

def expand(ops, m):
    lines = []
    if m == "LI":
        v = imm(ops[1])
        if -1024<=v<=1023: lines.append({"lb":None,"m":"ADDI","ops":[ops[0],"zero",str(v)]})
        elif 0<=v<=2097151: lines.append({"lb":None,"m":"LUI","ops":[ops[0],str(v)]})
        else:
            u=(v>>11)&0x1FFFFF; lo=v&0x7FF
            if lo>1023: lo-=2048; u+=1
            lines.extend([{"lb":None,"m":"LUI","ops":[ops[0],str(u)]},{"lb":None,"m":"ADDI","ops":[ops[0],ops[0],str(lo)]}])
    elif m=="MV": lines.append({"lb":None,"m":"ADD","ops":[ops[0],ops[1],"zero"]})
    elif m=="JMP": lines.append({"lb":None,"m":"J","ops":[ops[0]]})
    elif m in P:
        rn=dict(BEQZ="BEQ",BNEZ="BNE",BGTZ="BLT",BLTZ="BLT")
        if m=="BGTZ": lines.append({"lb":None,"m":rn[m],"ops":["zero",ops[0],ops[1]]})
        else: lines.append({"lb":None,"m":rn[m],"ops":[ops[0],"zero",ops[1]]})
    return lines

def encode(mnem, ops, lbls, addr):
    op = OPCODES[mnem]
    def lr(s): return resolve_label(s) if s in lbls else None
    def resolve_label(s):
        if s in lbls: return lbls[s]
        raise ValueError(f"unknown label {s}")

    if mnem in R:
        rd=rnum(ops[0])
        if mnem=="NOT": return (op<<26)|(rd<<21)|(rnum(ops[1])<<16)|0
        if mnem=="NOP": return 0
        return (op<<26)|(rd<<21)|(rnum(ops[1])<<16)|(rnum(ops[2])<<11)|0
    if mnem in I or mnem in L:
        return (op<<26)|(rnum(ops[0])<<21)|(rnum(ops[1])<<16)|(imm(ops[2])&0x7FF)
    if mnem in S:
        return (op<<26)|(rnum(ops[0])<<21)|(rnum(ops[1])<<16)|(imm(ops[2])&0x7FF)
    if mnem in B:
        t=resolve_label(ops[2]); off=t-addr-1
        if off<-1024 or off>1023: raise ValueError(f"branch offset {off} out of range")
        return (op<<26)|(rnum(ops[0])<<16)|(rnum(ops[1])<<11)|(off&0x7FF)
    if mnem=="LUI": return (op<<26)|(rnum(ops[0])<<21)|(imm(ops[1])&0x1FFFFF)
    if mnem=="J": return (op<<26)|(resolve_label(ops[0])&0x3FFFFFF)
    if mnem=="JAL": return (op<<26)|(rnum(ops[0])<<21)|(resolve_label(ops[1])&0x1FFFFF)
    if mnem=="JR": return (op<<26)|(rnum(ops[0])<<21)|0
    if mnem in V:
        return (op<<26)|(vnum(ops[0])<<21)|(vnum(ops[1])<<16)|(vnum(ops[2])<<11)|0
    if mnem=="VLD":
        m2=re.match(r"\[(\w+)\s*\+\s*([^\]]+)\]","".join(ops[1:]))
        return (op<<26)|(vnum(ops[0])<<21)|(rnum(m2.group(1))<<16)|(imm(m2.group(2))&0x7FF) if m2 else 0
    if mnem=="VST":
        m2=re.match(r"\[(\w+)\s*\+\s*([^\]]+)\]","".join(ops[1:]))
        return (op<<26)|(vnum(ops[0])<<21)|(rnum(m2.group(1))<<16)|(imm(m2.group(2))&0x7FF) if m2 else 0
    if mnem=="HALT": return 0xFC000000
    raise ValueError(f"unknown {mnem}")

def assemble(source):
    lines=[]
    for text in source.split("\n"):
        text=text.strip()
        if not text or text.startswith(";"): lines.append({"lb":None,"m":None,"ops":[]}); continue
        cmt=""
        if ";" in text: i=text.index(";"); cmt=text[i:].strip(); text=text[:i].strip()
        lb=None
        if ":" in text:
            p=text.split(":",1)
            if re.match(r"^[a-zA-Z_]\w*$",p[0].strip()): lb=p[0].strip(); text=p[1].strip()
        if not text: lines.append({"lb":lb,"m":None,"ops":[]}); continue
        toks=[t for t in re.split(r"[\s,]+",text) if t]
        m=toks[0].upper(); ops=toks[1:]
        if m in P:
            for e in expand(ops,m):
                e["lb"]=lb; lb=None
                lines.append(e)
        else: lines.append({"lb":lb,"m":m,"ops":ops})

    lbls={}; addr=0
    for ln in lines:
        if ln["lb"]: lbls[ln["lb"]]=addr
        m=ln["m"]
        if m==".ORG": addr=imm(ln["ops"][0])
        elif m==".WORD": addr+=len(ln["ops"])
        elif m==".STRING":
            s=ln["ops"][0]
            if s[0]=='"': s=s[1:-1]
            addr+=1+len(s)
        elif m: addr+=1

    data=b""; lst=[]
    for ln in lines:
        m=ln["m"]; ops=ln["ops"]
        if not m: continue
        if m==".ORG":
            addr=imm(ops[0])
            lst.append(f"        .org {ops[0]}")
        elif m==".WORD":
            for o in ops: data+=struct.pack("<I",imm(o)&0xFFFFFFFF)
            lst.append(f"        .word {' '.join(ops)}")
        elif m==".STRING":
            s=ops[0]
            if s[0]=='"': s=s[1:-1]
            s=s.replace("\\n","\n").replace("\\t","\t").replace("\\r","\r")
            data+=struct.pack("<I",len(s))
            for c in s: data+=struct.pack("<I",ord(c))
            lst.append(f"        .string {ops[0]}")
        else:
            w=encode(m,ops,lbls,addr)
            data+=struct.pack("<I",w)
            lst.append(f"{addr:04X} - {w:08X} - {m} {' '.join(ops)}")
            addr+=1
    return data, lst

def write_binary(src, bin_path, lst_path):
    data, lst = assemble(src)
    with open(bin_path,"wb") as f: f.write(data)
    with open(lst_path,"w",encoding="utf-8") as f: f.write("\n".join(lst))
    return len(data)//4
