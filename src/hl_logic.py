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
    def __init__(s):
        s.vars = {}
        s.arrays = {}
        s.do = 0
        s.lc = 0
        s.asm = []
        s.nr = 0
        s.sc = 0
        s.dl = []
        s.strs = []
        s.dv = {}
        s.toks = []
        s.pos = 0
        s.ast = None

    def tk(s, t):
        s.toks = []
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
                s.toks.append(("H", int(g, 16)))
            elif g.isdigit():
                s.toks.append(("N", int(g)))
            elif g.startswith('"'):
                g = (
                    g[1:-1]
                    .replace("\\n", "\n")
                    .replace("\\t", "\t")
                    .replace("\\r", "\r")
                    .replace('\\"', '"')
                    .replace("\\\\", "\\")
                )
                s.toks.append(("STR", g))
            elif g.startswith("'"):
                c = g[1:-1]
                v = {"n": 10, "t": 9, "r": 13, "0": 0}.get(c[1], ord(c[1])) if len(c) > 1 and c[0] == "\\" else ord(c)
                s.toks.append(("C", v))
            elif g[0].isalpha() or g[0] == "_":
                s.toks.append(("K" if g in KW else "B" if g in BI else "I", g))
            elif g in "{}();,[]":
                s.toks.append(("S", g))
            else:
                s.toks.append(("O", g))
        s.toks.append(("", ""))
        s.pos = 0

    def pk(s):
        return s.toks[s.pos] if s.pos < len(s.toks) else ("", "")

    def ad(s):
        t = s.toks[s.pos]
        s.pos += 1
        return t

    def ex(s, *v):
        t = s.pk()
        if t[1] in v or t[0] in v:
            return s.ad()
        raise SyntaxError(f"expected {v}, got {t}")

    def ag(s):
        s.ex("(")
        a = []
        while s.pk()[1] != ")":
            a.append(s.px())
            if s.pk()[1] == ",":
                s.ad()
        s.ex(")")
        return a

    def dp(s):
        s.ex("(")
        p = []
        while s.pk()[1] != ")":
            t = s.pk()
            if t[0] != "I":
                raise SyntaxError(f"expected id, got {t}")
            p.append(s.ad()[1])
            if s.pk()[1] == ",":
                s.ad()
        s.ex(")")
        return p

    def parse(s, src):
        s.tk(src)
        fs = []
        while s.pk()[0] != "":
            if s.pk() == ("K", "function"):
                s.ad()
                n = s.ad()[1]
                params = s.dp()
                s.ex("{")
                b = s._ss("}")
                s.ex("}")
                fd = {"function": n, "body": b}
                if params:
                    fd["params"] = params
                fs.append(fd)
            else:
                s.ad()
        s.ast = {"program": fs}
        return s.ast

    def _ss(s, e):
        r = []
        while s.pk()[1] != e:
            st = s._st()
            if st is not None:
                r.append(st)
        return r

    def _st(s):
        t = s.pk()
        if t == ("K", "let"):
            s.ad()
            n = s.ex("I")[1]
            sz = None
            iv = None
            if s.pk()[1] == "[":
                s.ad()
                sz = s.px()
                s.ex("]")
            if s.pk()[1] == "=":
                s.ad()
                iv = s.px()
            s.ex(";")
            d = {"let": n}
            if iv is not None:
                d["init"] = iv
            if sz is not None:
                d["array_size"] = sz
            return d
        if t == ("K", "if"):
            return s._iw("if")
        if t == ("K", "while"):
            return s._iw("while")
        if t == ("K", "halt"):
            s.ad()
            s.ex(";")
            return {"halt": True}
        if t == ("K", "return"):
            s.ad()
            v = s.px() if s.pk()[1] != ";" else None
            s.ex(";")
            return {"return": v}
        if t[0] == "S" and t[1] == "{":
            s.ad()
            b = s._ss("}")
            s.ex("}")
            return {"block": b}
        if t[0] == "B":
            n = s.ad()[1]
            a = s.ag()
            s.ex(";")
            return {"expr_stmt": {"call": n, "args": a}}
        if t[0] == "S" and t[1] == ";":
            s.ad()
            return None
        return s._as()

    def _iw(s, k):
        s.ad()
        s.ex("(")
        c = s.px()
        s.ex(")")
        b = s._st()
        bl = [b] if "block" not in b else b["block"]
        if k == "while":
            return {"while": c, "body": bl}
        el = None
        if s.pk() == ("K", "else"):
            s.ad()
            eb = s._st()
            el = [eb] if "block" not in eb else eb["block"]
        return {"if": c, "then": bl, "else": el} if el else {"if": c, "then": bl}

    def _as(s):
        n = s.ad()[1]
        if s.pk()[1] == "(":
            a = s.ag()
            s.ex(";")
            return {"expr_stmt": {"call": n, "args": a}}
        tg = {"var": n}
        while s.pk()[1] == "[":
            s.ad()
            tg = {"index": tg, "at": s.px()}
            s.ex("]")
        s.ex("=")
        v = s.px()
        s.ex(";")
        if "var" in tg:
            return {"assign": n, "value": v}
        return {"index_assign": tg, "value": v}

    def px(s, mp=0):
        r = s._pr()
        while True:
            t = s.pk()
            if t[0] != "O":
                break
            p = next((i for i, lv in enumerate(P) if t[1] in lv), -1)
            if p < 0 or p < mp:
                break
            s.ad()
            r = {"binop": t[1], "left": r, "right": s.px(p + 1)}
        return r

    def _pr(s):
        t = s.ad()
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
            if s.pk()[1] != "}":
                e.append(s.px())
            while s.pk()[1] == ",":
                s.ad()
                e.append(s.px())
            s.ex("}")
            return {"array": e}
        if t[0] in ("I", "B"):
            if s.pk()[1] == "(":
                f = t[1]
                a = s.ag()
                return {"call": f, "args": a}
            if t[0] == "I":
                n2 = {"var": t[1]}
                while s.pk()[1] == "[":
                    s.ad()
                    n2 = {"index": n2, "at": s.px()}
                    s.ex("]")
                return n2
            raise SyntaxError(f"unexpected builtin {t}")
        if t[0] == "S" and t[1] == "(":
            e = s.px()
            s.ex(")")
            return e
        if t[0] == "O" and t[1] in ("-", "~", "!"):
            return {"unary": t[1], "operand": s.px(len(P))}
        raise SyntaxError(f"unexpected token {t}")

    def gen(s, a):
        s.vars = {}
        s.do = 0
        s.lc = 0
        s.asm = []
        s.nr = 0
        s.sc = 0
        s.dl = []
        s.strs = []
        s.dv = {}
        for f in a["program"]:
            s._gf(f)
        return s._fn()

    def ar(s):
        r = TR[s.nr % 7]
        s.nr += 1
        return r

    def ml(s, p="L"):
        s.lc += 1
        return f"{p}_{s.lc}"

    def em(s, ln=""):
        s.asm.append(("    " + ln) if ln else "")

    def _li(s, v, r=None):
        rr = r or s.ar()
        if -2048 <= v <= 2047:
            s.em(f"ADDI {rr}, zero, {v}")
        else:
            lo = v & 0xFFF
            if lo >= 0x800:
                lo -= 0x1000
            hi = (v - lo) >> 12
            s.em(f"LUI {rr}, {hi & IMM20_MASK}")
            if lo:
                s.em(f"ADDI {rr}, {rr}, {lo}")
        return rr

    def _vv(s, n, ld=True):
        loc = s.vars.setdefault(n, s.do)
        if loc == s.do:
            s.do += 4
        if ld and -2048 <= loc <= 2047:
            r = s.ar()
            s.em(f"LW {r}, gp, {loc}")
            return r
        if not ld and -1024 <= loc <= 1023:
            return None
        t = s.ar()
        s._li(loc, t)
        s.em(f"ADD {t}, gp, {t}")
        if ld:
            r = s.ar()
            s.em(f"LW {r}, {t}, 0")
            return r
        return t

    def sv(s, n, r):
        loc = s.vars.setdefault(n, s.do)
        if loc == s.do:
            s.do += 4
        if -1024 <= loc <= 1023:
            s.em(f"SW {r}, gp, {loc}")
        else:
            t = s.ar()
            s._li(loc, t)
            s.em(f"ADD {t}, gp, {t}")
            s.em(f"SW {r}, {t}, 0")

    def _gf(s, f):
        im = f["function"] == "main"
        ba = []
        sv = s.asm
        s.asm = ba
        s.em(f"{f['function']}:")
        for i, p in enumerate(f.get("params", [])[:8]):
            s.vars.setdefault(p, s.do)
            if s.vars[p] == s.do:
                s.do += 4
        for i, p in enumerate(f.get("params", [])[:8]):
            s.sv(p, f"a{i}")
        for st in f["body"]:
            s._gs(st)
        if not im:
            ba[1:1] = ["    ADDI sp, sp, -4", "    SW ra, sp, 0"]
            ba += ["    LW ra, sp, 0", "    ADDI sp, sp, 4", "    JR ra"]
        elif not ba or ba[-1].strip() != "HALT":
            ba.append("    HALT")
        s.asm = sv
        s.asm += ba
        s.dl.append(f["function"])

    def _gs(s, x):
        if "let" in x:
            s._gl(x)
        elif "assign" in x:
            n = x["assign"]
            if n in s.arrays:
                r = s._ge(x["value"])
                if isinstance(r, tuple) and r and r[0] == "arr":
                    s.arrays[n] = (r[1], r[2])
                    s.vars[n] = r
                return
            s.vars.setdefault(n, s.do)
            if s.vars[n] == s.do:
                s.do += 4
            s.sv(n, s._er(s._ge(x["value"])))
        elif "index_assign" in x:
            tg = x["index_assign"]
            if "index" not in tg:
                return
            bl = s._la(tg["index"])
            if bl is None:
                return
            o, _n = bl
            vr = s._er(s._ge(x["value"]))
            ir = s._er(s._ge(tg["at"]))
            ar = s.ar()
            s.em(f"SLLI {ar}, {ir}, 2")
            s.em(f"ADDI {ar}, {ar}, {o}")
            s.em(f"ADD {ar}, {ar}, gp")
            s.em(f"SW {vr}, {ar}, 0")
        elif "if" in x:
            s._gc("if", x["if"], x["then"], x.get("else"))
        elif "while" in x:
            s._gc("while", x["while"], x["body"], None)
        elif "return" in x:
            if x["return"] is not None:
                s.em(f"MV a0, {s._er(s._ge(x['return']))}")
        elif "expr_stmt" in x:
            s._ges(x)
        elif "block" in x:
            for st in x["body"]:
                s._gs(st)
        elif "halt" in x:
            s.em("HALT")

    def _gl(s, x):
        n = x["let"]
        iv = x.get("init")
        if x.get("array_size") is not None or (isinstance(iv, dict) and "array" in iv):
            sz = (
                x["array_size"]["int"]
                if x.get("array_size") and isinstance(x["array_size"], dict) and "int" in x["array_size"]
                else (len(iv["array"]) if isinstance(iv, dict) and "array" in iv else 4)
            )
            o = s.do
            s.do += sz * 4
            if isinstance(iv, dict) and "array" in iv:
                for i, el in enumerate(iv["array"]):
                    if i >= sz:
                        break
                    v = s._ge(el)
                    if isinstance(v, int):
                        s.dv[o + i * 4] = v
                    else:
                        vr = s._er(v)
                        ar = s.ar()
                        s.em(f"ADDI {ar}, gp, {o + i * 4}")
                        s.em(f"SW {vr}, {ar}, 0")
            elif iv is not None:
                r = s._ge(iv)
                if isinstance(r, tuple) and r and r[0] == "arr":
                    ro, rn = r[1], r[2]
                    for i in range(min(rn, sz)):
                        ar = s.ar()
                        s.em(f"ADDI {ar}, gp, {ro + i * 4}")
                        s.em(f"LW {ar}, {ar}, 0")
                        s.em(f"SW {ar}, gp, {o + i * 4}")
            s.arrays[n] = (o, sz)
            s.vars[n] = ("arr", o, sz)
            return
        s.vars.setdefault(n, s.do)
        if s.vars[n] == s.do:
            s.do += 4
        if iv is not None:
            r = s._ge(iv)
            if isinstance(r, tuple) and r and r[0] == "arr":
                off, sz = r[1], r[2]
                s.arrays[n] = (off, sz)
                s.vars[n] = r
            else:
                s.sv(n, s._er(r))

    def _la(s, n):
        if isinstance(n, dict) and "var" in n and n["var"] in s.arrays:
            return s.arrays[n["var"]]
        if isinstance(n, dict) and "index" in n:
            return s._la(n["index"])
        return None

    def _ges(s, x):
        x = x["expr_stmt"]
        if "call" not in x:
            return
        cn = x["call"]
        args = x.get("args", [])
        if cn == "print_str" and args:
            a0 = args[0]
            if "string" in a0 or "var" in a0:
                sv = a0["string"] if "string" in a0 else a0["var"]
                so = s.do
                s.strs.append((so, sv))
                s.do += 4 + len(sv) * 4
                ba, le, i2, ch = s.ar(), s.ar(), s.ar(), s.ar()
                po = s._li(OUT_PORT)
                ls, le2 = s.ml("ps"), s.ml("pe")
                s.em(f"ADDI {ba}, gp, {so}")
                s.em(f"LW {le}, {ba}, 0")
                s.em(f"ADDI {ba}, {ba}, 4")
                s.em(f"ADDI {i2}, zero, 0")
                s.em(f"{ls}:")
                s.em(f"BGE {i2}, {le}, {le2}")
                s.em(f"SLLI {ch}, {i2}, 2")
                s.em(f"ADD {ch}, {ba}, {ch}")
                s.em(f"LW {ch}, {ch}, 0")
                s.em(f"SW {ch}, {po}, 0")
                s.em(f"ADDI {i2}, {i2}, 1")
                s.em(f"J {ls}")
                s.em(f"{le2}:")
                return
        if cn == "print_num" and args:
            vo = s._er(s._ge(args[0]))
            val = s.ar()
            s.em(f"MV {val}, {vo}")
            div, tmp, ten = s.ar(), s.ar(), s.ar()
            po = s._li(OUT_PORT)
            ls, l2, l3 = s.ml("pnl"), s.ml("pn2"), s.ml("pn3")
            s.em(f"ADDI {ten}, zero, 10")
            s.em(f"ADDI {div}, zero, 1")
            s.em(f"{ls}:")
            s.em(f"DIV {tmp}, {val}, {div}")
            s.em(f"BLT {tmp}, {ten}, {l2}")
            s.em(f"MUL {div}, {div}, {ten}")
            s.em(f"J {ls}")
            s.em(f"{l2}:")
            s.em(f"{l3}:")
            s.em(f"DIV {tmp}, {val}, {div}")
            s.em(f"REM {val}, {val}, {div}")
            s.em(f"ADDI {tmp}, {tmp}, 48")
            s.em(f"SW {tmp}, {po}, 0")
            s.em(f"DIV {div}, {div}, {ten}")
            s.em(f"BNE {div}, zero, {l3}")
            return
        if cn == "print":
            po = s._li(OUT_PORT)
            for a in args:
                s.em(f"SW {s._er(s._ge(a))}, {po}, 0")
            return
        if cn == "readln":
            if not args:
                s.em(f"LW {s.ar()}, {s._li(IN_PORT)}, 0")
                return
            a = args[0]
            o = s._ge(a)
            addr, i2, ch, tmp = s.ar(), s.ar(), s.ar(), s.ar()
            inp = s._li(IN_PORT)
            if isinstance(o, tuple) and o[0] == "arr":
                s.em(f"ADDI {addr}, gp, {o[1]}")
            elif isinstance(o, int):
                s.em(f"ADDI {addr}, gp, {o}")
            else:
                s.em(f"ADD {addr}, gp, {s._er(o)}")
            s.em(f"ADDI {i2}, zero, 0")
            l1, l2 = s.ml("rl"), s.ml("re")
            s.em(f"{l1}:")
            s.em(f"LW {ch}, {inp}, 0")
            s.em(f"BEQ {ch}, zero, {l2}")
            s.em(f"ADDI {tmp}, {ch}, -10")
            s.em(f"BEQ {tmp}, zero, {l2}")
            s.em(f"SLLI {tmp}, {i2}, 2")
            s.em(f"ADD {tmp}, {addr}, {tmp}")
            s.em(f"SW {ch}, {tmp}, 0")
            s.em(f"ADDI {i2}, {i2}, 1")
            s.em(f"J {l1}")
            s.em(f"{l2}:")
            return
        for i, a in enumerate(args):
            if i < 8:
                s.em(f"MV a{i}, {s._er(s._ge(a))}")
        s.em(f"JAL ra, {cn}")

    def _gc(s, k, cond, body, eb):
        lc = s.ml("wc") if k == "while" else None
        le = s.ml("el") if k == "if" else None
        le2 = s.ml("en")
        if k == "while":
            s.em(f"{lc}:")
        cv = s._ge(cond)
        if isinstance(cv, tuple) and len(cv) == 3 and cv[0] in _CMP:
            op, rs1, rs2 = cv
            s.em(f"{_CMP[op]} {rs1}, {rs2}, {le if k == 'if' else le2}")
        else:
            s.em(f"BEQ {s._er(cv)}, zero, {le if k == 'if' else le2}")
        for st in body:
            s._gs(st)
        if k == "if":
            if eb:
                s.em(f"J {le2}")
                s.em(f"{le}:")
                for st in eb:
                    s._gs(st)
            else:
                s.em(f"{le}:")
            s.em(f"{le2}:")
        else:
            s.em(f"J {lc}")
            s.em(f"{le2}:")

    def _ge(s, e, tr=None):
        if isinstance(e, int):
            return e
        if "int" in e:
            return e["int"]
        if "char" in e:
            return e["char"]
        if "bool" in e:
            return 1 if e["bool"] else 0
        if "index" in e:
            bl = s._la(e["index"])
            if bl is None:
                return 0
            o, _n = bl
            ir = s._er(s._ge(e["at"]))
            ar = s.ar()
            s.em(f"SLLI {ar}, {ir}, 2")
            s.em(f"ADDI {ar}, {ar}, {o}")
            s.em(f"ADD {ar}, {ar}, gp")
            r = tr or s.ar()
            s.em(f"LW {r}, {ar}, 0")
            return r
        if "var" in e:
            n = e["var"]
            if n in s.arrays:
                o, n2 = s.arrays[n]
                return ("arr", o, n2)
            v = s._vv(n, True)
            if tr and tr != v:
                s.em(f"MV {tr}, {v}")
            return tr if tr else v
        if "unary" in e:
            ev = s._ge(e["operand"])
            r = tr or s.ar()
            if e["unary"] == "-":
                s.em(f"SUB {r}, zero, {s._er(ev)}")
            else:
                s.em(f"XORI {r}, {s._er(ev)}, 1")
            return r
        if "binop" in e:
            op = e["binop"]
            if op in ("&&", "||"):
                sr = f"s{s.sc}"
                s.sc += 1
                r = tr or s.ar()
                lv = s._ge(e["left"])
                s.em(f"MV {r}, {s._er(lv)}")
                s.em(f"MV {sr}, {r}")
                le = s.ml("sc")
                s.em(f"{'BEQ' if op == '&&' else 'BNE'} {sr}, zero, {le}")
                rv = s._ge(e["right"])
                s.sc -= 1
                s.em(f"{'AND' if op == '&&' else 'OR'} {sr}, {sr}, {s._er(rv)}")
                s.em(f"{le}:")
                if tr and tr != sr:
                    s.em(f"MV {tr}, {sr}")
                    return tr
                return sr
            return s._eb(op, s._ge(e["left"]), s._ge(e["right"]), tr)
        if "call" in e and e["call"] == "read":
            r = tr or s.ar()
            s.em(f"LW {r}, {s._li(IN_PORT)}, 0")
            return r
        if "call" in e and e["call"] == "len":
            if e["args"] and "var" in e["args"][0] and e["args"][0]["var"] in s.arrays:
                return s.arrays[e["args"][0]["var"]][1]
            return 0
        if "call" in e:
            for i, a in enumerate(e["args"]):
                if i < 8:
                    s.em(f"MV a{i}, {s._er(s._ge(a))}")
            s.em(f"JAL ra, {e['call']}")
            r = tr or s.ar()
            s.em(f"MV {r}, a0")
            return r
        return 0

    def _er(s, v, tr=None):
        if isinstance(v, tuple):
            r = tr or s.ar()
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
                s.em(inst)
            return r
        if v == 0:
            return "zero" if tr is None else (s.em(f"MV {tr}, zero"), tr)[1]
        if isinstance(v, int):
            return s._li(v, tr)
        return v

    def _eb(s, op, left, right, tr=None):
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
            return (op, s._er(left), s._er(right))
        if isinstance(right, int) and -2048 <= right <= 2047:
            lr = s._er(left)
            res = tr or s.ar()
            if op == "+":
                s.em(f"ADDI {res}, {lr}, {right}")
                return res
            if op == "-" and -2048 <= -right <= 2047:
                s.em(f"ADDI {res}, {lr}, {-right}")
                return res
            if op in ("&", "|", "^", "<<", ">>"):
                s.em(f"{BM[op]}I {res}, {lr}, {right}")
                return res
        lr, rr = s._er(left), s._er(right)
        res = tr or s.ar()
        if op in ("||", "&&"):
            s.em(f"{'OR' if op == '||' else 'AND'} {res}, {lr}, {rr}")
            return res
        if op in BM:
            s.em(f"{BM[op]} {res}, {lr}, {rr}")
        return res

    def _fn(s):
        its = []
        for n, loc in s.vars.items():
            if isinstance(loc, int):
                its.append((loc, f"    .word 0  ; {n}", 4))
            elif isinstance(loc, tuple) and loc[0] == "arr":
                off, sz = loc[1], loc[2]
                for i in range(sz):
                    its.append((off + i * 4, f"    .word {s.dv.get(off + i * 4, 0)}  ; {n}[{i}]", 4))
        esc = {"\n": "\\n", "\t": "\\t", "\r": "\\r", '"': '\\"', "\\": "\\\\"}
        for o, c in s.strs:
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
        for l in s.asm:
            ln.append(l)
            if l.strip() == "main:":
                ln.append("    ADDI gp, zero, data_start")
        return "\n".join(ln)

    def dump_ast(s, src):
        s.parse(src)
        return s.ast if s.ast else {}

    def get_ast(s):
        return s.ast

    def run(s, src):
        return s.gen(s.parse(src))
