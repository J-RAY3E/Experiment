# Implementation Plan — NoComplex_Experiment

## Objetivo

Rediseñar el microcontrolador para que sea más simple, realista y educativo:

- FETCH en **2 ticks** (separar acceso a memoria de decode/dispatch)
- **1 tick de ejecución** por instrucción (R, I, U, J, JAL, JR, LUI, NOP, HALT)
- **SW/SB en 1 tick** (no 2 como ahora)
- **LW/LB en 2 ticks** (L_EX + L_WB)
- **Branch en 2 ticks** (B_EX + B_WB con PC-relative)
- **Sin extensión vectorial** (eliminar VADD, VSUB, VMUL, VDIV, VCMP, VLD, VST)
- **µROM entries como números hex/binarios**, sin campos simbólicos
- **Saltos PC-relative** (J, JAL, branches)
- **Eliminar señal `pc_inc`** (innecesaria)

---

## 1. FETCH en 2 ticks

### Estado actual (1 tick)

```
Tick N:   FETCH  →  IR = mem[PC], PC += 4, decode, dispatch
```

### Estado nuevo (2 ticks)

```
Tick N:   FETCH_ADDR  →  MAR = PC, iniciar lectura de IMEM
Tick N+1: FETCH_WB    →  IR = MDR(IMEM), PC += 4, decode, dispatch
```

**Cambios:**

| Archivo | Cambio |
|---------|--------|
| `src/control_path.py` | Nueva entry `F_ADDR` (br_type=0 → `F_WB`) y `F_WB` (br_type=2 → DISPATCH) |
| | `F_ADDR`: `mar_we=True, br_type=0` |
| | `F_WB`: `ir_we=True, br_type=2` |
| `src/data_path.py` | `dp.tick()`: cuando `mi.ir_we=True` ya no hace `pc_inc` (se elimina esa señal) |
| | `F_ADDR`: `mar_we` → MAR = PC (desde a_sel=A_PC) |
| | `F_WB`: `ir_we` → IR = MDR, PC depende de nueva lógica |

### Manejo de PC

Actualmente `pc_inc` incrementa PC automáticamente en FETCH. Ahora:

| Instrucción | Dónde se actualiza PC |
|------------|----------------------|
| R, I, U, LUI, NOP | En `F_WB`: `PC = PC + 4` (hardcoded, sin señal) |
| J | `PC = PC + imm26` en J_EX (relativo) |
| JAL | `PC = PC + imm21` en JAL_EX2, rd = PC+4 en JAL_EX1 |
| JR | `PC = rs1 + imm` en JR_EX |
| Branch | En B_EX: `PC = PC + imm_s` si condición verdadera, si no `PC = PC + 4` |
| HALT | No cambia PC |

Se elimina `pc_inc` del `MI` y de `DataPath.tick()`.

---

## 2. µROM reorganizada (solo scalar)

### Nuevo layout

| µPC | Nombre | br_type | addr | Descripción |
|-----|--------|---------|------|-------------|
| `00` | F_ADDR | 0 | — | MAR = PC, inicia lectura IMEM |
| `01` | F_WB | 2 | — | IR = MDR, PC+=4, dispatch |
| `02` | R_EX | 3 | — | rd = rs1 OP rs2 |
| `03` | I_EX | 3 | — | rd = rs1 OP imm |
| `04` | L_EX | 0 | — | MAR = rs1 + imm, mem_rd |
| `05` | L_WB | 3 | — | rd = MDR |
| `06` | S_EX | 3 | — | mem[MAR] = rs2 (MAR ya listo) |
| `07` | B_EX | 3 | — | Compara rs1, rs2; si condición: PC = PC + imm |
| `08` | J_EX | 3 | — | PC = PC + imm26 |
| `09` | JAL_EX1 | 1→0B | — | rd = PC (retorno) |
| `0A` | JAL_EX2 | 3 | — | PC = PC + imm21 |
| `0B` | JR_EX | 3 | — | PC = rs1 + imm |
| `0C` | U_EX | 3 | — | rd = imm20 << 12 |
| `0D` | NOP_EX | 3 | — | no op |
| `0E` | HALT_EX | 3 | — | halt = True |

### Entries como números hex

Cada `MI` se representa como un entero hex de 32 bits (el `mir_word`). Ejemplo:

