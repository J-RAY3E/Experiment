import re
import struct
from typing import Any

from src.isa import (
    B_FORMAT,
    HALT_WORD,
    I_FORMAT,
    IMM11_MASK,
    IMM12_MASK,
    IMM20_MASK,
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
IMM12_MIN, IMM12_MAX = -2048, 2047
IMM20_MAX = 0xFFFFF
BRANCH_MIN, BRANCH_MAX = -1024, 1023


def rnum(s: str) -> int:
    s = s.strip().lower()
    if s in REG:
        return REG[s]
    m = re.match(r"r(\d+)$", s, re.I)
    if m:
        return int(m.group(1))
    raise ValueError(f"bad register: {s}")


def vnum(s: str) -> int:
    return int(s.strip().upper().lstrip("V"))


def imm(s: str) -> int:
    s = s.strip()
    if s.startswith("0x") or s.startswith("0X"):
        return int(s, 16)
    return int(s, 10)


def expand(ops, mnem):
    lines: list[dict[str, Any]] = []
    if mnem == "LI":
        v = imm(ops[1])
        if IMM12_MIN <= v <= IMM12_MAX:
            lines.append({"lb": None, "m": "ADDI", "ops": [ops[0], "zero", str(v)]})
        elif 0 <= v <= IMM20_MAX:
            lines.append({"lb": None, "m": "LUI", "ops": [ops[0], str(v)]})
        else:
            upper, lower = (v >> 12) & IMM20_MASK, v & IMM12_MASK
            if lower > IMM12_MAX:
                lower -= IMM12_MASK + 1
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
    if mnem == "NOP":
        return 0
    rd = rnum(ops[0])
    if mnem == "NOT":
        return (op << OPCODE_SHIFT) | (rd << RD_SHIFT) | (rnum(ops[1]) << RS1_SHIFT)
    return (op << OPCODE_SHIFT) | (rd << RD_SHIFT) | (rnum(ops[1]) << RS1_SHIFT) | (rnum(ops[2]) << RS2_SHIFT)


def _encode_i_format(op, ops, labels):
    try:
        val = int(ops[2], 0)
    except ValueError:
        val = labels.get(ops[2], 0)
    return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) | (rnum(ops[1]) << RS1_SHIFT) | (val & IMM12_MASK)


def _encode_s_format(op, ops, labels):
    try:
        val = int(ops[2], 0)
    except ValueError:
        val = labels.get(ops[2], 0)
    return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RS2_SHIFT) | (rnum(ops[1]) << RS1_SHIFT) | (val & IMM11_MASK)


def _encode_b_format(op, ops, labels, addr):
    target = labels.get(ops[2])
    if target is None:
        raise ValueError(f"unknown label: {ops[2]}")
    off = target - addr - 4
    if off < BRANCH_MIN or off > BRANCH_MAX:
        raise ValueError(f"branch offset {off} out of range")
    return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RS1_SHIFT) | (rnum(ops[1]) << RS2_SHIFT) | (off & IMM11_MASK)


