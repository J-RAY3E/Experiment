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
from src.ISA import IN_PORT, OUT_PORT, IMM11_MASK, IMM21_MASK

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


    def _var_addr(self, name):
        if name not in self.vars:
            self.vars[name] = self.data_offset
            self.data_offset += 1
        return self.vars[name]

    def _load_var(self, name):
        reg = self._alloc_reg()
        self._emit(f"LW {reg}, gp, {self._var_addr(name)}")
        return reg

    def _store_var(self, name, reg):
        self._emit(f"SW {reg}, gp, {self._var_addr(name)}")

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
                    self.tokens.append(("C", {"n": 10, "t": 9, "r": 13, "0": 0}.get(c[1], ord(c[1]))))
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
        if self._peek()[1] == "=":
            self._advance()
            r = self._parse_expr(0)
            self._store_var(name, self._ensure_reg(r))
        else:
            self._var_addr(name)  # just allocate
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
            r = self._parse_expr(0)
            self._store_var(name, self._ensure_reg(r))
            self._expect(";")

    def _emit_io_addr(self, addr):
        reg = self._alloc_reg()
        upper = (addr >> 11) & IMM21_MASK
        lower = addr & IMM11_MASK
        if lower > IMM11_MAX:
            lower -= (IMM11_MASK + 1)
            upper += 1
        self._emit(f"LUI {reg}, {upper}")
        if lower:
            self._emit(f"ADDI {reg}, {reg}, {lower}")
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
            reg = self._alloc_reg()
            port = self._emit_io_addr(IN_PORT)
            self._emit(f"LW {reg}, {port}, 0")

    def _parse_if(self):
        self._advance()  # 'if'
        self._expect("(")
        cond = self._parse_expr(0)
        cond = self._ensure_reg(cond)
        lbl_else = self._make_label("el")
        lbl_end = self._make_label("en")
        self._emit(f"BEQZ {cond}, {lbl_else}")
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
        cond = self._ensure_reg(cond)
        self._emit(f"BEQZ {cond}, {lbl_end}")
        self._expect(")")
        self._parse_stmt()
        self._emit(f"J {lbl_start}")
        self._emit(f"{lbl_end}:")

    def _parse_expr(self, min_prec):
        left = self._parse_primary()
        while True:
            tok = self._peek()
            if tok[0] != "O":
                break
            prec = self._prec(tok[1])
            if prec < 0 or prec < min_prec:
                break
            self._advance()
            right = self._parse_expr(prec + 1)
            left = self._emit_binop(tok[1], left, right)
        return left

    def _parse_primary(self):
        tok = self._advance()
        if tok[0] in ("N", "H", "C"):
            return tok[1]
        if tok[0] == "K" and tok[1] in ("true", "false"):
            return 1 if tok[1] == "true" else 0
        if tok[0] == "I":
            if self._peek()[1] == "(":
                fn = tok[1]
                self._advance()
                while self._peek()[1] != ")":
                    self._advance()
                self._expect(")")
                if fn == "read":
                    reg = self._alloc_reg()
                    port = self._emit_io_addr(IN_PORT)
                    self._emit(f"LW {reg}, {port}, 0")
                    return reg
                return self._alloc_reg()
            return self._load_var(tok[1])
        if tok[0] == "S" and tok[1] == "(":
            expr = self._parse_expr(0)
            self._expect(")")
            return expr
        if tok[0] == "O" and tok[1] in ("-", "~", "!"):
            expr = self._parse_expr(len(PRECEDENCE))
            reg = self._alloc_reg()
            if tok[1] == "-":
                self._emit(f"SUB {reg}, zero, {self._ensure_reg(expr)}")
            elif tok[1] == "~":
                self._emit(f"XORI {reg}, {self._ensure_reg(expr)}, -1")
            return reg
        return 0

    def _emit_binop(self, op, left, right):
        # Constant folding
        if isinstance(left, int) and isinstance(right, int):
            return self._fold(op, left, right)

        lr = self._ensure_reg(left)
        rr = self._ensure_reg(right)
        result = self._alloc_reg()

        if op in BINOP_MAP:
            self._emit(f"{BINOP_MAP[op]} {result}, {lr}, {rr}")
        elif op == "<":
            self._emit(f"SLT {result}, {lr}, {rr}")
        elif op == ">":
            self._emit(f"SLT {result}, {rr}, {lr}")
        elif op == "<=":
            lbl = self._make_label("le")
            self._emit(f"SLT {result}, {rr}, {lr}")
            self._emit(f"BEQZ {result}, {lbl}")
            self._emit(f"ADDI {result}, zero, 0")
            self._emit(f"{lbl}: ADDI {result}, {result}, 1")
        elif op == ">=":
            lbl = self._make_label("ge")
            self._emit(f"SLT {result}, {lr}, {rr}")
            self._emit(f"BEQZ {result}, {lbl}")
            self._emit(f"ADDI {result}, zero, 0")
            self._emit(f"{lbl}: ADDI {result}, {result}, 1")
        elif op == "==":
            lbl = self._make_label("eq")
            self._emit(f"SUB {result}, {lr}, {rr}")
            self._emit(f"BNEZ {result}, {lbl}")
            self._emit(f"ADDI {result}, zero, 1")
            self._emit(f"J {lbl}_s")
            self._emit(f"{lbl}: ADDI {result}, zero, 0")
            self._emit(f"{lbl}_s:")
        elif op == "!=":
            lbl = self._make_label("ne")
            self._emit(f"SUB {result}, {lr}, {rr}")
            self._emit(f"BEQZ {result}, {lbl}")
            self._emit(f"ADDI {result}, zero, 1")
            self._emit(f"J {lbl}_s")
            self._emit(f"{lbl}: ADDI {result}, zero, 0")
            self._emit(f"{lbl}_s:")
        return result

    def _ensure_reg(self, val):
        if isinstance(val, int):
            reg = self._alloc_reg()
            if IMM11_MIN <= val <= IMM11_MAX:
                self._emit(f"ADDI {reg}, zero, {val}")
            elif 0 <= val <= IMM21_MASK:
                self._emit(f"LUI {reg}, {val}")
            else:
                upper = (val >> 11) & IMM21_MASK
                lower = val & IMM11_MASK
                if lower > IMM11_MAX:
                    lower -= (IMM11_MASK + 1)
                    upper += 1
                self._emit(f"LUI {reg}, {upper}")
                self._emit(f"ADDI {reg}, {reg}, {lower}")
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
                self.asm.append(f"    .word 0  ; {name}")
        return "    .org 0\n" + "\n".join(self.asm)
