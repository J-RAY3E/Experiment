    .org 0
    J main
    .org 4
data_start:
    .word 0  ; dummy
    .org 8
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    MV s1, zero
    MV s2, zero
    MV s3, zero
    MV s4, zero
    MV s5, zero
    wc_1:
    ADDI t0, zero, 4
    BGE s0, t0, en_2
    BNE s0, zero, el_3
    ADDI s1, zero, 1
    ADDI s2, zero, 10
    el_3:
    en_4:
    ADDI t1, zero, 1
    BNE s0, t1, el_5
    ADDI s1, zero, 2
    ADDI s2, zero, 20
    el_5:
    en_6:
    ADDI t2, zero, 2
    BNE s0, t2, el_7
    ADDI s1, zero, 3
    ADDI s2, zero, 30
    el_7:
    en_8:
    ADDI t3, zero, 3
    BNE s0, t3, el_9
    ADDI s1, zero, 4
    ADDI s2, zero, 40
    el_9:
    en_10:
    ADD s3, s1, s2
    ADDI t4, zero, 10
    DIV s4, s3, t4
    ADDI t5, zero, 10
    REM s5, s3, t5
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, s4, 48
    SW t0, t6, 0
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, s5, 48
    SW t2, t1, 0
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 32
    SW t4, t3, 0
    ADDI s0, s0, 1
    J wc_1
    en_2:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    HALT