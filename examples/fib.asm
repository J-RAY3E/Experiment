    .org 0
    J main
    .org 4
data_start:
    .word 0  ; dummy
    .org 8
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    ADDI s1, zero, 1
    MV s2, zero
    wc_1:
    ADDI t0, zero, 10
    BGE s2, t0, en_2
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, s0, 48
    SW t2, t1, 0
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 32
    SW t4, t3, 0
    ADD s3, s0, s1
    MV s0, s1
    MV s1, s3
    ADDI s2, s2, 1
    J wc_1
    en_2:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    HALT