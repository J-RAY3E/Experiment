"""Single-pass high-level to RISC-IV assembly translator.

Translates a JavaScript-like language with:
- 'function' keyword for function definitions
- 'let' for variable declarations with optional initialization
- 'if/else' conditional statements
- 'while' loops
- Expressions with arithmetic, bitwise, comparison operators
- Built-in I/O: print(), read()
- Constant folding for literal expressions

The translator operates in a single pass: tokenize -> parse + codegen -> emit ASM.
No intermediate AST — each statement emits assembly immediately.

Variables are stored in data memory (accessed via gp-relative LW/SW).
Register allocation is round-robin across t0-t6.
"""

import re

from src.ISA import IMM21_MASK, IN_PORT, OUT_PORT

PRECEDENCE = [
    {"||"}, {"&&"}, {"|"}, {"^"}, {"&"},
    {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"},
    {"+", "-"}, {"*", "/", "%"},
]

BINOP_MAP = {
    "+": "ADD", "-": "SUB", "*": "MUL", "/": "DIV", "%": "REM",
    "&": "AND", "|": "OR", "^": "XOR", "<<": "SLL", ">>": "SRL",
}

KEYWORDS = {"function", "let", "if", "else", "while", "halt", "true", "false", "return"}
BUILTINS = {"print", "read", "readln"}

TEMP_REGS = ["t0", "t1", "t2", "t3", "t4", "t5", "t6"]
NUM_TEMPS = len(TEMP_REGS)

DATA_OFFSET_BASE = 100

IMM11_MIN = -1024
IMM11_MAX = 1023


VAR_REGS = ["s0", "s1", "s2", "s3", "s4", "s5", "s6", "s7", "s8", "s9", "s10", "s11"]

class Condition:
    def __init__(self, op, rs1, rs2):
        self.op = op
        self.rs1 = rs1
        self.rs2 = rs2

class HL:
    def __init__(self):
        self.vars = {}
        self.data_offset = 0
        self.label_counter = 0
        self.asm = []
        self.nreg = 0
        self.data_labels = []

    def _alloc_reg(self):
        reg = TEMP_REGS[self.nreg % NUM_TEMPS]
        self.nreg += 1
        return reg

    def _make_label(self, prefix="L"):
        self.label_counter += 1
        return f"{prefix}_{self.label_counter}"

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
            return
        self._emit(f"SW {reg}, gp, {loc}")

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else ("", "")

    def _advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, *values):
        tok = self._peek()
        if tok[1] in values or tok[0] in values:
            return self._advance()
        raise SyntaxError(f"expected {values}, got {tok[1]} at position {self.pos}")

    def _prec(self, op):
        for i, level in enumerate(PRECEDENCE):
            if op in level:
                return i
        return -1


    def tokenize(self, src):
        self.tokens = []
        pattern = (
            r"//.*"                              # line comment
            r"|0[xX][0-9a-fA-F]+"                # hex literal
            r"|\d+"                               # decimal literal
            r"|'[^'\\]*(?:\\.[^'\\]*)*'"          # char literal
            r"|[a-zA-Z_]\w*"                      # identifier / keyword
            r"|&&|\|\||<<|>>|<=|>=|==|!="         # two-char operators
            r"|[-+*/%&|^~<>=!]=?"                 # single-char operators
            r"|[{}();,]"                           # separators
        )
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
                if len(c) > 1 and c[0] == "\\":
                    escapes = {"n": 10, "t": 9, "r": 13, "0": 0}
                    self.tokens.append(("C", escapes.get(c[1], ord(c[1]))))
                else:
                    self.tokens.append(("C", ord(c)))
            elif t[0].isalpha() or t[0] == "_":
                if t in KEYWORDS:
                    self.tokens.append(("K", t))
                elif t in BUILTINS:
                    self.tokens.append(("B", t))
                else:
                    self.tokens.append(("I", t))
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
        tok = self._peek()
        if tok == ("K", "let"):
            self._parse_let()
        elif tok == ("K", "if"):
            self._parse_if()
        elif tok == ("K", "while"):
            self._parse_while()
        elif tok == ("K", "halt"):
            self._advance()
            self._expect(";")
            self._emit("HALT")
        elif tok == ("K", "return"):
            self._advance()
            if self._peek()[1] != ";":
                r = self._parse_expr(0)
                self._emit(f"MV a0, {self._ensure_reg(r)}")
            self._expect(";")
        elif tok[0] == "S" and tok[1] == "{":
            self._advance()
            while self._peek()[1] != "}":
                self._parse_stmt()
            self._expect("}")
        elif tok[0] == "B":
            self._parse_builtin()
        elif tok[0] == "S" and tok[1] == ";":
            self._advance()
        else:
            self._parse_assign()

    def _parse_let(self):
        self._advance()  # 'let'
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
            # function call statement: name(...)
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
        # addr = (hi << 11) + lo, where lo is 11-bit signed
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
        arg = None
        if self._peek()[1] != ")":
            arg = self._parse_expr(0)
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
        if not isinstance(cond, Condition):
            reg = self._ensure_reg(cond)
            self._emit(f"{'BNEZ' if invert else 'BEQZ'} {reg}, {label}")
            return

        op = cond.op
        rs1, rs2 = cond.rs1, cond.rs2

        # Map of op -> branch mnemonic when we want to jump if condition is FALSE (for BEQZ target)
        branch_map = {
            "==": "BNE", "!=": "BEQ",
            "<": "BGE", ">=": "BLT",
            ">": "BLE", "<=": "BGT",
        }
        if invert:
             branch_map = {
                "==": "BEQ", "!=": "BNE",
                "<": "BLT", ">=": "BGE",
                ">": "BGT", "<=": "BLE",
             }
        self._emit(f"{branch_map[op]} {rs1}, {rs2}, {label}")

    def _parse_if(self):
        self._advance()  # 'if'
        self._expect("(")
        cond = self._parse_expr(0)
        lbl_else = self._make_label("el")
        lbl_end = self._make_label("en")
        self._emit_branch(cond, lbl_else)
        self._expect(")")
        self._parse_stmt()
        self._emit(f"J {lbl_end}")
        self._emit(f"{lbl_else}:")
        if self._peek() == ("K", "else"):
            self._advance()
            self._parse_stmt()
        self._emit(f"{lbl_end}:")

    def _parse_while(self):
        self._advance()
        self._expect("(")
        lbl_start = self._make_label("w")
        lbl_end = self._make_label("ew")
        self._emit(f"{lbl_start}:")
        cond = self._parse_expr(0)
        self._emit_branch(cond, lbl_end)
        self._expect(")")
        self._parse_stmt()
        self._emit(f"J {lbl_start}")
        self._emit(f"{lbl_end}:")

    def _parse_expr(self, min_prec, target_reg=None):
        left = self._parse_primary(target_reg=target_reg if min_prec == 0 else None)
        while True:
            tok = self._peek()
            if tok[0] != "O":
                break
            prec = self._prec(tok[1])
            if prec < 0 or prec < min_prec:
                break
            self._advance()
            right = self._parse_expr(prec + 1)
            left = self._emit_binop(tok[1], left, right, target_reg=target_reg)
        return left

    def _parse_primary(self, target_reg=None):
        tok = self._advance()
        if tok[0] in ("N", "H", "C"):
            if target_reg:
                return self._ensure_reg(tok[1], target_reg=target_reg)
            return tok[1]
        if tok[0] == "K" and tok[1] in ("true", "false"):
            val = 1 if tok[1] == "true" else 0
            if target_reg:
                return self._ensure_reg(val, target_reg=target_reg)
            return val
        if tok[0] == "I":
            if self._peek()[1] == "(":
                fn = tok[1]
                self._advance()
                while self._peek()[1] != ")":
                    self._advance()
                self._expect(")")
                if fn == "read":
                    reg = target_reg if target_reg else self._alloc_reg()
                    port = self._emit_io_addr(IN_PORT)
                    self._emit(f"LW {reg}, {port}, 0")
                    return reg
                return target_reg if target_reg else self._alloc_reg()
            val = self._load_var(tok[1])
            if target_reg and target_reg != val:
                self._emit(f"MV {target_reg}, {val}")
                return target_reg
            return val
        if tok[0] == "S" and tok[1] == "(":
            expr = self._parse_expr(0, target_reg=target_reg)
            self._expect(")")
            return expr
        if tok[0] == "O" and tok[1] in ("-", "~", "!"):
            expr = self._parse_expr(len(PRECEDENCE))
            reg = target_reg if target_reg else self._alloc_reg()
            if tok[1] == "-":
                self._emit(f"SUB {reg}, zero, {self._ensure_reg(expr)}")
            elif tok[1] == "~":
                self._emit(f"XORI {reg}, {self._ensure_reg(expr)}, -1")
            return reg
        return 0

    def _emit_binop(self, op, left, right, target_reg=None):
        # Constant folding
        if isinstance(left, int) and isinstance(right, int):
            return self._fold(op, left, right)

        if op in ("<", ">", "<=", ">=", "==", "!="):
             lr = self._ensure_reg(left)
             rr = self._ensure_reg(right)
             return Condition(op, lr, rr)

        # Optimization: Try immediate instructions if right is a constant
        if isinstance(right, int) and IMM11_MIN <= right <= IMM11_MAX:
            lr = self._ensure_reg(left)
            result = target_reg if target_reg else self._alloc_reg()
            if op == "+":
                self._emit(f"ADDI {result}, {lr}, {right}")
                return result
            if op == "-" and IMM11_MIN <= -right <= IMM11_MAX:
                self._emit(f"ADDI {result}, {lr}, {-right}")
                return result
            if op == "&":
                self._emit(f"ANDI {result}, {lr}, {right}")
                return result
            if op == "|":
                self._emit(f"ORI {result}, {lr}, {right}")
                return result
            if op == "^":
                self._emit(f"XORI {result}, {lr}, {right}")
                return result
            if op == "<<":
                self._emit(f"SLLI {result}, {lr}, {right}")
                return result
            if op == ">>":
                self._emit(f"SRLI {result}, {lr}, {right}")
                return result

        lr = self._ensure_reg(left)
        rr = self._ensure_reg(right)
        result = target_reg if target_reg else self._alloc_reg()

        if op in BINOP_MAP:
            self._emit(f"{BINOP_MAP[op]} {result}, {lr}, {rr}")
        return result

    def _ensure_reg(self, val, target_reg=None):
        if isinstance(val, Condition):
             result = target_reg if target_reg else self._alloc_reg()
             op, lr, rr = val.op, val.rs1, val.rs2
             if op == "<":
                 self._emit(f"SLT {result}, {lr}, {rr}")
             elif op == ">":
                 self._emit(f"SLT {result}, {rr}, {lr}")
             elif op == "<=":
                 self._emit(f"SLT {result}, {rr}, {lr}")
                 self._emit(f"XORI {result}, {result}, 1")
             elif op == ">=":
                 self._emit(f"SLT {result}, {lr}, {rr}")
                 self._emit(f"XORI {result}, {result}, 1")
             elif op == "==":
                 self._emit(f"SUB {result}, {lr}, {rr}")
                 t1, t2 = self._alloc_reg(), self._alloc_reg()
                 self._emit(f"SLT {t1}, zero, {result}")
                 self._emit(f"SLT {t2}, {result}, zero")
                 self._emit(f"OR {result}, {t1}, {t2}")
                 self._emit(f"XORI {result}, {result}, 1")
             elif op == "!=":
                 self._emit(f"SUB {result}, {lr}, {rr}")
                 t1, t2 = self._alloc_reg(), self._alloc_reg()
                 self._emit(f"SLT {t1}, zero, {result}")
                 self._emit(f"SLT {t2}, {result}, zero")
                 self._emit(f"OR {result}, {t1}, {t2}")
             return result

        if val == 0:
            if target_reg:
                self._emit(f"MV {target_reg}, zero")
                return target_reg
            return "zero"
        if isinstance(val, int):
            reg = target_reg if target_reg else self._alloc_reg()
            if IMM11_MIN <= val <= IMM11_MAX:
                self._emit(f"ADDI {reg}, zero, {val}")
            else:
                # Correct two-instruction sequence for 32-bit constants
                # LUI shifts left by 11. ADDI adds a 11-bit signed immediate.
                lo = val & 0x7FF
                if lo >= 0x400:
                    lo -= 0x800
                hi = (val - lo) >> 11
                self._emit(f"LUI {reg}, {hi & IMM21_MASK}")
                if lo:
                    self._emit(f"ADDI {reg}, {reg}, {lo}")
            return reg
        return val

    def _fold(self, op, a, b):
        return {
            "+": a + b, "-": a - b, "*": a * b,
            "/": a // b if b else 0, "%": a % b if b else 0,
            "&": a & b, "|": a | b, "^": a ^ b,
            "<<": a << b, ">>": a >> b,
            "<": 1 if a < b else 0, ">": 1 if a > b else 0,
            "<=": 1 if a <= b else 0, ">=": 1 if a >= b else 0,
            "==": 1 if a == b else 0, "!=": 1 if a != b else 0,
        }.get(op, 0)

    def _finish(self):
        if self.vars:
            self.asm.append("")
            self.asm.append(f".org {self.data_offset + DATA_OFFSET_BASE}")
            for name in sorted(self.vars, key=lambda n: self.vars[n]):
                if isinstance(self.vars[name], int):
                     self.asm.append(f"    .word 0  ; {name}")
        return "    .org 0\n" + "\n".join(self.asm)