def encode(mnem, ops, labels, addr):
    op = OPCODES[mnem]
    if mnem in R_FORMAT:
        return _encode_r_format(op, mnem, ops)
    if mnem in I_FORMAT or mnem in L_FORMAT:
        return _encode_i_format(op, ops, labels)
    if mnem in S_FORMAT:
        return _encode_s_format(op, ops, labels)
    if mnem in B_FORMAT:
        return _encode_b_format(op, ops, labels, addr)
    if mnem == "LUI":
        return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) | (imm(ops[1]) & IMM20_MASK)
    if mnem == "J":
        return (op << OPCODE_SHIFT) | (labels.get(ops[0], 0) & IMM26_MASK)
    if mnem == "JAL":
        return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RD_SHIFT) | (labels.get(ops[1], 0) & IMM21_MASK)
    if mnem == "JR":
        return (op << OPCODE_SHIFT) | (rnum(ops[0]) << RS1_SHIFT)
    if mnem in V_FORMAT:
        return (op << OPCODE_SHIFT) | (vnum(ops[0]) << RD_SHIFT) | (vnum(ops[1]) << RS1_SHIFT) | (vnum(ops[2]) << RS2_SHIFT)
    if mnem in {"VLD", "VST"}:
        m2 = re.match(r"\[(\w+)\s*\+\s*([^\]]+)\]", "".join(ops[1:]))
        if m2:
            return (
                (op << OPCODE_SHIFT)
                | (vnum(ops[0]) << RD_SHIFT)
                | (rnum(m2.group(1)) << RS1_SHIFT)
                | (imm(m2.group(2)) & IMM12_MASK)
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
    labels, addr_code, addr_data = {}, 0, 0
    use_separate = any(ln["m"] in (".TEXT", ".DATA") for ln in lines)
    section = "code"
    for ln in lines:
        if ln["lb"]:
            labels[ln["lb"]] = addr_data if section == "data" else addr_code
        mnem = ln["m"]
        if mnem == ".TEXT":
            section = "code"
            if ln["ops"]:
                addr_code = imm(ln["ops"][0])
        elif mnem == ".DATA":
            section = "data"
            if ln["ops"]:
                addr_data = imm(ln["ops"][0])
        elif mnem == ".ORG":
            n = imm(ln["ops"][0])
            if use_separate:
                if section == "code":
                    addr_code = n
                else:
                    addr_data = n
            else:
                addr_code = addr_data = n
        elif mnem in (".WORD", ".STRING"):
            if not use_separate and section == "code":
                addr_data = addr_code
            section = "data"
            if mnem == ".WORD":
                addr_data += len(ln["ops"]) * 4
            else:
                raw = ln["ops"][0]
                s = raw[1:-1] if raw.startswith('"') else raw
                s = s.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
                s = s.replace('\\"', '"').replace("\\\\", "\\")
                addr_data += 4 + len(s)
        elif mnem:
            section = "code"
            addr_code += 4
    return labels


def _generate_code(lines, labels):
    data, lst = b"", []
    addr_code, addr_data = 0, 0
    use_separate = any(ln["m"] in (".TEXT", ".DATA") for ln in lines)
    section = "code"
    for ln in lines:
        mnem, ops = ln["m"], ln["ops"]
        if not mnem:
            continue
        if mnem == ".TEXT":
            section = "code"
            if ops:
                addr_code = imm(ops[0])
            lst.append(f"        .text {ops[0]}" if ops else "        .text")
        elif mnem == ".DATA":
            section = "data"
            if ops:
                addr_data = imm(ops[0])
            lst.append(f"        .data {ops[0]}" if ops else "        .data")
        elif mnem == ".ORG":
            n = imm(ops[0])
            if use_separate:
                if section == "code":
                    addr_code = n
                else:
                    addr_data = n
            else:
                addr_code = addr_data = n
            lst.append(f"        .org {ops[0]}")
        elif mnem == ".WORD":
            if not use_separate and section == "code":
                addr_data = addr_code
            section = "data"
            for o in ops:
                w = imm(o) & WORD_MASK
                data += struct.pack("<I", w)
                lst.append(f"{addr_data:04X} - {w:08X} - .WORD {o}")
                addr_data += 4
        elif mnem == ".STRING":
            if not use_separate and section == "code":
                addr_data = addr_code
            section = "data"
            s = ops[0][1:-1].replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r")
            data += struct.pack("<I", len(s))
            lst.append(f"{addr_data:04X} - {len(s):08X} - .STRING_LEN {len(s)}")
            addr_data += 4
            for c in s:
                val = ord(c)
                data += struct.pack("B", val)
                lst.append(f"{addr_data:04X} - {val:02X} - .CHAR {c!r}")
                addr_data += 1
        else:
            section = "code"
            w = encode(mnem, ops, labels, addr_code)
            data += struct.pack("<I", w)
            lst.append(f"{addr_code:04X} - {w:08X} - {mnem} {' '.join(ops)}")
            addr_code += 4
    return data, lst


def assemble(source):
    lines: list[dict[str, Any]] = []
    for text in source.split("\n"):
        text = text.strip()
        if not text or text.startswith(";"):
            lines.append({"lb": None, "m": None, "ops": []})
            continue
        if ";" in text:
            text = text[: text.index(";")].strip()
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


def write_binary(src: str, bin_path: str, lst_path: str) -> int:
    data, lst = assemble(src)
    with open(bin_path, "wb") as f:
        f.write(data)
    with open(lst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))
    return len(data)


def main(source_path: str, target_prefix: str) -> int:
    with open(source_path, encoding="utf-8") as f:
        src = f.read()
    bin_path = target_prefix + ".bin"
    lst_path = target_prefix + ".lst"
    return write_binary(src, bin_path, lst_path)
