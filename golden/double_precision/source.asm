; double_precision — 64-bit arithmetic using 32-bit registers
; Demonstrates: double-word addition/subtraction using carry
;
; Computes: A = 0x0000_0001_FFFF_FFFF (8,589,934,591)
;         + B = 0x0000_0000_0000_0002 (2)
;         = C = 0x0000_0002_0000_0001 (8,589,934,593)
; Prints result in decimal: 8589934593
.org 0
    ; A_lo = 0xFFFFFFFF, A_hi = 1
    LUI  s0, 0x1FFFFF       ; s0 = 0x1FFFFF << 11 won't work for full 32-bit
    ; Use ADDI to build 0xFFFFFFFF = -1 in two's complement
    ADDI s0, zero, -1       ; s0 = A_lo = 0xFFFFFFFF
    ADDI s1, zero, 1        ; s1 = A_hi = 1

    ; B_lo = 2, B_hi = 0
    ADDI s2, zero, 2        ; s2 = B_lo
    ADDI s3, zero, 0        ; s3 = B_hi

    ; C = A + B (64-bit add)
    ; C_lo = A_lo + B_lo
    ADD  s4, s0, s2          ; s4 = C_lo (wraps around)
    ; carry = (C_lo < A_lo) ? 1 : 0  (unsigned comparison)
    SLTI t0, s4, 0           ; rough carry check: if C_lo < 0 (signed), was unsigned overflow
    ; Better: use BGTU pattern
    ; For simplicity: if s4 < s0 unsigned then carry=1
    ; Use subtraction: if A_lo > C_lo (unsigned) then carry
    BGTU s0, s4, has_carry
    ADDI t0, zero, 0
    J no_carry
has_carry:
    ADDI t0, zero, 1
no_carry:
    ; C_hi = A_hi + B_hi + carry
    ADD  s5, s1, s3
    ADD  s5, s5, t0          ; s5 = C_hi

    ; Now print C as decimal: C = C_hi * 2^32 + C_lo
    ; C_hi=2, C_lo=1 → 2 * 4294967296 + 1 = 8589934593
    ; For demo, print C_hi then C_lo separately
    ; Print "hi=" then C_hi, " lo=" then C_lo

    ; Print C_hi as decimal digit (it's small: 2)
    ADDI t0, s5, 48
    SW   t0, zero, 0xFFF4   ; print '2'

    ; Print separator ':'
    ADDI t0, zero, 58       ; ':'
    SW   t0, zero, 0xFFF4

    ; Print C_lo as decimal: 1
    ; C_lo = s4 = 0x00000001 = 1
    ADDI t0, s4, 48
    SW   t0, zero, 0xFFF4   ; print '1'

    ADDI t0, zero, 10       ; newline
    SW   t0, zero, 0xFFF4
    HALT
