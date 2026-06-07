from __future__ import annotations

import re

from src.ast_nodes import (
    ArrayLiteral,
    AssignStmt,
    BinaryOp,
    BlockStmt,
    BoolLiteral,
    CallExpr,
    CharLiteral,
    ExprStmt,
    FunctionDef,
    HaltStmt,
    IfStmt,
    IndexAssignStmt,
    IndexExpr,
    IntLiteral,
    LetStmt,
    Program,
    ReturnStmt,
    StringLiteral,
    UnaryOp,
    VarRef,
    WhileStmt,
)
from src.isa import IMM21_MASK, IN_PORT, OUT_PORT

PREC = [{"||"}, {"&&"}, {"|"}, {"^"}, {"&"}, {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"}, {"+", "-"}, {"*", "/", "%"}]
BM = {"+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "REM", "&": "AND", "|": "OR", "^": "XOR", "<<": "SLL", ">>": "SRL"}
VBM = {"+": "VADD", "-": "VSUB", "*": "VMUL", "/": "VDIV"}
KW = {"function", "let", "if", "else", "while", "halt", "true", "false", "return"}
BI = {"print", "print_str", "print_num", "read", "readln", "vload", "vadd", "vstore", "len"}
TREGS = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
VREGS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"]
I11 = -1024, 1023


class HL:
    def __init__(self):
        self.vars = {}
        self.arrays = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.nv = 0
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

    def parse(self, s):
        self.tokenize(s)
        fs = []
        while self.peek()[0] != "":
            if self.peek() == ("K", "function"):
                self.adv()
                n = self.adv()[1]
                self.args()
                self.exp("{")
                b = self._stmts("}")
                self.exp("}")
                fs.append(FunctionDef(n, b))
            else:
                self.adv()
        self.ast = Program(fs)
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
            return LetStmt(n, iv, sz)
        if t == ("K", "if"):
            return self._ifwhile("if")
        if t == ("K", "while"):
            return self._ifwhile("while")
        if t == ("K", "halt"):
            self.adv()
            self.exp(";")
            return HaltStmt()
        if t == ("K", "return"):
            self.adv()
            v = self.pexpr() if self.peek()[1] != ";" else None
            self.exp(";")
            return ReturnStmt(v)
        if t[0] == "S" and t[1] == "{":
            self.adv()
            b = self._stmts("}")
            self.exp("}")
            return BlockStmt(b)
        if t[0] == "B":
            n = self.adv()[1]
            a = self.args()
            self.exp(";")
            return ExprStmt(CallExpr(n, a))
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
        bl = [b] if not isinstance(b, BlockStmt) else b.body
        if k == "while":
            return WhileStmt(c, bl)
        el = None
        if self.peek() == ("K", "else"):
            self.adv()
            eb = self._stmt()
            el = [eb] if not isinstance(eb, BlockStmt) else eb.body
        return IfStmt(c, bl, el)

    def _assign(self):
        n = self.adv()[1]
        if self.peek()[1] == "(":
            a = self.args()
            self.exp(";")
            return ExprStmt(CallExpr(n, a))
        tg = VarRef(n)
        while self.peek()[1] == "[":
            self.adv()
            tg = IndexExpr(tg, self.pexpr())
            self.exp("]")
        self.exp("=")
        v = self.pexpr()
        self.exp(";")
        return AssignStmt(n, v) if isinstance(tg, VarRef) else IndexAssignStmt(tg, v)

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
            res = BinaryOp(t[1], res, self.pexpr(p + 1))
        return res

    def _prim(self):
        t = self.adv()
        if t[0] in ("N", "H"):
            return IntLiteral(t[1])
        if t[0] == "C":
            return CharLiteral(t[1])
        if t[0] == "K" and t[1] in ("true", "false"):
            return BoolLiteral(t[1] == "true")
        if t[0] == "STR":
            return StringLiteral(t[1])
        if t[0] == "S" and t[1] == "{":
            e = []
            if self.peek()[1] != "}":
                e.append(self.pexpr())
                while self.peek()[1] == ",":
                    self.adv()
                    e.append(self.pexpr())
            self.exp("}")
            return ArrayLiteral(e)
        if t[0] in ("I", "B"):
            if self.peek()[1] == "(":
                f = t[1]
                a = self.args()
                return CallExpr(f, a)
            if t[0] == "I":
                n2 = VarRef(t[1])
                while self.peek()[1] == "[":
                    self.adv()
                    n2 = IndexExpr(n2, self.pexpr())
                    self.exp("]")
                return n2
            raise SyntaxError(f"unexpected builtin {t} at {self.pos}")
        if t[0] == "S" and t[1] == "(":
            e = self.pexpr()
            self.exp(")")
            return e
        if t[0] == "O" and t[1] in ("-", "~", "!"):
            return UnaryOp(t[1], self.pexpr(len(PREC)))
        raise SyntaxError(f"unexpected token {t} at {self.pos}")

    def gen(self, a):
        self.vars = {}
        self.do = 0
        self.lc = 0
        self.asm = []
        self.nr = 0
        self.nv = 0
        self.dl = []
        self.strs = []
        self.dv = {}
        self.arrays = {}
        for f in a.functions:
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

    def vl(self, n):
        if n not in self.vars:
            self.vars[n] = VREGS[len(self.vars)] if len(self.vars) < 12 else self.do
            if isinstance(self.vars[n], int):
                self.do += 1
        return self.vars[n]

    def lv(self, n):
        loc = self.vl(n)
        return loc if loc in VREGS else (r := self.ar(), self.em(f"LW {r}, gp, {loc}"), r)[2]

    def sv(self, n, r):
        loc = self.vl(n)
        if loc in VREGS:
            if loc != r:
                self.em(f"MV {loc}, {r}")
        else:
            self.em(f"SW {r}, gp, {loc}")

    def li(self, v, r=None):
        rr = r or self.ar()
        if I11[0] <= v <= I11[1]:
            self.em(f"ADDI {rr}, zero, {v}")
        else:
            lo = v & 0x7FF
            if lo >= 0x400:
                lo -= 0x800
            hi = (v - lo) >> 11
            self.em(f"LUI {rr}, {hi & IMM21_MASK}")
            if lo:
                self.em(f"ADDI {rr}, {rr}, {lo}")
        return rr

    def als(self, c):
        o = self.do
        self.strs.append((o, c))
        self.do += 1 + len(c)
        return o

    def _gfunc(self, f):
        self.em(f"{f.name}:")
        for s in f.body:
            self._gs(s)
        if not self.asm or self.asm[-1].strip() != "HALT":
            self.em("HALT")
        self.dl.append(f.name)

    def _gs(self, s):
        t = type(s)
        if t is LetStmt:
            self._gl(s)
        elif t is AssignStmt:
            self._ga(s)
        elif t is IndexAssignStmt:
            self._gia(s)
        elif t is IfStmt:
            self._gc("if", s.cond, s.then_body, getattr(s, "else_body", None))
        elif t is WhileStmt:
            self._gc("while", s.cond, s.body, None)
        elif t is ReturnStmt:
            if s.value is not None:
                self.em(f"MV a0, {self.er(self.ge(s.value))}")
        elif t is ExprStmt:
            self._ges(s)
        elif t is BlockStmt:
            for x in s.body:
                self._gs(x)
        elif t is HaltStmt:
            self.em("HALT")

    def _gl(self, s):
        n = s.name
        iv = s.init
        if s.array_size is not None or isinstance(iv, ArrayLiteral):
            sz = (
                s.array_size.value
                if s.array_size is not None and isinstance(s.array_size, IntLiteral)
                else (len(iv.elements) if isinstance(iv, ArrayLiteral) else 4)
            )
            o = self.do
            self.do += sz
            if isinstance(iv, ArrayLiteral):
                for i, el in enumerate(iv.elements):
                    if i >= sz:
                        break
                    v = self.ge(el)
                    if isinstance(v, int):
                        self.dv[o + i] = v
                    else:
                        vr = self.er(v)
                        ar = self.ar()
                        self.em(f"ADDI {ar}, gp, {o + i}")
                        self.em(f"SW {vr}, {ar}, 0")
            elif iv is not None:
                r = self.ge(iv)
                if isinstance(r, tuple) and r and r[0] == "arr":
                    ro, rn = r[1], r[2]
                    for i in range(min(rn, sz)):
                        ar = self.ar()
                        self.em(f"ADDI {ar}, gp, {ro + i}")
                        self.em(f"LW {ar}, {ar}, 0")
                        self.em(f"SW {ar}, gp, {o + i}")
            self.arrays[n] = (o, sz)
            self.vars[n] = ("arr", o, sz)
            return
        loc = self.vl(n)
        tg = loc if loc in VREGS else None
        if iv is not None:
            r = self.ge(iv, target_reg=tg)
            if isinstance(r, tuple) and r and r[0] == "arr":
                self.arrays[n] = (r[1], r[2])
                self.vars[n] = r
            elif r != tg:
                self.sv(n, self.er(r, target_reg=tg))

    def _ga(self, s):
        if s.name in self.arrays:
            r = self.ge(s.value)
            if isinstance(r, tuple) and r and r[0] == "arr":
                self.arrays[s.name] = (r[1], r[2])
                self.vars[s.name] = r
            return
        loc = self.vl(s.name)
        tg = loc if loc in VREGS else None
        r = self.ge(s.value, target_reg=tg)
        if r != tg:
            self.sv(s.name, self.er(r, target_reg=tg))

    def _gia(self, s):
        tg = s.target
        if not isinstance(tg, IndexExpr):
            return
        bl = self._la(tg.array)
        if bl is None:
            return
        o, _n = bl
        vr = self.er(self.ge(s.value))
        ir = self.er(self.ge(tg.index))
        ar = self.ar()
        self.em(f"ADDI {ar}, gp, {o}")
        self.em(f"ADD {ar}, {ar}, {ir}")
        self.em(f"SW {vr}, {ar}, 0")

    def _la(self, n):
        if isinstance(n, VarRef) and n.name in self.arrays:
            return self.arrays[n.name]
        if isinstance(n, IndexExpr):
            return self._la(n.array)
        return None

    def _ges(self, e):
        x = e.expr
        if isinstance(x, CallExpr) and x.name == "print_str":
            if x.args and isinstance(x.args[0], (StringLiteral, VarRef)):
                s = x.args[0].value if isinstance(x.args[0], StringLiteral) else x.args[0].name
                so = self.als(s)
                ba = self.ar()
                le = self.ar()
                i2 = self.ar()
                ch = self.ar()
                po = self.li(OUT_PORT)
                ls = self.ml("ps")
                le2 = self.ml("pe")
                self.em(f"ADDI {ba}, gp, {so}")
                self.em(f"LW {le}, {ba}, 0")
                self.em(f"ADDI {ba}, {ba}, 1")
                self.em(f"ADDI {i2}, zero, 0")
                self.em(f"{ls}:")
                self.em(f"BGE {i2}, {le}, {le2}")
                self.em(f"ADD {ch}, {ba}, {i2}")
                self.em(f"LW {ch}, {ch}, 0")
                self.em(f"SW {ch}, {po}, 0")
                self.em(f"ADDI {i2}, {i2}, 1")
                self.em(f"J {ls}")
                self.em(f"{le2}:")
                return
        if isinstance(x, CallExpr) and x.name == "print_num":
            if x.args:
                val_orig = self.er(self.ge(x.args[0]))
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
        if isinstance(x, CallExpr) and x.name == "print":
            po = self.li(OUT_PORT)
            for a in x.args:
                self.em(f"SW {self.er(self.ge(a))}, {po}, 0")
            return
        if isinstance(x, CallExpr) and x.name == "readln":
            self.em(f"LW {self.ar()}, {self.li(IN_PORT)}, 0")
            return
        if isinstance(x, CallExpr) and x.name == "vstore":
            o = self.ge(x.args[0])
            idx = self.ge(x.args[1]) if len(x.args) > 2 else None
            vv = self.ge(x.args[2] if len(x.args) > 2 else x.args[1])
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
        if isinstance(x, CallExpr):
            for i, a in enumerate(x.args):
                if i < 8:
                    self.em(f"MV a{i}, {self.er(self.ge(a))}")
            self.em(f"JAL {x.name}")

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
        if isinstance(e, (IntLiteral, BoolLiteral, CharLiteral)):
            return e.value if not isinstance(e, BoolLiteral) else (1 if e.value else 0)
        if isinstance(e, IndexExpr):
            bl = self._la(e.array)
            if bl is None:
                return 0
            o, _n = bl
            ir = self.er(self.ge(e.index))
            ar = self.ar()
            self.em(f"ADDI {ar}, gp, {o}")
            self.em(f"ADD {ar}, {ar}, {ir}")
            r = target_reg or self.ar()
            self.em(f"LW {r}, {ar}, 0")
            return r
        if isinstance(e, VarRef):
            if e.name in self.arrays:
                o, n = self.arrays[e.name]
                return ("arr", o, n)
            v = self.lv(e.name)
            if target_reg and target_reg != v:
                self.em(f"MV {target_reg}, {v}")
            return target_reg if target_reg else v
        if isinstance(e, UnaryOp):
            ev = self.ge(e.operand)
            r = target_reg or self.ar()
            if e.op == "-":
                self.em(f"SUB {r}, zero, {self.er(ev)}")
            else:
                self.em(f"XORI {r}, {self.er(ev)}, -1")
            return r
        if isinstance(e, BinaryOp):
            return self._eb(e.op, self.ge(e.left), self.ge(e.right), target_reg)
        if isinstance(e, CallExpr) and e.name == "read":
            r = target_reg or self.ar()
            self.em(f"LW {r}, {self.li(IN_PORT)}, 0")
            return r
        if isinstance(e, CallExpr) and e.name == "len":
            if e.args and isinstance(e.args[0], VarRef) and e.args[0].name in self.arrays:
                return self.arrays[e.args[0].name][1]
            return 0
        if isinstance(e, CallExpr) and e.name == "vload":
            o = self.ge(e.args[0])
            idx = self.ge(e.args[1]) if len(e.args) > 1 else None
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
        if isinstance(e, CallExpr) and e.name == "vadd":
            v1 = self.ge(e.args[0])
            v2 = self.ge(e.args[1])
            if isinstance(v1, tuple) and isinstance(v2, tuple):
                vr = self.av()
                self.em(f"VADD {vr}, {v1[1]}, {v2[1]}")
                return ("v", vr)
            return 0
        if isinstance(e, CallExpr):
            for i, a in enumerate(e.args):
                if i < 8:
                    self.em(f"MV a{i}, {self.er(self.ge(a))}")
            self.em(f"JAL {e.name}")
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
            self.do += ln
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
                self.em(f"ADDI {rlo}, {rlo}, 4")
                self.em(f"ADDI {rro}, {rro}, 4")
                self.em(f"ADDI {rro2}, {rro2}, 4")
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
                    self.em(f"ADDI {rlo}, {rlo}, 1")
                    self.em(f"ADDI {rro}, {rro}, 1")
                    self.em(f"ADDI {rro2}, {rro2}, 1")
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
        if isinstance(right, int) and I11[0] <= right <= I11[1]:
            lr = self.er(left)
            res = target_reg or self.ar()
            if op == "+":
                self.em(f"ADDI {res}, {lr}, {right}")
                return res
            if op == "-" and I11[0] <= -right <= I11[1]:
                self.em(f"ADDI {res}, {lr}, {-right}")
                return res
            if op in ("&", "|", "^", "<<", ">>"):
                self.em(f"{BM[op]}I {res}, {lr}, {right}")
                return res
        lr, rr = self.er(left), self.er(right)
        res = target_reg or self.ar()
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
                    its.append((off + i, f"    .word {self.dv.get(off + i, 0)}  ; {n}[{i}]"))
        esc = {"\n": "\\n", "\t": "\\t", "\r": "\\r", '"': '\\"', "\\": "\\\\"}
        for o, c in self.strs:
            its.append((o, f'    .string "{"".join(esc.get(ch, ch) for ch in c)}"'))
        its.sort(key=lambda x: x[0])
        lns = ["    .org 0", "    J main", "    .org 1", "data_start:"]
        cur = 1
        for ao, line in its:
            addr = 1 + ao
            if addr > cur:
                lns.append(f"    .org {addr}")
                cur = addr
            lns.append(line)
            if ".string" in line:
                m = re.search(r'\.string "(.*)"', line)
                if m:
                    s_raw = m.group(1)
                    s_len = len(s_raw.replace("\\n", "\n").replace("\\t", "\t").replace("\\r", "\r").replace('\\"', '"').replace("\\\\", "\\"))
                    cur += 1 + s_len
            else:
                cur += 1
        code_base = 1 + self.do
        if not its:
            lns.append("    .word 0  ; dummy")
            code_base = 2
        lns.append(f"    .org {code_base}")
        for ln in self.asm:
            lns.append(ln)
            if ln.strip() == "main:":
                lns.append("    ADDI gp, zero, data_start")
        return "\n".join(lns)

    def run(self, s):
        return self.gen(self.parse(s))

    def dump_ast(self, s):
        self.parse(s)
        return self.ast.to_dict() if self.ast else {}

    def get_ast(self):
        return self.ast
