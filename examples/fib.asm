    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    ADDI s1, zero, 1
    MV s2, zero
    w_1:
    ADDI t0, zero, 10
    BGE s2, t0, ew_2
    ADDI t1, s0, 48
    LUI t2, 0
    ADDI t2, t2, -12
    SW t1, t2, 0
    ADDI t3, zero, 32
    LUI t4, 0
    ADDI t4, t4, -12
    SW t3, t4, 0
    ADD s3, s0, s1
    MV s0, s1
    MV s1, s3
    ADDI s2, s2, 1
    J w_1
    ew_2:
    ADDI t5, zero, 10
    LUI t6, 0
    ADDI t6, t6, -12
    SW t5, t6, 0
    HALT