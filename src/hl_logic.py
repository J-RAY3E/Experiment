from __future__ import annotations

import re

from src.isa import IMM20_MASK, IN_PORT, OUT_PORT

PREC = [{"||"}, {"&&"}, {"|"}, {"^"}, {"&"}, {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"}, {"+", "-"}, {"*", "/", "%"}]
BM = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "REM", "&": "AND", "|": "OR", "^": "XOR", "<<": "SLL", ">>": "SRL"}
VBM = {"+": "VADD", "-": "VSUB", "*": "VMUL", "/": "VDIV"}
KW = {"function", "let", "if", "else", "while", "halt", "true", "false", "return"}
BI = {"print", "print_str", "print_num", "read", "readln", "vload", "vadd", "vstore", "len"}
TREGS = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
VREGS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"]


class HL:
    def __init__(self):
        self.vars = {}
        self.arrays = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.nv = 0
        self.sc_nest = 0
        self.dl = []
        self.strs = []
        self.dv = {}
        self.toks = []
        self.pos = 0
        self.ast = None

    def tokenize(self, s):
        self.toks = []
        for m in re.finditer(
            r'//.*|"[^"\\]*(?:\\.[^"\\]*)*"|0[xX][0-9a-fA-F]+|\d+|'
            r"'[^'\\]*(?:\\.[^'\\]*)*'|"
            r"[a-zA-Z_]\w*|&&|\|\||<<|>>|<=|>=|==|!=|[-+*/%&|^~<>=!]=?|[{}();,\[\]]",
            s,
        ):
            t = m.group()
            if t.startswith("//"):
                continue
            if t.startswith("0x") or t.startswith("0X"):
                self.toks.append(("H", int(t, 16)))
            elif t.isdigit():
                self.toks.append(("N", int(t)))
            elif t.startswith('"'):
                s = (
                    t[1:-1]
                    .replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace("\\r", "\r")
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )
                self.toks.append(("STR", s))
            elif t.startswith("'"):
                c = t[1:-1]
                v = {"n": 10, "t": 9, "r": 13, "0": 0}.get(c[1], ord(c[1])) if len(c) > 1 and c[0] == "\\" else ord(c)
                self.toks.append(("C", v))
            elif t[0].isalpha() or t[0] == "_":
                self.toks.append(("K" if t in KW else "B" if t in BI else "I", t))
            elif t in "{}();,[]":
                self.toks.append(("S", t))
            else:
                self.toks.append(("O", t))
        self.toks.append(("", ""))
        self.pos = 0

    def peek(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else ("", "")

    def adv(self):
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def exp(self, *v):
        t = self.peek()
        if t[1] in v or t[0] in v:
            return self.adv()
        raise SyntaxError(f"expected {v}, got {t} at {self.pos}")

    def args(self):
        self.exp("(")
        a = []
        while self.peek()[1] != ")":
            a.append(self.pexpr())
            if self.peek()[1] == ",":
                self.adv()
        self.exp(")")
        return a

    def def_params(self):
        self.exp("(")
        params = []
        while self.peek()[1] != ")":
            t = self.peek()
            if t[0] != "I":
                raise SyntaxError(f"expected identifier in function params, got {t}")
            params.append(self.adv()[1])
            if self.peek()[1] == ",":
                self.adv()
        self.exp(")")
        return params

    def parse(self, s):
        self.tokenize(s)
        fs = []
        while self.peek()[0] != "":
            if self.peek() == ("K", "function"):
                self.adv()
                n = self.adv()[1]
                params = self.def_params()
                self.exp("{")
                b = self._stmts("}")
                self.exp("}")
                fd = {"function": n, "body": b}
                if params:
                    fd["params"] = params
                fs.append(fd)
            else:
                self.adv()
        self.ast = {"program": fs}
        return self.ast

    def _stmts(self, e):
        r = []
        while self.peek()[1] != e:
            s = self._stmt()
            if s is not None:
                r.append(s)
        return r

    def _stmt(self):
        t = self.peek()
        if t == ("K", "let"):
            self.adv()
            n = self.exp("I")[1]
            sz = None
            if self.peek()[1] == "[":
                self.adv()
                sz = self.pexpr()
                self.exp("]")
            iv = None
            if self.peek()[1] == "=":
                self.adv()
                iv = self.pexpr()
            self.exp(";")
            d = {"let": n}
            if iv is not None:
                d["init"] = iv
            if sz is not None:
                d["array_size"] = sz
            return d
        if t == ("K", "if"):
            return self._ifwhile("if")
        if t == ("K", "while"):
            return self._ifwhile("while")
        if t == ("K", "halt"):
            self.adv()
            self.exp(";")
            return {"halt": True}
        if t == ("K", "return"):
            self.adv()
            v = self.pexpr() if self.peek()[1] != ";" else None
            self.exp(";")
            return {"return": v}
        if t[0] == "S" and t[1] == "{":
            self.adv()
            b = self._stmts("}")
            self.exp("}")
            return {"block": b}
        if t[0] == "B":
            n = self.adv()[1]
            a = self.args()
            self.exp(";")
            return {"expr_stmt": {"call": n, "args": a}}
        if t[0] == "S" and t[1] == ";":
            self.adv()
            return None
        return self._assign()

    def _ifwhile(self, k):
        self.adv()
        self.exp("(")
        c = self.pexpr()
        self.exp(")")
        b = self._stmt()
        bl = [b] if "block" not in b else b["block"]
        if k == "while":
            return {"while": c, "body": bl}
        el = None
        if self.peek() == ("K", "else"):
            self.adv()
            eb = self._stmt()
            el = [eb] if "block" not in eb else eb["block"]
        return {"if": c, "then": bl, "else": el} if el else {"if": c, "then": bl}

    def _assign(self):
        n = self.adv()[1]
        if self.peek()[1] == "(":
            a = self.args()
            self.exp(";")
            return {"expr_stmt": {"call": n, "args": a}}
        tg = {"var": n}
        while self.peek()[1] == "[":
            self.adv()
            tg = {"index": tg, "at": self.pexpr()}
            self.exp("]")
        self.exp("=")
        v = self.pexpr()
        self.exp(";")
        if "var" in tg:
            return {"assign": n, "value": v}
        return {"index_assign": tg, "value": v}

    def pexpr(self, mp=0):
        res = self._prim()
        while True:
            t = self.peek()
            if t[0] != "O":
                break
            p = next((i for i, lv in enumerate(PREC) if t[1] in lv), -1)
            if p < 0 or p < mp:
                break
            self.adv()
            res = {"binop": t[1], "left": res, "right": self.pexpr(p + 1)}
        return res

    def _prim(self):
        t = self.adv()
        if t[0] in ("N", "H"):
            return {"int": t[1]}
        if t[0] == "C":
            return {"char": t[1]}
        if t[0] == "K" and t[1] in ("true", "false"):
            return {"bool": t[1] == "true"}
        if t[0] == "STR":
            return {"string": t[1]}
        if t[0] == "S" and t[1] == "{":
            e = []
            if self.peek()[1] != "}":
                e.append(self.pexpr())
                while self.peek()[1] == ",":
                    self.adv()
                    e.append(self.pexpr())
            self.exp("}")
            return {"array": e}
        if t[0] in ("I", "B"):
            if self.peek()[1] == "(":
                f = t[1]
                a = self.args()
                return {"call": f, "args": a}
            if t[0] == "I":
                n2 = {"var": t[1]}
                while self.peek()[1] == "[":
                    self.adv()
                    n2 = {"index": n2, "at": self.pexpr()}
                    self.exp("]")
                return n2
            raise SyntaxError(f"unexpected builtin {t} at {self.pos}")
        if t[0] == "S" and t[1] == "(":
            e = self.pexpr()
            self.exp(")")
            return e
        if t[0] == "O" and t[1] in ("-", "~", "!"):
            return {"unary": t[1], "operand": self.pexpr(len(PREC))}
        raise SyntaxError(f"unexpected token {t} at {self.pos}")

    def gen(self, a):
        self.vars = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.nv = 0
        self.sc_nest = 0
        self.dl = []
        self.strs = []
        self.dv = {}
        self.arrays = {}
        for f in a["program"]:
            self._gfunc(f)
        return self._fin()

    def ar(self):
        r = TREGS[self.nr % 7]
        self.nr += 1
        return r

    def av(self):
        r = self.nv
        self.nv += 1
        return f"V{r}"

    def ml(self, p="L"):
        self.lc += 1
        return f"{p}_{self.lc}"

    def em(self, ln=""):
        self.asm.append(("    " + ln) if ln else "")

    I11 = -1024, 1023
    I12 = -2048, 2047

    def vl(self, n):
        if n not in self.vars:
            self.vars[n] = self.do
            self.do += 4
        return self.vars[n]

    def lv(self, n):
        loc = self.vl(n)
        if self.I12[0] <= loc <= self.I12[1]:
            r = self.ar()
            self.em(f"LW {r}, gp, {loc}")
            return r
        tmp = self.ar()
        self.li(loc, tmp)
        self.em(f"ADD {tmp}, gp, {tmp}")
        r = self.ar()
        self.em(f"LW {r}, {tmp}, 0")
        return r

    def sv(self, n, r):
        loc = self.vl(n)
        if self.I11[0] <= loc <= self.I11[1]:
            self.em(f"SW {r}, gp, {loc}")
        else:
            tmp = self.ar()
            self.li(loc, tmp)
            self.em(f"ADD {tmp}, gp, {tmp}")
            self.em(f"SW {r}, {tmp}, 0")

    def li(self, v, r=None):
        rr = r or self.ar()
        if self.I12[0] <= v <= self.I12[1]:
            self.em(f"ADDI {rr}, zero, {v}")
        else:
            lo = v & 0xFFF
            if lo >= 0x800:
                lo -= 0x1000
            hi = (v - lo) >> 12
            self.em(f"LUI {rr}, {hi & IMM20_MASK}")
            if lo:
                self.em(f"ADDI {rr}, {rr}, {lo}")
        return rr

    def als(self, c):
        o = self.do
        self.strs.append((o, c))
        self.do += 4 + len(c) * 4
        return o

    def _gfunc(self, f):
        is_main = f["function"] == "main"
        body_asm: list[str] = []
        saved_asm = self.asm
        self.asm = body_asm
        self.em(f"{f['function']}:")
        for i, p in enumerate(f.get("params", [])):
            if i >= 8:
                break
            self.vl(p)
        for i, p in enumerate(f.get("params", [])):
            if i >= 8:
                break
            self.sv(p, f"a{i}")
        for s in f["body"]:
            self._gs(s)
        if not is_main:
            body_asm[1:1] = [
                "    ADDI sp, sp, -4",
                "    SW ra, sp, 0",
            ]
            body_asm.append("    LW ra, sp, 0")
            body_asm.append("    ADDI sp, sp, 4")
            body_asm.append("    JR ra")
        elif not body_asm or body_asm[-1].strip() != "HALT":
            body_asm.append("    HALT")
        self.asm = saved_asm
        self.asm.extend(body_asm)
        self.dl.append(f["function"])

    def _gs(self, s):
        if "let" in s:
            self._gl(s)
        elif "assign" in s:
            self._ga(s)
        elif "index_assign" in s:
            self._gia(s)
        elif "if" in s:
            self._gc("if", s["if"], s["then"], s.get("else"))
        elif "while" in s:
            self._gc("while", s["while"], s["body"], None)
        elif "return" in s:
            if s["return"] is not None:
                self.em(f"MV a0, {self.er(self.ge(s['return']))}")
        elif "expr_stmt" in s:
            self._ges(s)
        elif "block" in s:
            for x in s["body"]:
                self._gs(x)
        elif "halt" in s:
            self.em("HALT")

    def _gl(self, s):
        n = s["let"]
        iv = s.get("init")
        if s.get("array_size") is not None or (isinstance(iv, dict) and "array" in iv):
            sz = (
                s["array_size"]["int"]
                if s.get("array_size") and isinstance(s["array_size"], dict) and "int" in s["array_size"]
                else (len(iv["array"]) if isinstance(iv, dict) and "array" in iv else 4)
            )
            o = self.do
            self.do += sz * 4
            if isinstance(iv, dict) and "array" in iv:
                for i, el in enumerate(iv["array"]):
                    if i >= sz:
                        break
                    v = self.ge(el)
                    if isinstance(v, int):
                        self.dv[o + i * 4] = v
                    else:
                        vr = self.er(v)
                        ar = self.ar()
                        self.em(f"ADDI {ar}, gp, {o + i * 4}")
                        self.em(f"SW {vr}, {ar}, 0")
            elif iv is not None:
                r = self.ge(iv)
                if isinstance(r, tuple) and r and r[0] == "arr":
                    ro, rn = r[1], r[2]
                    for i in range(min(rn, sz)):
                        ar = self.ar()
                        self.em(f"ADDI {ar}, gp, {ro + i * 4}")
                        self.em(f"LW {ar}, {ar}, 0")
                        self.em(f"SW {ar}, gp, {o + i * 4}")
            self.arrays[n] = (o, sz)
            self.vars[n] = ("arr", o, sz)
            return
        self.vl(n)
        if iv is not None:
            r = self.ge(iv)
            if isinstance(r, tuple) and r and r[0] == "arr":
                off, sz = r[1], r[2]
                self.arrays[n] = (off, sz)
                self.vars[n] = r
            else:
                self.sv(n, self.er(r))

    def _ga(self, s):
        n = s["assign"]
        if n in self.arrays:
            r = self.ge(s["value"])
            if isinstance(r, tuple) and r and r[0] == "arr":
                self.arrays[n] = (r[1], r[2])
                self.vars[n] = r
            return
        self.vl(n)
        self.sv(n, self.er(self.ge(s["value"])))

    def _gia(self, s):
        tg = s["index_assign"]
        if "index" not in tg:
            return
        bl = self._la(tg["index"])
        if bl is None:
            return
        o, _n = bl
        vr = self.er(self.ge(s["value"]))
        ir = self.er(self.ge(tg["at"]))
        ar = self.ar()
        self.em(f"SLLI {ar}, {ir}, 2")
        self.em(f"ADDI {ar}, {ar}, {o}")
        self.em(f"ADD {ar}, {ar}, gp")
        self.em(f"SW {vr}, {ar}, 0")

    def _la(self, n):
        if isinstance(n, dict) and "var" in n and n["var"] in self.arrays:
            return self.arrays[n["var"]]
        if isinstance(n, dict) and "index" in n:
            return self._la(n["index"])
        return None

    def _ges(self, s):
        x = s["expr_stmt"]
        if "call" in x and x["call"] == "print_str":
            a0 = x["args"][0]
            if "string" in a0 or "var" in a0:
                sval = a0["string"] if "string" in a0 else a0["var"]
                so = self.als(sval)
                ba = self.ar()
                le = self.ar()
                i2 = self.ar()
                ch = self.ar()
                po = self.li(OUT_PORT)
                ls = self.ml("ps")
                le2 = self.ml("pe")
                self.em(f"ADDI {ba}, gp, {so}")
                self.em(f"LW {le}, {ba}, 0")
                self.em(f"ADDI {ba}, {ba}, 4")
                self.em(f"ADDI {i2}, zero, 0")
                self.em(f"{ls}:")
                self.em(f"BGE {i2}, {le}, {le2}")
                self.em(f"SLLI {ch}, {i2}, 2")
                self.em(f"ADD {ch}, {ba}, {ch}")
                self.em(f"LW {ch}, {ch}, 0")
                self.em(f"SW {ch}, {po}, 0")
                self.em(f"ADDI {i2}, {i2}, 1")
                self.em(f"J {ls}")
                self.em(f"{le2}:")
                return
        if "call" in x and x["call"] == "print_num":
            if x["args"]:
                val_orig = self.er(self.ge(x["args"][0]))
                val = self.ar()
                self.em(f"MV {val}, {val_orig}")
                div = self.ar()
                tmp = self.ar()
                ten = self.ar()
                po = self.li(OUT_PORT)
                ls = self.ml("pnl")
                l2 = self.ml("pn2")
                l3 = self.ml("pn3")
                self.em(f"ADDI {ten}, zero, 10")
                self.em(f"ADDI {div}, zero, 1")
                self.em(f"{ls}:")
                self.em(f"DIV {tmp}, {val}, {div}")
                self.em(f"BLT {tmp}, {ten}, {l2}")
                self.em(f"MUL {div}, {div}, {ten}")
                self.em(f"J {ls}")
                self.em(f"{l2}:")
                self.em(f"{l3}:")
                self.em(f"DIV {tmp}, {val}, {div}")
                self.em(f"REM {val}, {val}, {div}")
                self.em(f"ADDI {tmp}, {tmp}, 48")
                self.em(f"SW {tmp}, {po}, 0")
                self.em(f"DIV {div}, {div}, {ten}")
                self.em(f"BNE {div}, zero, {l3}")
                return
        if "call" in x and x["call"] == "print":
            po = self.li(OUT_PORT)
            for a in x["args"]:
                self.em(f"SW {self.er(self.ge(a))}, {po}, 0")
            return
        if "call" in x and x["call"] == "readln":
            if len(x["args"]) == 0:
                self.em(f"LW {self.ar()}, {self.li(IN_PORT)}, 0")
                return
            a = x["args"][0]
            o = self.ge(a)
            addr = self.ar()
            i2 = self.ar()
            ch = self.ar()
            tmp = self.ar()
            inp = self.li(IN_PORT)
            if isinstance(o, tuple) and o[0] == "arr":
                self.em(f"ADDI {addr}, gp, {o[1]}")
            elif isinstance(o, int):
                self.em(f"ADDI {addr}, gp, {o}")
            else:
                self.em(f"ADD {addr}, gp, {self.er(o)}")
            self.em(f"ADDI {i2}, zero, 0")
            l1 = self.ml("rl")
            l2 = self.ml("re")
            self.em(f"{l1}:")
            self.em(f"LW {ch}, {inp}, 0")
            self.em(f"BEQ {ch}, zero, {l2}")
            self.em(f"ADDI {tmp}, {ch}, -10")
            self.em(f"BEQ {tmp}, zero, {l2}")
            self.em(f"SLLI {tmp}, {i2}, 2")
            self.em(f"ADD {tmp}, {addr}, {tmp}")
            self.em(f"SW {ch}, {tmp}, 0")
            self.em(f"ADDI {i2}, {i2}, 1")
            self.em(f"J {l1}")
            self.em(f"{l2}:")
            return
        if "call" in x and x["call"] == "vstore":
            o = self.ge(x["args"][0])
            idx = self.ge(x["args"][1]) if len(x["args"]) > 2 else None
            vv = self.ge(x["args"][2] if len(x["args"]) > 2 else x["args"][1])
            ar = self.ar()
            if isinstance(o, tuple) and o[0] == "arr":
                self.em(f"ADDI {ar}, gp, {o[1]}")
            elif isinstance(o, int):
                self.em(f"ADDI {ar}, gp, {o}")
            else:
                self.em(f"ADD {ar}, gp, {self.er(o)}")
            if idx is not None:
                self.em(f"ADD {ar}, {ar}, {self.er(idx)}")
            if isinstance(vv, tuple) and vv[0] == "v":
                self.em(f"VST {vv[1]}, [{ar}+0]")
            return
        if "call" in x:
            for i, a in enumerate(x["args"]):
                if i < 8:
                    self.em(f"MV a{i}, {self.er(self.ge(a))}")
            self.em(f"JAL ra, {x['call']}")

    def _gc(self, k, cond, body, eb):
        lc = self.ml("wc") if k == "while" else None
        le = self.ml("el") if k == "if" else None
        le2 = self.ml("en")
        if k == "while":
            self.em(f"{lc}:")
        cv = self.ge(cond)
        bm = {"==": "BNE", "!=": "BEQ", "<": "BGE", ">=": "BLT", ">": "BLE", "<=": "BGT"}
        if isinstance(cv, tuple) and len(cv) == 3 and cv[0] in bm:
            op, rs1, rs2 = cv
            tg = le if k == "if" else le2
            self.em(f"{bm[op]} {rs1}, {rs2}, {tg}")
        else:
            self.em(f"BEQ {self.er(cv)}, zero, {le if k == 'if' else le2}")
        for s in body:
            self._gs(s)
        if k == "if":
            if eb:
                self.em(f"J {le2}")
                self.em(f"{le}:")
                for s in eb:
                    self._gs(s)
            else:
                self.em(f"{le}:")
            self.em(f"{le2}:")
        else:
            self.em(f"J {lc}")
            self.em(f"{le2}:")

    def ge(self, e, target_reg=None):
        if isinstance(e, int):
            return e
        if "int" in e:
            return e["int"]
        if "char" in e:
            return e["char"]
        if "bool" in e:
            return 1 if e["bool"] else 0
        if "index" in e:
            bl = self._la(e["index"])
            if bl is None:
                return 0
            o, _n = bl
            ir = self.er(self.ge(e["at"]))
            ar = self.ar()
            self.em(f"SLLI {ar}, {ir}, 2")
            self.em(f"ADDI {ar}, {ar}, {o}")
            self.em(f"ADD {ar}, {ar}, gp")
            r = target_reg or self.ar()
            self.em(f"LW {r}, {ar}, 0")
            return r
        if "var" in e:
            n = e["var"]
            if n in self.arrays:
                o, n2 = self.arrays[n]
                return ("arr", o, n2)
            v = self.lv(n)
            if target_reg and target_reg != v:
                self.em(f"MV {target_reg}, {v}")
            return target_reg if target_reg else v
        if "unary" in e:
            ev = self.ge(e["operand"])
            r = target_reg or self.ar()
            if e["unary"] == "-":
                self.em(f"SUB {r}, zero, {self.er(ev)}")
            else:
                self.em(f"XORI {r}, {self.er(ev)}, 1")
            return r
        if "binop" in e:
            op = e["binop"]
            if op in ("&&", "||"):
                sr = f"s{self.sc_nest}"
                self.sc_nest += 1
                r = target_reg or self.ar()
                lv = self.ge(e["left"])
                self.em(f"MV {r}, {self.er(lv)}")
                self.em(f"MV {sr}, {r}")
                le = self.ml("sc")
                if op == "&&":
                    self.em(f"BEQ {sr}, zero, {le}")
                else:
                    self.em(f"BNE {sr}, zero, {le}")
                rv = self.ge(e["right"])
                self.sc_nest -= 1
                if op == "&&":
                    self.em(f"AND {sr}, {sr}, {self.er(rv)}")
                else:
                    self.em(f"OR {sr}, {sr}, {self.er(rv)}")
                self.em(f"{le}:")
                if target_reg and target_reg != sr:
                    self.em(f"MV {target_reg}, {sr}")
                    return target_reg
                return sr
            return self._eb(op, self.ge(e["left"]), self.ge(e["right"]), target_reg)
        if "call" in e and e["call"] == "read":
            r = target_reg or self.ar()
            self.em(f"LW {r}, {self.li(IN_PORT)}, 0")
            return r
        if "call" in e and e["call"] == "len":
            if e["args"] and "var" in e["args"][0] and e["args"][0]["var"] in self.arrays:
                return self.arrays[e["args"][0]["var"]][1]
            return 0
        if "call" in e and e["call"] == "vload":
            o = self.ge(e["args"][0])
            idx = self.ge(e["args"][1]) if len(e["args"]) > 1 else None
            vr = self.av()
            ar = self.ar()
            if isinstance(o, tuple) and o[0] == "arr":
                self.em(f"ADDI {ar}, gp, {o[1]}")
            elif isinstance(o, int):
                self.em(f"ADDI {ar}, gp, {o}")
            else:
                self.em(f"ADD {ar}, gp, {self.er(o)}")
            if idx is not None:
                self.em(f"ADD {ar}, {ar}, {self.er(idx)}")
            self.em(f"VLD {vr}, [{ar}+0]")
            return ("v", vr)
        if "call" in e and e["call"] == "vadd":
            v1 = self.ge(e["args"][0])
            v2 = self.ge(e["args"][1])
            if isinstance(v1, tuple) and isinstance(v2, tuple):
                vr = self.av()
                self.em(f"VADD {vr}, {v1[1]}, {v2[1]}")
                return ("v", vr)
            return 0
        if "call" in e:
            for i, a in enumerate(e["args"]):
                if i < 8:
                    self.em(f"MV a{i}, {self.er(self.ge(a))}")
            self.em(f"JAL ra, {e['call']}")
            r = target_reg or self.ar()
            self.em(f"MV {r}, a0")
            return r
        return 0

    def er(self, v, target_reg=None):
        if isinstance(v, tuple):
            r = target_reg or self.ar()
            op, lr, rr = v
            if op == "<":
                self.em(f"SLT {r}, {lr}, {rr}")
            elif op == ">":
                self.em(f"SLT {r}, {rr}, {lr}")
            elif op == "<=":
                self.em(f"SLT {r}, {rr}, {lr}")
                self.em(f"XORI {r}, {r}, 1")
            elif op == ">=":
                self.em(f"SLT {r}, {lr}, {rr}")
                self.em(f"XORI {r}, {r}, 1")
            elif op in ("==", "!="):
                self.em(f"SUB {r}, {lr}, {rr}")
                t1, t2 = self.ar(), self.ar()
                self.em(f"SLT {t1}, zero, {r}")
                self.em(f"SLT {t2}, {r}, zero")
                self.em(f"OR {r}, {t1}, {t2}")
                if op == "==":
                    self.em(f"XORI {r}, {r}, 1")
            return r
        if v == 0:
            return "zero" if target_reg is None else (self.em(f"MV {target_reg}, zero"), target_reg)[1]
        if isinstance(v, int):
            return self.li(v, target_reg)
        return v

    def _eb(self, op, left, right, target_reg=None):
        if (
            isinstance(left, tuple)
            and len(left) == 3
            and left[0] == "arr"
            and isinstance(right, tuple)
            and len(right) == 3
            and right[0] == "arr"
            and op in VBM
        ):
            lo, ln = left[1], left[2]
            ro, _rn = right[1], right[2]
            ro2 = self.do
            orig = ro2
            self.do += ln * 4
            nf = ln // 4
            tl = ln % 4
            vl = self.av()
            vr = self.av()
            vd = self.av()
            rlo = self.ar()
            rro = self.ar()
            rro2 = self.ar()
            self.em(f"ADDI {rlo}, gp, {lo}")
            self.em(f"ADDI {rro}, gp, {ro}")
            self.em(f"ADDI {rro2}, gp, {ro2}")
            if nf > 0:
                ci = self.ar()
                lh = self.ml("vh")
                self.em(f"ADDI {ci}, zero, {nf}")
                self.em(f"{lh}:")
                self.em(f"VLD {vl}, [{rlo}+0]")
                self.em(f"VLD {vr}, [{rro}+0]")
                self.em(f"{VBM[op]} {vd}, {vl}, {vr}")
                self.em(f"VST {vd}, [{rro2}+0]")
                self.em(f"ADDI {rlo}, {rlo}, 16")
                self.em(f"ADDI {rro}, {rro}, 16")
                self.em(f"ADDI {rro2}, {rro2}, 16")
                self.em(f"ADDI {ci}, {ci}, -1")
                self.em(f"BNE {ci}, zero, {lh}")
            if tl > 0:
                sl = self.ar()
                sr = self.ar()
                sd = self.ar()
                for _ in range(tl):
                    self.em(f"LW {sl}, {rlo}, 0")
                    self.em(f"LW {sr}, {rro}, 0")
                    self.em(f"{BM[op]} {sd}, {sl}, {sr}")
                    self.em(f"SW {sd}, {rro2}, 0")
                    self.em(f"ADDI {rlo}, {rlo}, 4")
                    self.em(f"ADDI {rro}, {rro}, 4")
                    self.em(f"ADDI {rro2}, {rro2}, 4")
            return ("arr", orig, ln)
        if isinstance(left, int) and isinstance(right, int):
            ops = {
                "+": left + right,
                "-": left - right,
                "*": left * right,
                "/": left // right if right else 0,
                "%": left % right if right else 0,
                "&": left & right,
                "|": left | right,
                "^": left ^ right,
                "<<": left << right,
                ">>": left >> right,
                "<": 1 if left < right else 0,
                ">": 1 if left > right else 0,
                "<=": 1 if left <= right else 0,
                ">=": 1 if left >= right else 0,
                "==": 1 if left == right else 0,
                "!=": 1 if left != right else 0,
            }
            return ops.get(op, 0)
        if op in ("<", ">", "<=", ">=", "==", "!="):
            return (op, self.er(left), self.er(right))
        if isinstance(right, int) and self.I12[0] <= right <= self.I12[1]:
            lr = self.er(left)
            res = target_reg or self.ar()
            if op == "+":
                self.em(f"ADDI {res}, {lr}, {right}")
                return res
            if op == "-" and self.I12[0] <= -right <= self.I12[1]:
                self.em(f"ADDI {res}, {lr}, {-right}")
                return res
            if op in ("&", "|", "^", "<<", ">>"):
                self.em(f"{BM[op]}I {res}, {lr}, {right}")
                return res
        lr, rr = self.er(left), self.er(right)
        res = target_reg or self.ar()
        if op == "||":
            self.em(f"OR {res}, {lr}, {rr}")
            return res
        if op == "&&":
            self.em(f"AND {res}, {lr}, {rr}")
            return res
        if op in BM:
            self.em(f"{BM[op]} {res}, {lr}, {rr}")
        return res

    def _fin(self):
        its = []
        for n, loc in self.vars.items():
            if isinstance(loc, int):
                its.append((loc, f"    .word 0  ; {n}"))
            elif isinstance(loc, tuple) and loc[0] == "arr":
                off, sz = loc[1], loc[2]
                for i in range(sz):
                    its.append((off + i * 4, f"    .word {self.dv.get(off + i * 4, 0)}  ; {n}[{i}]"))
        esc = {"\n": "\\n", "\t": "\\t", "\r": "\\r", '"': '\\"', "\\": "\\\\"}
        for o, c in self.strs:
            chs = [f'    .word {len(c)}  ; len "{"".join(esc.get(ch, ch) for ch in c)}"']
            for i, ch in enumerate(c):
                chs.append(f"    .word {ord(ch)}  ; '{esc.get(ch, ch)}'")
            its.append((o, "\n".join(chs)))
        its.sort(key=lambda x: x[0])
        lns = ["    .data 0", "data_start:"]
        if its:
            cur = 0
            for ao, block in its:
                if ao > cur:
                    lns.append(f"    .org {ao}")
                    cur = ao
                for line in block.split("\n"):
                    lns.append(line)
                    cur += 4
        else:
            lns.append("    .word 0  ; dummy")
        lns.append("    .text 0")
        lns.append("    J main")
        for ln in self.asm:
            lns.append(ln)
            if ln.strip() == "main:":
                lns.append("    ADDI gp, zero, data_start")
        return "\n".join(lns)

    def run(self, s):
        return self.gen(self.parse(s))

    def dump_ast(self, s):
        self.parse(s)
        return self.ast if self.ast else {}

    def get_ast(self):
        return self.ast
