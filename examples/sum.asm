    .org 0
    J main
    .org 4
data_start:
    .word 0  ; dummy
    .org 8
    main:
    ADDI gp, zero, data_start
    ADDI s0, zero, 10
    ADDI s1, zero, 20
    ADD s2, s0, s1
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, s2, 48
    SW t1, t0, 0
    LUI t2, 0
    ADDI t2, t2, -12
    ADDI t3, zero, 10
    SW t3, t2, 0
    HALT