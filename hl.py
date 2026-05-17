"""Single-pass high-level to RISC assembly translator.

Translates a JavaScript-like language with the following features:
- 'function' keyword for function definitions
- 'let' for variable declarations with optional initialization
- 'if/else' conditional statements
- 'while' loops
- Expressions with arithmetic, bitwise, comparison operators
- Built-in I/O: print(), read()
- Constant folding for literal expressions

The translator operates in a single pass: tokenize -> parse + codegen -> emit ASM.
No intermediate AST is constructed — each statement is parsed and its
corresponding assembly is emitted immediately.

Variables are stored in data memory (accessed via gp-relative LW/SW).
Register allocation is round-robin across t0-t6.
"""

import re

PREC = [
    {"||"}, {"&&"}, {"|"}, {"^"}, {"&"},
    {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"},
    {"+", "-"}, {"*", "/", "%"},
]
BINOPS = {
    "+":"ADD","-":"SUB","*":"MUL","/":"DIV","%":"REM",
    "&":"AND","|":"OR","^":"XOR","<<":"SLL",">>":"SRL",
}

class HL:
    def __init__(self):
        self.vars = {}; self.doff = 0
        self.lcnt = 0; self.asm = []
        self.regs = ["t0","t1","t2","t3","t4","t5","t6"]
        self.nreg = 0; self.data_labels = []

    def r(self): r=self.regs[self.nreg%7]; self.nreg+=1; return r
    def L(self, p="L"): self.lcnt+=1; return f"{p}_{self.lcnt}"
    def e(self, s=""): self.asm.append(("    "+s) if s else "")

    def va(self, n):
        if n not in self.vars: self.vars[n]=self.doff; self.doff+=1
        return self.vars[n]
    def ld(self, n):
        r=self.r(); self.e(f"LW {r}, gp, {self.va(n)}"); return r
    def st(self, n, r): self.e(f"SW {r}, gp, {self.va(n)}")

    def tok(self): return self.ts[self.p] if self.p<len(self.ts) else ("","")
    def ad(self): t=self.ts[self.p]; self.p+=1; return t
    def ex(self, *vs):
        t=self.tok()
        if t[1] in vs or t[0] in vs: return self.ad()
        raise SyntaxError(f"want {vs}, got {t[1]} at {self.p}")

    def prec(self, op):
        for i,l in enumerate(PREC):
            if op in l: return i
        return -1

    def tokenize(self, src):
        self.ts = []
        for m in re.finditer(r"//.*|0[xX][0-9a-fA-F]+|\d+|'[^'\\]*(?:\\.[^'\\]*)*'|[a-zA-Z_]\w*|&&|\|\||<<|>>|<=|>=|==|!=|[-+*/%&|^~<>=!]=?|[{}();,]", src):
            t = m.group()
            if t.startswith("//"): continue
            if t.startswith("0x") or t.startswith("0X"):
                self.ts.append(("H", int(t, 16)))
            elif t.isdigit():
                self.ts.append(("N", int(t)))
            elif t.startswith("'"):
                c = t[1:-1]
                if len(c) > 1 and c[0] == "\\":
                    self.ts.append(("C", {"n":10,"t":9,"r":13,"0":0}[c[1]]))
                else:
                    self.ts.append(("C", ord(c)))
            elif t[0].isalpha() or t[0] == "_":
                if t in {"function","let","if","else","while","halt","true","false","return"}:
                    self.ts.append(("K", t))
                elif t in {"print","read","readln"}:
                    self.ts.append(("B", t))
                else:
                    self.ts.append(("I", t))
            elif t in "{}();,":
                self.ts.append(("S", t))
            elif t in {"&&","||","<<",">>","<=",">=","==","!="} or t in "-+*/%&|^~<>=!":
                self.ts.append(("O", t))
            else:
                self.ts.append(("O", t))
        self.ts.append(("",""))
        self.p = 0

    def run(self, src):
        self.tokenize(src)
        self.parse()
        return self.finish()

    def parse(self):
        while self.tok()[0]!="":
            if self.tok()==("K","function"): self.func()
            else: self.ad()

    def func(self):
        self.ad()  # consume 'function'
        name = self.ad()[1]  # function name
        self.ex("("); self.ex(")"); self.ex("{")
        self.e(f"{name}:")
        while self.tok()[1]!="}": self.stmt()
        self.ex("}")
        self.e("HALT")
        self.data_labels.append(name)

    def stmt(self):
        t=self.tok()
        if t==("K","let"): self.let()
        elif t==("K","if"): self.iff()
        elif t==("K","while"): self.whl()
        elif t==("K","halt"): self.ad(); self.ex(";"); self.e("HALT")
        elif t==("K","return"):
            self.ad()
            if self.tok()[1]!=";":
                r=self.expr(0); self.e(f"MV a0, {self.ir(r)}")
            self.ex(";")
        elif t[0]=="S"and t[1]=="{":
            self.ad()
            while self.tok()[1]!="}": self.stmt()
            self.ex("}")
        elif t[0]=="B": self.built()
        elif t[0]=="S"and t[1]==";": self.ad()
        else: self.assign()

    def let(self):
        self.ad(); n=self.ex("I")[1]
        if self.tok()[1]=="=":
            self.ad(); r=self.expr(0); self.st(n,self.ir(r))
        self.ex(";")

    def assign(self):
        n=self.ad()[1]
        if self.tok()[1]=="(":
            self.ad();self.ad();self.ex(")");self.ex(";")
        else:
            self.ex("="); r=self.expr(0); self.st(n,self.ir(r)); self.ex(";")

    def io_addr(self, addr):
        r = self.r()
        u = (addr >> 11) & 0x1FFFFF
        lo = addr & 0x7FF
        if lo > 1023:
            lo -= 2048
            u += 1
        self.e(f"LUI {r}, {u}")
        if lo:
            self.e(f"ADDI {r}, {r}, {lo}")
        return r

    def built(self):
        b=self.ad()[1]; self.ex("(")
        if self.tok()[1]!=")": a=self.expr(0)
        else: a=None
        self.ex(")"); self.ex(";")
        if b=="print"and a is not None:
            v=self.ir(a)
            p=self.io_addr(0xFFF4)
            self.e(f"SW {v}, {p}, 0")
        if b=="read":
            r=self.r()
            p=self.io_addr(0xFFF0)
            self.e(f"LW {r}, {p}, 0")

    def iff(self):
        self.ad(); self.ex("(")
        c=self.expr(0); c=self.ir(c)
        el,en=self.L("el"),self.L("en")
        self.e(f"BEQZ {c}, {el}")
        self.ex(")"); self.stmt()
        self.e(f"J {en}"); self.e(f"{el}:")
        if self.tok()==("K","else"): self.ad(); self.stmt()
        self.e(f"{en}:")

    def whl(self):
        self.ad(); self.ex("(")
        st,en=self.L("w"),self.L("ew")
        self.e(f"{st}:")
        c=self.expr(0); c=self.ir(c)
        self.e(f"BEQZ {c}, {en}")
        self.ex(")"); self.stmt()
        self.e(f"J {st}"); self.e(f"{en}:")

    def expr(self, mp):
        l=self.prim()
        while True:
            t=self.tok()
            if t[0]!="O": break
            p=self.prec(t[1])
            if p<0 or p<mp: break
            self.ad(); r=self.expr(p+1)
            l=self.mkbin(t[1],l,r)
        return l

    def prim(self):
        t=self.ad()
        if t[0]=="N": return t[1]
        if t[0]=="H": return t[1]
        if t[0]=="C": return t[1]
        if t[0]=="K"and t[1]in("true","false"): return 1 if t[1]=="true"else 0
        if t[0]=="I":
            if self.tok()[1]=="(":
                fn=t[1]
                self.ad()
                while self.tok()[1]!=")": self.ad()
                self.ex(")")
                if fn=="read":
                    r=self.r()
                    p=self.io_addr(0xFFF0)
                    self.e(f"LW {r}, {p}, 0")
                    return r
                return self.r()
            return self.ld(t[1])
        if t[0]=="S"and t[1]=="(":
            e=self.expr(0); self.ex(")"); return e
        if t[0]=="O"and t[1]in("-","~","!"):
            e=self.expr(len(PREC)); r=self.r()
            if t[1]=="-": self.e(f"SUB {r}, zero, {self.ir(e)}")
            elif t[1]=="~": self.e(f"XORI {r}, {self.ir(e)}, -1")
            return r
        return 0

    def mkbin(self, op, l, r):
        if isinstance(l,int)and isinstance(r,int):
            return self.fold(op,l,r)
        lr,rr=self.ir(l),self.ir(r)
        ro=self.r()
        if op in BINOPS: self.e(f"{BINOPS[op]} {ro}, {lr}, {rr}")
        elif op=="<": self.e(f"SLT {ro}, {lr}, {rr}")
        elif op==">": self.e(f"SLT {ro}, {rr}, {lr}")
        elif op=="<=":
            L=self.L("le")
            self.e(f"SLT {ro}, {rr}, {lr}");self.e(f"BEQZ {ro}, {L}")
            self.e(f"ADDI {ro}, zero, 0");self.e(f"{L}: ADDI {ro}, {ro}, 1")
        elif op==">=":
            L=self.L("ge")
            self.e(f"SLT {ro}, {lr}, {rr}");self.e(f"BEQZ {ro}, {L}")
            self.e(f"ADDI {ro}, zero, 0");self.e(f"{L}: ADDI {ro}, {ro}, 1")
        elif op=="==":
            L=self.L("eq")
            self.e(f"SUB {ro}, {lr}, {rr}");self.e(f"BNEZ {ro}, {L}")
            self.e(f"ADDI {ro}, zero, 1");self.e(f"J {L}_s");self.e(f"{L}: ADDI {ro}, zero, 0");self.e(f"{L}_s:")
        elif op=="!=":
            L=self.L("ne")
            self.e(f"SUB {ro}, {lr}, {rr}");self.e(f"BEQZ {ro}, {L}")
            self.e(f"ADDI {ro}, zero, 1");self.e(f"J {L}_s");self.e(f"{L}: ADDI {ro}, zero, 0");self.e(f"{L}_s:")
        return ro

    def ir(self, v):
        if isinstance(v, int):
            r=self.r()
            if -1024<=v<=1023: self.e(f"ADDI {r}, zero, {v}")
            elif 0<=v<=2097151: self.e(f"LUI {r}, {v}")
            else:
                u=(v>>11)&0x1FFFFF;lo=v&0x7FF
                if lo>1023:lo-=2048;u+=1
                self.e(f"LUI {r}, {u}");self.e(f"ADDI {r}, {r}, {lo}")
            return r
        return v

    def fold(self, op, a, b):
        return{
            "+":a+b,"-":a-b,"*":a*b,"/":a//b if b else 0,"%":a%b,
            "&":a&b,"|":a|b,"^":a^b,"<<":a<<b,">>":a>>b,
            "<":1 if a<b else 0,">":1 if a>b else 0,"<=":1 if a<=b else 0,
            ">=":1 if a>=b else 0,"==":1 if a==b else 0,"!=":1 if a!=b else 0,
        }.get(op,0)

    def finish(self):
        if self.vars:
            self.asm.append(f"")
            self.asm.append(f".org {self.doff + 100}")
            for n in sorted(self.vars, key=lambda n:self.vars[n]):
                self.asm.append(f"    .word 0  ; {n}")
        return "    .org 0\n" + "\n".join(self.asm)
