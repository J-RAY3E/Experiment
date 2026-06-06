    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    w_1:
    ADDI t0, zero, 10
    BGE s0, t0, ew_2
    ADDI t1, s0, 48
    LUI t2, 0
    ADDI t2, t2, -12
    SW t1, t2, 0
    ADDI s0, s0, 1
    J w_1
    ew_2:
    ADDI t3, zero, 10
    LUI t4, 0
    ADDI t4, t4, -12
    SW t3, t4, 0
    HALT