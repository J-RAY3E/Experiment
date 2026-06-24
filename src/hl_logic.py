from __future__ import annotations

import re

from src.isa import IMM20_MASK, IN_PORT, OUT_PORT

P = [{"||"}, {"&&"}, {"|"}, {"^"}, {"&"}, {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"}, {"+", "-"}, {"*", "/", "%"}]
BM = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "REM", "&": "AND", "|": "OR", "^": "XOR", "<<": "SLL", ">>": "SRL"}
KW = {"function", "let", "if", "else", "while", "halt", "true", "false", "return"}
BI = {"print", "print_str", "print_num", "read", "readln", "len"}
TR = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
_CMP = {"==": "BNE", "!=": "BEQ", "<": "BGE", ">=": "BLT", ">": "BLE", "<=": "BGT"}


class HL:
    def __init__(self):
        self.vars = {}
        self.arrays = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.sc = 0
        self.dl = []
        self.strs = []
        self.dv = {}
        self.toks = []
        self.pos = 0
        self.ast = None

    def tk(self, t):
        self.toks = []
        for m in re.finditer(
            r'//.*|"[^"\\]*(?:\\.[^"\\]*)*"|0[xX][0-9a-fA-F]+|\d+|'
            r"'[^'\\]*(?:\\.[^'\\]*)*'|"
            r"[a-zA-Z_]\w*|&&|\|\||<<|>>|<=|>=|==|!=|[-+*/%&|^~<>=!]=?|[{}();,\[\]]",
            t,
        ):
            g = m.group()
            if g.startswith("//"):
                continue
            if g.startswith("0x") or g.startswith("0X"):
                self.toks.append(("H", int(g, 16)))
            elif g.isdigit():
                self.toks.append(("N", int(g)))
            elif g.startswith('"'):
                g = (
                    g[1:-1]
                    .replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace("\\r", "\r")
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )
                self.toks.append(("STR", g))
            elif g.startswith("'"):
                c = g[1:-1]
                v = {"n": 10, "t": 9, "r": 13, "0": 0}.get(c[1], ord(c[1])) if len(c) > 1 and c[0] == "\\" else ord(c)
                self.toks.append(("C", v))
            elif g[0].isalpha() or g[0] == "_":
                self.toks.append(("K" if g in KW else "B" if g in BI else "I", g))
            elif g in "{}();,[]":
                self.toks.append(("S", g))
            else:
                self.toks.append(("O", g))
        self.toks.append(("", ""))
        self.pos = 0

    def pk(self):
        return self.toks[self.pos] if self.pos < len(self.toks) else ("", "")

    def ad(self):
        t = self.toks[self.pos]
        self.pos += 1
        return t

    def ex(self, *v):
        t = self.pk()
        if t[1] in v or t[0] in v:
            return self.ad()
        raise SyntaxError(f"expected {v}, got {t}")

    def ag(self):
        self.ex("(")
        a = []
        while self.pk()[1] != ")":
            a.append(self.px())
            if self.pk()[1] == ",":
                self.ad()
        self.ex(")")
        return a

    def dp(self):
        self.ex("(")
        p = []
        while self.pk()[1] != ")":
            t = self.pk()
            if t[0] != "I":
                raise SyntaxError(f"expected id, got {t}")
            p.append(self.ad()[1])
            if self.pk()[1] == ",":
                self.ad()
        self.ex(")")
        return p

    def parse(self, src):
        self.tk(src)
        fs = []
        while self.pk()[0] != "":
            if self.pk() == ("K", "function"):
                self.ad()
                n = self.ad()[1]
                params = self.dp()
                self.ex("{")
                b = self._ss("}")
                self.ex("}")
                fd = {"function": n, "body": b}
                if params:
                    fd["params"] = params
                fs.append(fd)
            else:
                self.ad()
        self.ast = {"program": fs}
        return self.ast

    def _ss(self, e):
        r = []
        while self.pk()[1] != e:
            st = self._st()
            if st is not None:
                r.append(st)
        return r

    def _st(self):
        t = self.pk()
        if t == ("K", "let"):
            self.ad()
            n = self.ex("I")[1]
            sz = None
            iv = None
            if self.pk()[1] == "[":
                self.ad()
                sz = self.px()
                self.ex("]")
            if self.pk()[1] == "=":
                self.ad()
                iv = self.px()
            self.ex(";")
            d = {"let": n}
            if iv is not None:
                d["init"] = iv
            if sz is not None:
                d["array_size"] = sz
            return d
        if t == ("K", "if"):
            return self._iw("if")
        if t == ("K", "while"):
            return self._iw("while")
        if t == ("K", "halt"):
            self.ad()
            self.ex(";")
            return {"halt": True}
        if t == ("K", "return"):
            self.ad()
            v = self.px() if self.pk()[1] != ";" else None
            self.ex(";")
            return {"return": v}
        if t[0] == "S" and t[1] == "{":
            self.ad()
            b = self._ss("}")
            self.ex("}")
            return {"block": b}
        if t[0] == "B":
            n = self.ad()[1]
            a = self.ag()
            self.ex(";")
            return {"expr_stmt": {"call": n, "args": a}}
        if t[0] == "S" and t[1] == ";":
            self.ad()
            return None
        return self._as()

    def _iw(self, k):
        self.ad()
        self.ex("(")
        c = self.px()
        self.ex(")")
        b = self._st()
        bl = [b] if "block" not in b else b["block"]
        if k == "while":
            return {"while": c, "body": bl}
        el = None
        if self.pk() == ("K", "else"):
            self.ad()
            eb = self._st()
            el = [eb] if "block" not in eb else eb["block"]
        return {"if": c, "then": bl, "else": el} if el else {"if": c, "then": bl}

    def _as(self):
        n = self.ad()[1]
        if self.pk()[1] == "(":
            a = self.ag()
            self.ex(";")
            return {"expr_stmt": {"call": n, "args": a}}
        tg = {"var": n}
        while self.pk()[1] == "[":
            self.ad()
            tg = {"index": tg, "at": self.px()}
            self.ex("]")
        self.ex("=")
        v = self.px()
        self.ex(";")
        if "var" in tg:
            return {"assign": n, "value": v}
        return {"index_assign": tg, "value": v}

    def px(self, mp=0):
        r = self._pr()
        while True:
            t = self.pk()
            if t[0] != "O":
                break
            p = next((i for i, lv in enumerate(P) if t[1] in lv), -1)
            if p < 0 or p < mp:
                break
            self.ad()
            r = {"binop": t[1], "left": r, "right": self.px(p + 1)}
        return r

    def _pr(self):
        t = self.ad()
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
            if self.pk()[1] != "}":
                e.append(self.px())
            while self.pk()[1] == ",":
                self.ad()
                e.append(self.px())
            self.ex("}")
            return {"array": e}
        if t[0] in ("I", "B"):
            if self.pk()[1] == "(":
                f = t[1]
                a = self.ag()
                return {"call": f, "args": a}
            if t[0] == "I":
                n2 = {"var": t[1]}
                while self.pk()[1] == "[":
                    self.ad()
                    n2 = {"index": n2, "at": self.px()}
                    self.ex("]")
                return n2
            raise SyntaxError(f"unexpected builtin {t}")
        if t[0] == "S" and t[1] == "(":
            e = self.px()
            self.ex(")")
            return e
        if t[0] == "O" and t[1] in ("-", "~", "!"):
            return {"unary": t[1], "operand": self.px(len(P))}
        raise SyntaxError(f"unexpected token {t}")

    def gen(self, a):
        self.vars = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.sc = 0
        self.dl = []
        self.strs = []
        self.dv = {}
        for f in a["program"]:
            self._gf(f)
        return self._fn()

    def ar(self):
        r = TR[self.nr % 7]
        self.nr += 1
        return r

    def ml(self, p="L"):
        self.lc += 1
        return f"{p}_{self.lc}"

    def em(self, ln=""):
        self.asm.append(("    " + ln) if ln else "")

    def _li(self, v, r=None):
        rr = r or self.ar()
        if -2048 <= v <= 2047:
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

    def _vv(self, n, ld=True):
        loc = self.vars.setdefault(n, self.do)
        if loc == self.do:
            self.do += 4
        if ld and -2048 <= loc <= 2047:
            r = self.ar()
            self.em(f"LW {r}, gp, {loc}")
            return r
        if not ld and -1024 <= loc <= 1023:
            return None
        t = self.ar()
        self._li(loc, t)
        self.em(f"ADD {t}, gp, {t}")
        if ld:
            r = self.ar()
            self.em(f"LW {r}, {t}, 0")
            return r
        return t

    def sv(self, n, r):
        loc = self.vars.setdefault(n, self.do)
        if loc == self.do:
            self.do += 4
        if -1024 <= loc <= 1023:
            self.em(f"SW {r}, gp, {loc}")
        else:
            t = self.ar()
            self._li(loc, t)
            self.em(f"ADD {t}, gp, {t}")
            self.em(f"SW {r}, {t}, 0")

    def _gf(self, f):
        im = f["function"] == "main"
        ba = []
        sv = self.asm
        self.asm = ba
        self.em(f"{f['function']}:")
        for i, p in enumerate(f.get("params", [])[:8]):
            self.vars.setdefault(p, self.do)
            if self.vars[p] == self.do:
                self.do += 4
        for i, p in enumerate(f.get("params", [])[:8]):
            self.sv(p, f"a{i}")
        for st in f["body"]:
            self._gs(st)
        if not im:
            ba[1:1] = ["    ADDI sp, sp, -4", "    SW ra, sp, 0"]
            ba += ["    LW ra, sp, 0", "    ADDI sp, sp, 4", "    JR ra"]
        elif not ba or ba[-1].strip() != "HALT":
            ba.append("    HALT")
        self.asm = sv
        self.asm += ba
        self.dl.append(f["function"])

    def _gs(self, x):
        if "let" in x:
            self._gl(x)
        elif "assign" in x:
            n = x["assign"]
            if n in self.arrays:
                r = self._ge(x["value"])
                if isinstance(r, tuple) and r and r[0] == "arr":
                    self.arrays[n] = (r[1], r[2])
                    self.vars[n] = r
                return
            self.vars.setdefault(n, self.do)
            if self.vars[n] == self.do:
                self.do += 4
            self.sv(n, self._er(self._ge(x["value"])))
        elif "index_assign" in x:
            tg = x["index_assign"]
            if "index" not in tg:
                return
            bl = self._la(tg["index"])
            if bl is None:
                return
            o, _n = bl
            vr = self._er(self._ge(x["value"]))
            ir = self._er(self._ge(tg["at"]))
            ar = self.ar()
            self.em(f"SLLI {ar}, {ir}, 2")
            self.em(f"ADDI {ar}, {ar}, {o}")
            self.em(f"ADD {ar}, {ar}, gp")
            self.em(f"SW {vr}, {ar}, 0")
        elif "if" in x:
            self._gc("if", x["if"], x["then"], x.get("else"))
        elif "while" in x:
            self._gc("while", x["while"], x["body"], None)
        elif "return" in x:
            if x["return"] is not None:
                self.em(f"MV a0, {self._er(self._ge(x['return']))}")
        elif "expr_stmt" in x:
            self._ges(x)
        elif "block" in x:
            for st in x["body"]:
                self._gs(st)
        elif "halt" in x:
            self.em("HALT")

    def _gl(self, x):
        n = x["let"]
        iv = x.get("init")
        if x.get("array_size") is not None or (isinstance(iv, dict) and "array" in iv):
            sz = (
                x["array_size"]["int"]
                if x.get("array_size") and isinstance(x["array_size"], dict) and "int" in x["array_size"]
                else (len(iv["array"]) if isinstance(iv, dict) and "array" in iv else 4)
            )
            o = self.do
            self.do += sz * 4
            if isinstance(iv, dict) and "array" in iv:
                for i, el in enumerate(iv["array"]):
                    if i >= sz:
                        break
                    v = self._ge(el)
                    if isinstance(v, int):
                        self.dv[o + i * 4] = v
                    else:
                        vr = self._er(v)
                        ar = self.ar()
                        self.em(f"ADDI {ar}, gp, {o + i * 4}")
                        self.em(f"SW {vr}, {ar}, 0")
            elif iv is not None:
                r = self._ge(iv)
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
        self.vars.setdefault(n, self.do)
        if self.vars[n] == self.do:
            self.do += 4
        if iv is not None:
            r = self._ge(iv)
            if isinstance(r, tuple) and r and r[0] == "arr":
                off, sz = r[1], r[2]
                self.arrays[n] = (off, sz)
                self.vars[n] = r
            else:
                self.sv(n, self._er(r))

    def _la(self, n):
        if isinstance(n, dict) and "var" in n and n["var"] in self.arrays:
            return self.arrays[n["var"]]
        if isinstance(n, dict) and "index" in n:
            return self._la(n["index"])
        return None

    def _ges(self, x):
        x = x["expr_stmt"]
        if "call" not in x:
            return
        cn = x["call"]
        args = x.get("args", [])
        if cn == "print_str" and args:
            a0 = args[0]
            if "string" in a0 or "var" in a0:
                sv = a0["string"] if "string" in a0 else a0["var"]
                so = self.do
                self.strs.append((so, sv))
                self.do += 4 + len(sv) * 4
                ba, le, i2, ch = self.ar(), self.ar(), self.ar(), self.ar()
                po = self._li(OUT_PORT)
                ls, le2 = self.ml("ps"), self.ml("pe")
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
        if cn == "print_num" and args:
            vo = self._er(self._ge(args[0]))
            val = self.ar()
            self.em(f"MV {val}, {vo}")
            div, tmp, ten = self.ar(), self.ar(), self.ar()
            po = self._li(OUT_PORT)
            ls, l2, l3 = self.ml("pnl"), self.ml("pn2"), self.ml("pn3")
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
        if cn == "print":
            po = self._li(OUT_PORT)
            for a in args:
                self.em(f"SW {self._er(self._ge(a))}, {po}, 0")
            return
        if cn == "readln":
            if not args:
                self.em(f"LW {self.ar()}, {self._li(IN_PORT)}, 0")
                return
            a = args[0]
            o = self._ge(a)
            addr, i2, ch, tmp = self.ar(), self.ar(), self.ar(), self.ar()
            inp = self._li(IN_PORT)
            if isinstance(o, tuple) and o[0] == "arr":
                self.em(f"ADDI {addr}, gp, {o[1]}")
            elif isinstance(o, int):
                self.em(f"ADDI {addr}, gp, {o}")
            else:
                self.em(f"ADD {addr}, gp, {self._er(o)}")
            self.em(f"ADDI {i2}, zero, 0")
            l1, l2 = self.ml("rl"), self.ml("re")
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
        for i, a in enumerate(args):
            if i < 8:
                self.em(f"MV a{i}, {self._er(self._ge(a))}")
        self.em(f"JAL ra, {cn}")

    def _gc(self, k, cond, body, eb):
        lc = self.ml("wc") if k == "while" else None
        le = self.ml("el") if k == "if" else None
        le2 = self.ml("en")
        if k == "while":
            self.em(f"{lc}:")
        cv = self._ge(cond)
        if isinstance(cv, tuple) and len(cv) == 3 and cv[0] in _CMP:
            op, rs1, rs2 = cv
            self.em(f"{_CMP[op]} {rs1}, {rs2}, {le if k == 'if' else le2}")
        else:
            self.em(f"BEQ {self._er(cv)}, zero, {le if k == 'if' else le2}")
        for st in body:
            self._gs(st)
        if k == "if":
            if eb:
                self.em(f"J {le2}")
                self.em(f"{le}:")
                for st in eb:
                    self._gs(st)
            else:
                self.em(f"{le}:")
            self.em(f"{le2}:")
        else:
            self.em(f"J {lc}")
            self.em(f"{le2}:")

    def _ge(self, e, tr=None):
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
            ir = self._er(self._ge(e["at"]))
            ar = self.ar()
            self.em(f"SLLI {ar}, {ir}, 2")
            self.em(f"ADDI {ar}, {ar}, {o}")
            self.em(f"ADD {ar}, {ar}, gp")
            r = tr or self.ar()
            self.em(f"LW {r}, {ar}, 0")
            return r
        if "var" in e:
            n = e["var"]
            if n in self.arrays:
                o, n2 = self.arrays[n]
                return ("arr", o, n2)
            v = self._vv(n, True)
            if tr and tr != v:
                self.em(f"MV {tr}, {v}")
            return tr if tr else v
        if "unary" in e:
            ev = self._ge(e["operand"])
            r = tr or self.ar()
            if e["unary"] == "-":
                self.em(f"SUB {r}, zero, {self._er(ev)}")
            else:
                self.em(f"XORI {r}, {self._er(ev)}, 1")
            return r
        if "binop" in e:
            op = e["binop"]
            if op in ("&&", "||"):
                sr = f"s{self.sc}"
                self.sc += 1
                r = tr or self.ar()
                lv = self._ge(e["left"])
                self.em(f"MV {r}, {self._er(lv)}")
                self.em(f"MV {sr}, {r}")
                le = self.ml("sc")
                self.em(f"{'BEQ' if op == '&&' else 'BNE'} {sr}, zero, {le}")
                rv = self._ge(e["right"])
                self.sc -= 1
                self.em(f"{'AND' if op == '&&' else 'OR'} {sr}, {sr}, {self._er(rv)}")
                self.em(f"{le}:")
                if tr and tr != sr:
                    self.em(f"MV {tr}, {sr}")
                    return tr
                return sr
            return self._eb(op, self._ge(e["left"]), self._ge(e["right"]), tr)
        if "call" in e and e["call"] == "read":
            r = tr or self.ar()
            self.em(f"LW {r}, {self._li(IN_PORT)}, 0")
            return r
        if "call" in e and e["call"] == "len":
            if e["args"] and "var" in e["args"][0] and e["args"][0]["var"] in self.arrays:
                return self.arrays[e["args"][0]["var"]][1]
            return 0
        if "call" in e:
            for i, a in enumerate(e["args"]):
                if i < 8:
                    self.em(f"MV a{i}, {self._er(self._ge(a))}")
            self.em(f"JAL ra, {e['call']}")
            r = tr or self.ar()
            self.em(f"MV {r}, a0")
            return r
        return 0

    def _er(self, v, tr=None):
        if isinstance(v, tuple):
            r = tr or self.ar()
            op, lr, rr = v
            _ec = {
                "<": (f"SLT {r}, {lr}, {rr}",),
                ">": (f"SLT {r}, {rr}, {lr}",),
                "<=": (f"SLT {r}, {rr}, {lr}", f"XORI {r}, {r}, 1"),
                ">=": (f"SLT {r}, {lr}, {rr}", f"XORI {r}, {r}, 1"),
                "==": (
                    f"SUB {r}, {lr}, {rr}",
                    f"SLT t1, zero, {r}",
                    f"SLT t2, {r}, zero",
                    f"OR {r}, t1, t2",
                    f"XORI {r}, {r}, 1",
                ),
                "!=": (f"SUB {r}, {lr}, {rr}", f"SLT t1, zero, {r}", f"SLT t2, {r}, zero", f"OR {r}, t1, t2"),
            }
            for inst in _ec.get(op, ()):
                self.em(inst)
            return r
        if v == 0:
            return "zero" if tr is None else (self.em(f"MV {tr}, zero"), tr)[1]
        if isinstance(v, int):
            return self._li(v, tr)
        return v

    def _eb(self, op, left, right, tr=None):
        if isinstance(left, int) and isinstance(right, int):
            _bo = {
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
            return _bo.get(op, 0)
        if op in _CMP:
            return (op, self._er(left), self._er(right))
        if isinstance(right, int) and -2048 <= right <= 2047:
            lr = self._er(left)
            res = tr or self.ar()
            if op == "+":
                self.em(f"ADDI {res}, {lr}, {right}")
                return res
            if op == "-" and -2048 <= -right <= 2047:
                self.em(f"ADDI {res}, {lr}, {-right}")
                return res
            if op in ("&", "|", "^", "<<", ">>"):
                self.em(f"{BM[op]}I {res}, {lr}, {right}")
                return res
        lr, rr = self._er(left), self._er(right)
        res = tr or self.ar()
        if op in ("||", "&&"):
            self.em(f"{'OR' if op == '||' else 'AND'} {res}, {lr}, {rr}")
            return res
        if op in BM:
            self.em(f"{BM[op]} {res}, {lr}, {rr}")
        return res

    def _fn(self):
        its = []
        for n, loc in self.vars.items():
            if isinstance(loc, int):
                its.append((loc, f"    .word 0  ; {n}", 4))
            elif isinstance(loc, tuple) and loc[0] == "arr":
                off, sz = loc[1], loc[2]
                for i in range(sz):
                    its.append((off + i * 4, f"    .word {self.dv.get(off + i * 4, 0)}  ; {n}[{i}]", 4))
        esc = {"\n": "\\n", "\t": "\\t", "\r": "\\r", '"': '\\"', "\\": "\\\\"}
        for o, c in self.strs:
            ec = "".join(esc.get(ch, ch) for ch in c)
            its.append((o, f'    .string "{ec}"', 4 + len(c) * 4))
        its.sort(key=lambda x: x[0])
        ln = ["    .data 0", "    data_start:"]
        if its:
            cur = 0
            for ao, blk, sz in its:
                if ao > cur:
                    ln.append(f"    .org {ao}")
                    cur = ao
                for line in blk.split("\n"):
                    ln.append(line)
                cur += sz
        else:
            ln.append("    .word 0  ; dummy")
        ln.append("    .text 0")
        ln.append("    J main")
        for line in self.asm:
            ln.append(line)
            if line.strip() == "main:":
                ln.append("    ADDI gp, zero, data_start")
        return "\n".join(ln)

    def dump_ast(self, src):
        self.parse(src)
        return self.ast if self.ast else {}

    def get_ast(self):
        return self.ast

    def run(self, src):
        return self.gen(self.parse(src))