```python
# MIR word layout (bits):
# 0: ir_we, 1: pc_inc(ELIMINADO), 2: pc_src
# 5-6: a_sel, 7-8: b_sel, 9: alu_exec
# 10: mar_we, 11: mem_rd, 12: mem_wr, 13: mem_byte
# 14: reg_we, 15-17: reg_src
# 19: halt
# 20-21: br_type, 22-29: addr

_UROM = [
    0x00000000,  # 00 F_ADDR
    0x00000000,  # 01 F_WB
    0x00000000,  # 02 R_EX
    0x00000000,  # 03 I_EX
    0x00000000,  # 04 L_EX
    0x00000000,  # 05 L_WB
    0x00000000,  # 06 S_EX
    0x00000000,  # 07 B_EX
    0x00000000,  # 08 J_EX
    0x00000000,  # 09 JAL_EX1
    0x00000000,  # 0A JAL_EX2
    0x00000000,  # 0B JR_EX
    0x00000000,  # 0C U_EX
    0x00000000,  # 0D NOP_EX
    0x00000000,  # 0E HALT_EX
]
```

Se necesita un **diccionario de mapeo** para convertir de nombre a valor hex:

```python
MIR_MAP = {
    "ir_we":      1 << 0,
    "pc_src":     1 << 2,
    "a_pc":       2 << 5,
    "a_rs1":      1 << 5,
    "b_imm":      2 << 7,
    "b_rs2":      1 << 7,
    "b_zero":     3 << 7,
    "alu_exec":   1 << 9,
    "mar_we":     1 << 10,
    "mem_rd":     1 << 11,
    "mem_wr":     1 << 12,
    "mem_byte":   1 << 13,
    "reg_we":     1 << 14,
    "reg_alu":    1 << 15,
    "reg_mem":    2 << 15,
    "reg_pc":     3 << 15,
    "reg_imm20":  4 << 15,
    "reg_imm26":  5 << 15,
    "reg_imm21":  6 << 15,
    "halt":       1 << 19,
    "br_seq":     0 << 20,  # br_type=0 → µPC+1
    "br_addr":    1 << 20,  # br_type=1 → µPC = addr
    "br_disp":    2 << 20,  # br_type=2 → DISPATCH
    "br_fetch":   3 << 20,  # br_type=3 → µPC=0
}
```

---

## 3. DISPATCH actualizado

```python
DISPATCH = {
    "ADD": 2, "SUB": 2, "MUL": 2, "DIV": 2, "REM": 2,
    "MULH": 2, "AND": 2, "OR": 2, "XOR": 2, "NOT": 2,
    "SLL": 2, "SRL": 2, "SRA": 2, "SLT": 2, "NOP": 0x0D,
    "ADDI": 3, "ANDI": 3, "ORI": 3, "XORI": 3,
    "SLLI": 3, "SRLI": 3, "SRAI": 3, "SLTI": 3,
    "LW": 4, "LB": 4,
    "SW": 6, "SB": 6,
    "BEQ": 7, "BNE": 7, "BLT": 7, "BGE": 7,
    "BGT": 7, "BLE": 7, "BGTU": 7, "BLEU": 7, "BLTU": 7, "BGEU": 7,
    "J": 8,
    "JAL": 9,
    "JR": 0x0B,
    "LUI": 0x0C,
    "HALT": 0x0E,
}
```

---

## 4. ALU dinámica vs hardcodeada

Actualmente cada instrucción R tiene su propia µROM entry con `alu_op` hardcodeado (ADD→1, SUB→1C, etc.). En el nuevo diseño:

**Opción A:** Una sola µROM entry `R_EX` (µPC=02) que usa `decode(IR)` para determinar la operación ALU dinámicamente.

```python
# data_path.py
if mi.alu_exec:
    alu_op = decode(ir)["name"]  # "ADD", "SUB", etc.
    self.alu_out = self.alu.execute(alu_op, self.a, self.b)
```

**Opción B:** Mantener entries separadas pero con el `alu_op` codificado en el MIR.

Recomiendo **Opción A** por simplicidad — toda R-format comparte µPC=02.

---

## 5. LW/LB en 2 ticks

| µPC | Micro | Signals |
|-----|-------|---------|
| 04 | L_EX | `a_sel=A_RS1, b_sel=B_IMM, alu_exec, alu_op=ADD, mar_we, mem_rd` (+ `mem_byte` si LB), `br_type=0` |
| 05 | L_WB | `reg_we, reg_src=REG_MEM, br_type=3` |

**Cambio clave:** La lectura de memoria (`mem_rd`) ocurre en el **mismo tick** que `mar_we` — se asume memoria síncrona que devuelve el dato en el mismo ciclo (como BRAM con read-during-write). Si no es realista, se puede añadir un tick de espera.

---

## 6. SW/SB en 1 tick

| µPC | Micro | Signals |
|-----|-------|---------|
| 06 | S_EX | `mar_we?(no, MAR ya está), mem_wr, br_type=3` |

Wait — para SW necesitamos MAR = rs1 + imm. Si no hay un tick previo, necesitamos calcular MAR en el mismo tick.

| µPC | Micro | Signals |
|-----|-------|---------|
| 06 | S_EX | `a_sel=A_RS1, b_sel=B_IMM, alu_exec, alu_op=ADD, mar_we, mem_wr, br_type=3` |

