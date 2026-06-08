    .org 0
    J main
    .org 4
data_start:
    .word 0  ; dummy
    .org 8
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    wc_1:
    ADDI t0, zero, 10
    BGE s0, t0, en_2
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, s0, 48
    SW t2, t1, 0
    ADDI s0, s0, 1
    J wc_1
    en_2:
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 10
    SW t4, t3, 0
    HALT