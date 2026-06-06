    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    MV s1, zero
    MV s2, zero
    MV s3, zero
    MV s4, zero
    MV s5, zero
    w_1:
    ADDI t0, zero, 4
    BGE s0, t0, ew_2
    BNE s0, zero, el_3
    ADDI s1, zero, 1
    ADDI s2, zero, 10
    J en_4
    el_3:
    en_4:
    ADDI t1, zero, 1
    BNE s0, t1, el_5
    ADDI s1, zero, 2
    ADDI s2, zero, 20
    J en_6
    el_5:
    en_6:
    ADDI t2, zero, 2
    BNE s0, t2, el_7
    ADDI s1, zero, 3
    ADDI s2, zero, 30
    J en_8
    el_7:
    en_8:
    ADDI t3, zero, 3
    BNE s0, t3, el_9
    ADDI s1, zero, 4
    ADDI s2, zero, 40
    J en_10
    el_9:
    en_10:
    ADD s3, s1, s2
    ADDI t4, zero, 10
    DIV s4, s3, t4
    ADDI t5, zero, 10
    REM s5, s3, t5
    ADDI t6, s4, 48
    LUI t0, 0
    ADDI t0, t0, -12
    SW t6, t0, 0
    ADDI t1, s5, 48
    LUI t2, 0
    ADDI t2, t2, -12
    SW t1, t2, 0
    ADDI t3, zero, 32
    LUI t4, 0
    ADDI t4, t4, -12
    SW t3, t4, 0
    ADDI s0, s0, 1
    J w_1
    ew_2:
    ADDI t5, zero, 10
    LUI t6, 0
    ADDI t6, t6, -12
    SW t5, t6, 0
    HALT