Esto funciona si `mar_we` y `mem_wr` ocurren en el mismo tick (MAR se calcula y se usa inmediatamente para la dirección de memoria). Asumimos forwarding interno.

---

## 7. Branch en 2 ticks (si es necesario)

Opción A: 1 tick (B_EX):

| µPC | Micro | Signals |
|-----|-------|---------|
| 07 | B_EX | Compara rs1, rs2; si condición: `PC = PC + imm`; si no: `PC = PC + 4`, `br_type=3` |

Esto requiere que la comparación y el cálculo de `PC + imm` ocurran en el mismo tick. Es posible si el comparator y el adder están en paralelo.

Opción B: 2 ticks:

| µPC | Micro | Signals |
|-----|-------|---------|
| 07 | B_EX | Compara rs1, rs2, `br_type=0` |
| 08 | B_WB | `pc_src` con PC+imm o PC+4 según resultado, `br_type=3` |

Por ahora, evaluar si la **Opción A** es viable (depende de la ruta crítica).

---

## 8. Saltos PC-relative

### J (Jump)

```python
# encode
imm26 = (target - PC - 4)  & IMM26_MASK  # offset relativo
return (opcode << 26) | imm26

# µROM J_EX (µPC=08)
a_sel=A_PC, b_sel=B_IMM, alu_exec, alu_op=ADD, pc_src=True
```

### JAL (Jump and Link)

```python
# encode
imm21 = (target - PC - 4) & IMM21_MASK

# JAL_EX1 (µPC=09): rd = PC (retorno)
reg_we=True, reg_src=REG_PC, br_type=1, addr=0x0A

# JAL_EX2 (µPC=0A): PC = PC + imm21
a_sel=A_PC, b_sel=B_IMM, alu_exec, alu_op=ADD, pc_src=True
```

---

## 9. Eliminar vector extension

### Archivos afectados

| Archivo | Cambio |
|---------|--------|
| `src/isa.py` | Eliminar `V_FORMAT`, `VL_FORMAT`, opcodes VADD..VST, `NUM_VREGS`, `VLANES` |
| `src/control_path.py` | Eliminar entries 0D-1B (V_EX, VLD_EX, VST_EX1, VLD_W0..W3, VST_W0..W3), actualizar DISPATCH |
| `src/data_path.py` | Eliminar `VectorRegisterFile`, `valu_exec`, `v_reg_we`, `v_reg_src`, `lane_sel`, `mem_data_src`, `vbase`, `addr_sel`, `vbase_we`, `vbase_sel` de `MI` y `DataPath` |
| `src/translator.py` | Eliminar `V_FORMAT`, `VLD`, `VST` de `encode()` |
| `src/hl_logic.py` | Eliminar `VREGS`, `vload`, `vadd`, `vstore`, `VBM`, `av()`, vector ops en `_eb()` |

---

## 10. Actualizar `mir_word` layout

Eliminar bits de vector y pc_inc, compactar:

| Bit | Señal | Descripción |
|-----|-------|-------------|
| 0 | `ir_we` | Escribir IR |
| 1 | *(libre)* | Antes era pc_inc |
| 2 | `pc_src` | PC = feedback_bus |
| 3-4 | `a_sel` | 0=NONE, 1=RS1, 2=PC |
| 5-6 | `b_sel` | 0=NONE, 1=RS2, 2=IMM, 3=ZERO |
| 7 | `alu_exec` | Ejecutar ALU |
| 8 | `mar_we` | MAR = ALU_out |
| 9 | `mem_rd` | Leer memoria |
| 10 | `mem_wr` | Escribir memoria |
| 11 | `mem_byte` | Acceso byte (no word) |
| 12 | `reg_we` | Escribir registro |
| 13-15 | `reg_src` | 1=ALU, 2=MEM, 3=PC, 4=IMM20<<12, 5=IMM26, 6=IMM21 |
| 16 | `halt` | Detener |
| 17-18 | `br_type` | 0=seq, 1=addr, 2=disp, 3=fetch |
| 19-26 | `addr` | Dirección de salto (br_type=1) |

---

## 11. Tabla de traducción de µROM entries a hex

### Cálculo de MIR word por entry

```
MIR = (ir_we << 0) | (pc_src << 2) | (a_sel << 3) | (b_sel << 5) |
      (alu_exec << 7) | (mar_we << 8) | (mem_rd << 9) | (mem_wr << 10) |
      (mem_byte << 11) | (reg_we << 12) | (reg_src << 13) | (halt << 16) |
      (br_type << 17) | (addr << 19)
```

