import re
import struct

from src.ISA import (
    B_FORMAT,
    HALT_WORD,
    I_FORMAT,
    IMM11_MASK,
    IMM21_MASK,
    IMM26_MASK,
    L_FORMAT,
    OPCODE_SHIFT,
    OPCODES,
    R_FORMAT,
    RD_SHIFT,
    REG,
    RS1_SHIFT,
    RS2_SHIFT,
    S_FORMAT,
    V_FORMAT,
    WORD_MASK,
)

PSEUDO_SET = {"LI", "MV", "JMP", "BEQZ", "BNEZ", "BGTZ", "BLTZ"}
IMM11_MIN, IMM11_MAX = -1024, 1023
IMM21_MAX = 0x1FFFFF
BRANCH_MIN, BRANCH_MAX = -1024, 1023


def rnum(s):
    s = s.strip().lower()
    if s in REG:
        return REG[s]
    m = re.match(r"r(\d+)$", s, re.I)
    if m:
        return int(m.group(1))
    raise ValueError(f"bad register: {s}")

def vnum(s):
    return int(s.strip().upper().lstrip("V"))

def imm(s):
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s, 10)

def expand(ops, mnem):
    lines = []
    if mnem == "LI":
        v = imm(ops[1])
        if IMM11_MIN <= v <= IMM11_MAX:
            lines.append({"lb": None, "m": "ADDI", "ops": [ops[0], "zero", str(v)]})
        elif 0 <= v <= IMM21_MAX:
            lines.append({"lb": None, "m": "LUI", "ops": [ops[0], str(v)]})
        else:
            upper, lower = (v >> 11) & IMM21_MASK, v & IMM11_MASK
            if lower > IMM11_MAX:
                lower -= (IMM11_MASK + 1)
                upper += 1
            lines.append({"lb": None, "m": "LUI", "ops": [ops[0], str(upper)]})
            lines.append({"lb": None, "m": "ADDI", "ops": [ops[0], ops[0], str(lower)]})

    elif mnem == "MV":
        lines.append({"lb": None, "m": "ADD", "ops": [ops[0], ops[1], "zero"]})
    elif mnem == "JMP":
        lines.append({"lb": None, "m": "J", "ops": [ops[0]]})
    elif mnem in PSEUDO_SET:
        real = {"BEQZ": "BEQ", "BNEZ": "BNE", "BGTZ": "BLT", "BLTZ": "BLT"}
        if mnem == "BGTZ":
            lines.append({"lb": None, "m": real[mnem], "ops": ["zero", ops[0], ops[1]]})
        else:
            lines.append({"lb": None, "m": real[mnem], "ops": [ops[0], "zero", ops[1]]})
    return lines


def _encode_r_format(op, mnem, ops):
    rd = rnum(ops[0])
    if mnem == "NOT":
        return (op << OPCODE_SHIFT) | (rd << RD_SHIFT) | (rnum(ops[1]) << RS1_SHIFT)
    if mnem == "NOP":
        return 0
    return (
        (op << OPCODE_SHIFT) | (rd << RD_SHIFT) |
        (rnum(ops[1]) << RS1_SHIFT) | (rnum(ops[2]) << RS2_SHIFT)
    )


def _encode_i_format(op, ops):
    return (
        (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) |
        (rnum(ops[1]) << RS1_SHIFT) | (imm(ops[2]) & IMM11_MASK)
    )


def _encode_s_format(op, ops):
    return (
        (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) |
        (rnum(ops[1]) << RS1_SHIFT) | (imm(ops[2]) & IMM11_MASK)
    )


def _encode_b_format(op, ops, labels, addr):
    target = labels.get(ops[2])
    if target is None:
        raise ValueError(f"unknown label: {ops[2]}")
    off = target - addr - 1
    if off < BRANCH_MIN or off > BRANCH_MAX:
        raise ValueError(f"branch offset {off} out of range")
    return (
        (op << OPCODE_SHIFT) | (rnum(ops[0]) << RS1_SHIFT) |
        (rnum(ops[1]) << RS2_SHIFT) | (off & IMM11_MASK)
    )


