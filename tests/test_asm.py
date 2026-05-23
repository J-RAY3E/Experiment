import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.assembler import assemble

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def write_bin(src, bin_path, lst_path):
    data, lst = assemble(src)
    with open(bin_path, "wb") as f:
        f.write(data)
    with open(lst_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lst))
    return len(data) // 4, lst

tests = {
    "sum": """
.org 0
start:
    LW r1, gp, 0
    LW r2, gp, 1
    ADD r3, r1, r2
    SW r3, gp, 2
    ADDI r4, r3, 48
    SW r4, zero, 0xFFF4
    HALT
.org 100
    .word 12
    .word 30
    .word 0
""",
    "countdown": """
.org 0
    LI r1, 5
loop:
    BEQZ r1, end
    ADDI r2, r1, 48
    SW r2, zero, 0xFFF4
    ADDI r1, r1, -1
    J loop
end:
    LI r3, 10
    SW r3, zero, 0xFFF4
    HALT
""",
    "pstr": """
.org 0
    LUI r1, 0
    LW r2, r1, 0
    LI r3, 0
loop:
    BLT r3, r2, body
    J end
body:
    ADDI r4, r1, 1
    ADD r5, r4, r3
    LW r6, r5, 0
    SW r6, zero, 0xFFF4
    ADDI r3, r3, 1
    J loop
end:
    HALT
.org 0
    .string "Hi!"
""",
}

passes = fails = 0
for name, src in tests.items():
    lst = []
    try:
        n, lst = write_bin(src, f"tests/{name}.bin", f"tests/{name}.lst")
        print(f"  OK  {name}: {n} instructions")
        passes += 1
    except Exception as e:
        print(f"  FAIL {name}: {e}")
        fails += 1
    for line in lst:
        print(f"    {line}")

print(f"\n{passes}/{passes+fails} passed")
sys.exit(0 if fails == 0 else 1)
