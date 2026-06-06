    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    ADDI s0, zero, 10
    ADDI s1, zero, 20
    ADD s2, s0, s1
    ADDI t0, s2, 48
    LUI t1, 0
    ADDI t1, t1, -12
    SW t0, t1, 0
    ADDI t2, zero, 10
    LUI t3, 0
    ADDI t3, t3, -12
    SW t2, t3, 0
    HALT