| Entry | Señales | MIR (hex) |
|-------|---------|-----------|
| F_ADDR | a_sel=PC(2), mar_we, br_type=seq(0) | `00000300` |
| F_WB | ir_we, br_type=disp(2) | `00040001` |
| R_EX | a_sel=RS1(1), b_sel=RS2(1), alu_exec, reg_we, reg_src=ALU(1), br_type=fetch(3) | `000620A8` |
| I_EX | a_sel=RS1(1), b_sel=IMM(2), alu_exec, reg_we, reg_src=ALU(1), br_type=fetch(3) | `000630A8` |
| L_EX | a_sel=RS1(1), b_sel=IMM(2), alu_exec, mar_we, mem_rd, br_type=seq(0) | `00033300` |
| L_WB | reg_we, reg_src=MEM(2), br_type=fetch(3) | `00061000` |
| S_EX | a_sel=RS1(1), b_sel=IMM(2), alu_exec, mar_we, mem_wr, br_type=fetch(3) | `00063200` |
| B_EX | a_sel=PC(2), b_sel=IMM(2), alu_exec, pc_src, br_type=fetch(3) | `00063004` |
| J_EX | a_sel=PC(2), b_sel=IMM(2), alu_exec, pc_src, br_type=fetch(3) | `00063004` |
| JAL_EX1 | reg_we, reg_src=PC(3), br_type=addr(1), addr=0x0A | `000B200A` |
| JAL_EX2 | a_sel=PC(2), b_sel=IMM(2), alu_exec, pc_src, br_type=fetch(3) | `00063004` |
| JR_EX | a_sel=RS1(1), b_sel=IMM(2), alu_exec, pc_src, br_type=fetch(3) | `00023004` |
| U_EX | reg_we, reg_src=IMM20(4), br_type=fetch(3) | `000C1000` |
| NOP_EX | br_type=fetch(3) | `00060000` |
| HALT_EX | halt, br_type=fetch(3) | `00060001` |

Wait — los valores hex de arriba están mal calculados. Necesito recalcularlos con el layout de bits correcto. Esto se hará en la implementación usando el `MIR_MAP`.

---

## 12. Archivos a modificar

| Archivo | Cambios |
|---------|---------|
| `src/control_path.py` | Reescribir completo: nuevo µROM como `list[int]`, `DISPATCH`, `MIR_MAP`, eliminar clase `MI`, `ControlPath.current_mi()` retorna `int` (MIR word) |
| `src/data_path.py` | Eliminar `VectorRegisterFile`, `v*` señales, `valu_exec`, `v_reg_we`, etc. Actualizar `DataPath.tick()` para recibir `mi: int` y usar `MIR_MAP` para decodificar señales |
| `src/isa.py` | Eliminar opcodes vectoriales, `V_FORMAT`, `VL_FORMAT`, `NUM_VREGS`, `VLANES`. Actualizar `encode()` para saltos PC-relative |
| `src/translator.py` | Eliminar `V_FORMAT`, `VLD`, `VST` de `encode()`. Actualizar J/JAL encode para PC-relative |
| `src/machine.py` | Eliminar `v*` references. Actualizar `tick()` para nuevo FETCH de 2 ticks |
| `src/hl_logic.py` | Eliminar `VREGS`, `VBM`, `vload`, `vadd`, `vstore`, `av()`, código vectorial |
| `tests/test_golden.py` | Actualizar goldens con nuevo formato de journal |
| `golden/*.yaml` | Regenerar todos con nuevo diseño |

---

## 13. Orden de implementación

1. `src/control_path.py` — Nuevo µROM como `list[int]`, MIR_MAP, DISPATCH sin vector
2. `src/isa.py` — Eliminar vector, actualizar encode() para PC-relative J/JAL
3. `src/data_path.py` — Eliminar vector, actualizar tick() para nuevo MI como int
4. `src/machine.py` — FETCH de 2 ticks, eliminar vector
5. `src/translator.py` — Eliminar vector, PC-relative J/JAL
6. `src/hl_logic.py` — Eliminar vector
7. Probar con tests existentes, depurar
8. Regenerar goldens
9. Verificar CI (ruff, mypy, pytest)

---

## 14. Notas sobre el diseño

- **ALU dinámica**: R_EX e I_EX usan `decode(IR)["name"]` para determinar la operación ALU (ADD/SUB/MUL/etc.), no hay entries separadas por instrucción
- **SW/SB en 1 tick**: `mar_we` y `mem_wr` se activan juntos — MAR se calcula y se usa como dirección en el mismo ciclo. La memoria debe soportar read-during-write o tener forwarding interno
- **Branch en 1 tick**: El comparator evalúa rs1 vs rs2, y si la condición se cumple, se actualiza PC. Todo en paralelo en el mismo tick
- **J/JAL JR encode**: El assembler calcula `target - PC - 4` como offset, no dirección absoluta
- **`pc_inc` eliminado**: El PC se actualiza explícitamente: +4 en F_WB, o por pc_src en saltos
