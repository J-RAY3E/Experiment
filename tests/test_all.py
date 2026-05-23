import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.assembler import assemble
from src.hl import HL

tests = {
    "sum": '''
function main() {
    let a = 5;
    let b = 7;
    let c = a + b;
    print(c + 48);
    halt;
}
''',
    "countdown": '''
function main() {
    let i = 5;
    while (i > 0) {
        print(i + 48);
        i = i - 1;
    }
    halt;
}
''',
    "hello": '''
function main() {
    print(72);   // H
    print(101);  // e
    print(108);  // l
    print(108);  // l
    print(111);  // o
    print(10);   // newline
    halt;
}
''',
    "ifelse": '''
function main() {
    let x = 10;
    if (x > 5) {
        print(89);   // Y
    } else {
        print(78);   // N
    }
    halt;
}
''',
    "math": '''
function main() {
    let a = 20;
    let b = 6;
    let sum = a + b;
    let diff = a - b;
    let prod = a * b;
    let quot = a / b;
    print(sum + 48);
    print(diff + 48);
    print(prod + 48);
    print(quot + 48);
    halt;
}
''',
}

passes = fails = 0
for name, src in tests.items():
    print(f"\n=== {name} ===")
    asm = HL().run(src)
    try:
        data, lst = assemble(asm)
        n = len(data) // 4
        print(f"  OK: {n} instructions")
        for line in lst:
            print(f"    {line}")
        passes += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        fails += 1

print(f"\n{passes}/{passes+fails} passed")
sys.exit(0 if fails == 0 else 1)