def encode(mnem, ops, labels, addr):
    op = OPCODES[mnem]
    if mnem in R_FORMAT:
        return _encode_r_format(op, mnem, ops)
    if mnem in I_FORMAT or mnem in L_FORMAT:
        return _encode_i_format(op, ops)
    if mnem in S_FORMAT:
        return _encode_s_format(op, ops)
    if mnem in B_FORMAT:
        return _encode_b_format(op, ops, labels, addr)
    if mnem == "LUI":
        return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) | (imm(ops[1]) & IMM21_MASK)
    if mnem == "J":
        return (op << OPCODE_SHIFT) | (labels.get(ops[0], 0) & IMM26_MASK)
    if mnem == "JAL":
        return (
            (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) |
            (labels.get(ops[1], 0) & IMM21_MASK)
        )
    if mnem == "JR":
        return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT)
    if mnem in V_FORMAT:
        return (
            (op << OPCODE_SHIFT) | (vnum(ops[0]) << RD_SHIFT) |
            (vnum(ops[1]) << RS1_SHIFT) | (vnum(ops[2]) << RS2_SHIFT)
        )
    if mnem in {"VLD", "VST"}:
        m2 = re.match(r"\[(\w+)\s*\+\s*([^\]]+)\]", "".join(ops[1:]))
        if m2:
            return (
                (op << OPCODE_SHIFT) | (vnum(ops[0]) << RD_SHIFT) |
                (rnum(m2.group(1)) << RS1_SHIFT) | (imm(m2.group(2)) & IMM11_MASK)
            )
        return 0
    if mnem == "HALT":
        return HALT_WORD
    raise ValueError(f"unknown mnemonic: {mnem}")


def _process_line(text, lb):
    if not text:
        return {"lb": lb, "m": None, "ops": []}
    m_str = re.match(r'\.string\s+(".*")\s*$', text, re.I)
    if m_str:
        return {"lb": lb, "m": ".STRING", "ops": [m_str.group(1)]}
    toks = [t for t in re.split(r"[\s,]+", text) if t]
    return {"lb": lb, "m": toks[0].upper(), "ops": toks[1:]}


def _resolve_labels(lines):
    labels, addr = {}, 0
    for ln in lines:
        if ln["lb"]:
            labels[ln["lb"]] = addr
        mnem = ln["m"]
        if mnem == ".ORG":
            addr = imm(ln["ops"][0])
        elif mnem == ".WORD":
            addr += len(ln["ops"])
        elif mnem == ".STRING":
            s = ln["ops"][0][1:-1] if ln["ops"][0].startswith('"') else ln["ops"][0]
            addr += 1 + len(s)
        elif mnem:
            addr += 1
    return labels


def _generate_code(lines, labels):
    data, lst = b"", []
    addr = 0
    for ln in lines:
        mnem, ops = ln["m"], ln["ops"]
        if not mnem:
            continue
        if mnem == ".ORG":
            addr = imm(ops[0])
            lst.append(f"        .org {ops[0]}")
        elif mnem == ".WORD":
            for o in ops:
                data += struct.pack("<I", imm(o) & WORD_MASK)
            lst.append(f"        .word {' '.join(ops)}")
        elif mnem == ".STRING":
            s = ops[0][1:-1].replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
            data += struct.pack("<I", len(s))
            for c in s:
                data += struct.pack("<I", ord(c))
            lst.append(f"        .string {ops[0]}")
        else:
            w = encode(mnem, ops, labels, addr)
            data += struct.pack("<I", w)
            lst.append(f"{addr:04X} - {w:08X} - {mnem} {' '.join(ops)}")
            addr += 1
    return data, lst


def assemble(source):
    lines = []
    for text in source.split("\n"):
        text = text.strip()
        if not text or text.startswith(";"):
            lines.append({"lb": None, "m": None, "ops": []})
            continue
        if ";" in text:
            text = text[:text.index(";")].strip()
        lb = None
        if ":" in text:
            parts = text.split(":", 1)
            if re.match(r"^[a-zA-Z_]\w*$", parts[0].strip()):
                lb = parts[0].strip()
                text = parts[1].strip()

        parsed = _process_line(text, lb)
        if parsed["m"] in PSEUDO_SET:
            for e in expand(parsed["ops"], parsed["m"]):
                e["lb"] = lb
                lb = None
                lines.append(e)
        else:
            lines.append(parsed)

    labels = _resolve_labels(lines)
    return _generate_code(lines, labels)

def write_binary(src, bin_path, lst_path):
    data, lst = assemble(src)
    with open(bin_path, "wb") as f:
        f.write(data)
    with open(lst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))
    return len(data) // 4
