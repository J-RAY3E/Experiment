; Compute-bound scalar benchmark
; 1024 iterations × 4 elements: LW + ADDI + SW per element (12 instructions per iter)
    .org 0
    ADDI s0, zero, 200
    ADDI t0, zero, 1024
    ADDI s1, zero, 0
loop:
    LW   t1, s0, 0
    ADDI t1, t1, 1
    SW   t1, s0, 0
    LW   t2, s0, 4
    ADDI t2, t2, 1
    SW   t2, s0, 4
    LW   t3, s0, 8
    ADDI t3, t3, 1
    SW   t3, s0, 8
    LW   t4, s0, 12
    ADDI t4, t4, 1
    SW   t4, s0, 12
    ADDI s1, s1, 1
    BLT  s1, t0, loop
    HALT
    .org 200
    .word 0
    .word 0
    .word 0
    .word 0
