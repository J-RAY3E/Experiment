import re
from src.ISA import IMM21_MASK, IN_PORT, OUT_PORT

PRECEDENCE = [
    {"||"}, {"&&"}, {"|"}, {"^"}, {"&"},
    {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"},
    {"+", "-"}, {"*", "/", "%"}
]

BINOP_MAP = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "REM",
    "&": "AND", "|": "OR", "^": "XOR", "<<": "SLL", ">>": "SRL"
}

KEYWORDS = {"function", "let", "if", "else", "while", "halt", "true", "false", "return"}
BUILTINS = {"print", "read", "readln"}
TEMP_REGS = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
VAR_REGS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"]
IMM11_MIN, IMM11_MAX = -1024, 1023

class HL:
    def __init__(self):
        self.vars = {}
        self.data_offset = 0
        self.label_counter = 0
        self.asm = []
        self.nreg = 0
        self.data_labels = []

    def _alloc_reg(self):
        r = TEMP_REGS[self.nreg % len(TEMP_REGS)]
        self.nreg += 1
        return r

    def _make_label(self, p="L"):
        self.label_counter += 1
        return f"{p}_{self.label_counter}"

    def _emit(self, line=""):
        self.asm.append(("    " + line) if line else "")

    def _var_loc(self, name):
        if name not in self.vars:
            if len(self.vars) < len(VAR_REGS):
                self.vars[name] = VAR_REGS[len(self.vars)]
            else:
                self.vars[name] = self.data_offset
                self.data_offset += 1
        return self.vars[name]

    def _load_var(self, name):
        loc = self._var_loc(name)
        if loc in VAR_REGS:
            return loc
        reg = self._alloc_reg()
        self._emit(f"LW {reg}, gp, {loc}")
        return reg

    def _store_var(self, name, reg):
        loc = self._var_loc(name)
        if loc in VAR_REGS:
            if loc != reg:
                self._emit(f"MV {loc}, {reg}")
        else:
            self._emit(f"SW {reg}, gp, {loc}")

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("", "")

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, *v):
        t = self._peek()
        if t[1] in v or t[0] in v:
            return self._advance()
        raise SyntaxError(f"expected {v}, got {t} at {self.pos}")

    def tokenize(self, src):
        self.tokens = []
        pattern = r"//.*|0[xX][0-9a-fA-F]+|\d+|'[^'\\]*(?:\\.[^'\\]*)*'|[a-zA-Z_]\w*|&&|\|\||<<|>>|<=|>=|==|!=|[-+*/%&|^~<>=!]=?|[{}();,]"
        for m in re.finditer(pattern, src):
            t = m.group()
            if t.startswith("//"):
                continue
            if t.startswith("0x") or t.startswith("0X"):
                self.tokens.append(("H", int(t, 16)))
            elif t.isdigit():
                self.tokens.append(("N", int(t)))
            elif t.startswith("'"):
                c = t[1:-1]
                val = {"n": 10, "t": 9, "r": 13, "0": 0}.get(c[1], ord(c[1])) if len(c) > 1 and c[0] == "\\" else ord(c)
                self.tokens.append(("C", val))
            elif t[0].isalpha() or t[0] == "_":
                tag = "K" if t in KEYWORDS else "B" if t in BUILTINS else "I"
                self.tokens.append((tag, t))
            elif t in "{}();,":
                self.tokens.append(("S", t))
            else:
                self.tokens.append(("O", t))
        self.tokens.append(("", ""))
        self.pos = 0

    def run(self, src):
        self.tokenize(src)
        self._parse_program()
        return self._finish()

    def _parse_program(self):
        while self._peek()[0] != "":
            if self._peek() == ("K", "function"):
                self._parse_function()
            else:
                self._advance()

    def _parse_function(self):
        self._advance()
        name = self._advance()[1]
        self._expect("(")
        self._expect(")")
        self._expect("{")
        self._emit(f"{name}:")
        while self._peek()[1] != "}":
            self._parse_stmt()
        self._expect("}")
        self._emit("HALT")
        self.data_labels.append(name)

    def _parse_stmt(self):
        t = self._peek()
        if t == ("K", "let"):
            self._parse_let()
        elif t == ("K", "if"):
            self._parse_if()
        elif t == ("K", "while"):
            self._parse_while()
        elif t == ("K", "halt"):
            self._advance()
            self._expect(";")
            self._emit("HALT")
        elif t == ("K", "return"):
            self._advance()
            if self._peek()[1] != ";":
                reg = self._ensure_reg(self._parse_expr(0))
                self._emit(f"MV a0, {reg}")
            self._expect(";")
        elif t[0] == "S" and t[1] == "{":
            self._advance()
            while self._peek()[1] != "}":
                self._parse_stmt()
            self._expect("}")
        elif t[0] == "B":
            self._parse_builtin()
        elif t[0] == "S" and t[1] == ";":
            self._advance()
        else:
            self._parse_assign()

    def _parse_let(self):
        self._advance()
        name = self._expect("I")[1]
        loc = self._var_loc(name)
        target = loc if loc in VAR_REGS else None
        if self._peek()[1] == "=":
            self._advance()
            self._parse_expr(0, target_reg=target)
        self._expect(";")

    def _parse_assign(self):
        name = self._advance()[1]
        if self._peek()[1] == "(":
            self._advance()
            self._advance()
            self._expect(")")
            self._expect(";")
        else:
            self._expect("=")
            loc = self._var_loc(name)
            target = loc if loc in VAR_REGS else None
            r = self._parse_expr(0, target_reg=target)
            if r != target:
                self._store_var(name, self._ensure_reg(r, target_reg=target))
            self._expect(";")

    def _emit_io_addr(self, addr):
        reg = self._alloc_reg()
        lo = addr & 0x7FF
        if lo >= 0x400:
            lo -= 0x800
        hi = (addr - lo) >> 11
        self._emit(f"LUI {reg}, {hi & IMM21_MASK}")
        if lo:
            self._emit(f"ADDI {reg}, {reg}, {lo}")
        return reg

    def _parse_builtin(self):
        name = self._advance()[1]
        self._expect("(")
        arg = self._parse_expr(0) if self._peek()[1] != ")" else None
        self._expect(")")
        self._expect(";")
        if name == "print" and arg is not None:
            val = self._ensure_reg(arg)
            port = self._emit_io_addr(OUT_PORT)
            self._emit(f"SW {val}, {port}, 0")
        elif name == "read":
            port = self._emit_io_addr(IN_PORT)
            reg = self._alloc_reg()
            self._emit(f"LW {reg}, {port}, 0")
            return reg

    def _emit_branch(self, cond, label, invert=False):
        if not isinstance(cond, tuple):
            reg = self._ensure_reg(cond)
            # Map single condition to BEQ/BNE with zero register
            op = "BNE" if invert else "BEQ"
            self._emit(f"{op} {reg}, zero, {label}")
            return
        op, rs1, rs2 = cond
        bm_norm = {"==": "BNE", "!=": "BEQ", "<": "BGE", ">=": "BLT", ">": "BLE", "<=": "BGT"}
        bm_inv = {"==": "BEQ", "!=": "BNE", "<": "BLT", ">=": "BGE", ">": "BGT", "<=": "BLE"}
        bm = bm_inv if invert else bm_norm
        self._emit(f"{bm[op]} {rs1}, {rs2}, {label}")

    def _parse_if(self):
        self._advance()
        self._expect("(")
        cond = self._parse_expr(0)
        l_else, l_end = self._make_label("el"), self._make_label("en")
        self._emit_branch(cond, l_else)
        self._expect(")")
        self._parse_stmt()
        self._emit(f"J {l_end}")
        self._emit(f"{l_else}:")
        if self._peek() == ("K", "else"):
            self._advance()
            self._parse_stmt()
        self._emit(f"{l_end}:")

    def _parse_while(self):
        self._advance()
        self._expect("(")
        l_start, l_end = self._make_label("w"), self._make_label("ew")
        self._emit(f"{l_start}:")
        cond = self._parse_expr(0)
        self._emit_branch(cond, l_end)
        self._expect(")")
        self._parse_stmt()
        self._emit(f"J {l_start}")
        self._emit(f"{l_end}:")

    def _parse_expr(self, min_prec, target_reg=None):
        left = self._parse_primary(target_reg=target_reg if min_prec == 0 else None)
        while True:
            t = self._peek()
            if t[0] != "O":
                break
            prec = next((i for i, l in enumerate(PRECEDENCE) if t[1] in l), -1)
            if prec < 0 or prec < min_prec:
                break
            self._advance()
            right = self._parse_expr(prec + 1)
            left = self._emit_binop(t[1], left, right, target_reg=target_reg)
        return left

    def _parse_primary(self, target_reg=None):
        t = self._advance()
        if t[0] in ("N", "H", "C"):
            return self._ensure_reg(t[1], target_reg=target_reg) if target_reg else t[1]
        if t[0] == "K" and t[1] in ("true", "false"):
            v = 1 if t[1] == "true" else 0
            return self._ensure_reg(v, target_reg=target_reg) if target_reg else v
        if t[0] == "I":
            if self._peek()[1] == "(":
                fn = t[1]
                self._advance()
                while self._peek()[1] != ")":
                    self._advance()
                self._expect(")")
                if fn == "read":
                    r = target_reg or self._alloc_reg()
                    p = self._emit_io_addr(IN_PORT)
                    self._emit(f"LW {r}, {p}, 0")
                    return r
                return target_reg or self._alloc_reg()
            v = self._load_var(t[1])
            if target_reg and target_reg != v:
                self._emit(f"MV {target_reg}, {v}")
            return target_reg if target_reg else v
        if t[0] == "S" and t[1] == "(":
            e = self._parse_expr(0, target_reg=target_reg)
            self._expect(")")
            return e
        if t[0] == "O" and t[1] in ("-", "~", "!"):
            e = self._parse_expr(len(PRECEDENCE))
            r = target_reg or self._alloc_reg()
            if t[1] == "-":
                self._emit(f"SUB {r}, zero, {self._ensure_reg(e)}")
            elif t[1] == "~":
                self._emit(f"XORI {r}, {self._ensure_reg(e)}, -1")
            return r
        return 0

    def _emit_binop(self, op, left, right, target_reg=None):
        if isinstance(left, int) and isinstance(right, int):
            ops = {
                "+": left + right, "-": left - right, "*": left * right,
                "/": left // right if right else 0, "%": left % right if right else 0,
                "&": left & right, "|": left | right, "^": left ^ right,
                "<<": left << right, ">>": left >> right,
                "<": 1 if left < right else 0, ">": 1 if left > right else 0,
                "<=": 1 if left <= right else 0, ">=": 1 if left >= right else 0,
                "==": 1 if left == right else 0, "!=": 1 if left != right else 0
            }
            return ops.get(op, 0)
        if op in ("<", ">", "<=", ">=", "==", "!="):
            return (op, self._ensure_reg(left), self._ensure_reg(right))
        if isinstance(right, int) and IMM11_MIN <= right <= IMM11_MAX:
            lr = self._ensure_reg(left)
            res = target_reg or self._alloc_reg()
            if op == "+":
                self._emit(f"ADDI {res}, {lr}, {right}")
                return res
            if op == "-" and IMM11_MIN <= -right <= IMM11_MAX:
                self._emit(f"ADDI {res}, {lr}, {-right}")
                return res
            if op in ("&", "|", "^", "<<", ">>"):
                self._emit(f"{BINOP_MAP[op]}I {res}, {lr}, {right}")
                return res
        lr, rr = self._ensure_reg(left), self._ensure_reg(right)
        res = target_reg or self._alloc_reg()
        if op in BINOP_MAP:
            self._emit(f"{BINOP_MAP[op]} {res}, {lr}, {rr}")
        return res

    def _ensure_reg(self, v, target_reg=None):
        if isinstance(v, tuple):
            r = target_reg or self._alloc_reg()
            op, lr, rr = v
            if op == "<": self._emit(f"SLT {r}, {lr}, {rr}")
            elif op == ">": self._emit(f"SLT {r}, {rr}, {lr}")
            elif op == "<=":
                self._emit(f"SLT {r}, {rr}, {lr}")
                self._emit(f"XORI {r}, {r}, 1")
            elif op == ">=":
                self._emit(f"SLT {r}, {lr}, {rr}")
                self._emit(f"XORI {r}, {r}, 1")
            elif op in ("==", "!="):
                self._emit(f"SUB {r}, {lr}, {rr}")
                t1, t2 = self._alloc_reg(), self._alloc_reg()
                self._emit(f"SLT {t1}, zero, {r}")
                self._emit(f"SLT {t2}, {r}, zero")
                self._emit(f"OR {r}, {t1}, {t2}")
                if op == "==": self._emit(f"XORI {r}, {r}, 1")
            return r
        if v == 0:
            if target_reg: self._emit(f"MV {target_reg}, zero")
            return "zero"
        if isinstance(v, int):
            r = target_reg or self._alloc_reg()
            if IMM11_MIN <= v <= IMM11_MAX:
                self._emit(f"ADDI {r}, zero, {v}")
            else:
                lo = v & 0x7FF
                if lo >= 0x400: lo -= 0x800
                hi = (v - lo) >> 11
                self._emit(f"LUI {r}, {hi & IMM21_MASK}")
                if lo: self._emit(f"ADDI {r}, {r}, {lo}")
            return r
        return v

    def _finish(self):
        if self.vars:
            self.asm.append(f"\n.org {self.data_offset + 100}")
            for n in sorted(self.vars, key=lambda x: self.vars[x] if isinstance(self.vars[x], int) else -1):
                if isinstance(self.vars[n], int):
                    self.asm.append(f"    .word 0  ; {n}")
        return "    .org 0\n" + "\n".join(self.asm)
