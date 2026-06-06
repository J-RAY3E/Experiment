    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    MV s1, zero
    w_1:
    ADDI t0, zero, 100
    BGE s1, t0, ew_2
    ADDI t2, zero, 3
    REM t3, s1, t2
    BNE t3, zero, el_3
    ADD s0, s0, s1
    J en_4
    el_3:
    ADDI t5, zero, 5
    REM t6, s1, t5
    BNE t6, zero, el_5
    ADD s0, s0, s1
    J en_6
    el_5:
    en_6:
    en_4:
    ADDI s1, s1, 1
    J w_1
    ew_2:
    MV s2, s0
    ADDI s3, zero, 1000
    w_7:
    BLE s3, zero, ew_8
    DIV s4, s2, s3
    ADDI t0, s4, 48
    LUI t1, 0
    ADDI t1, t1, -12
    SW t0, t1, 0
    REM s2, s2, s3
    ADDI t2, zero, 10
    DIV s3, s3, t2
    J w_7
    ew_8:
    ADDI t3, zero, 10
    LUI t4, 0
    ADDI t4, t4, -12
    SW t3, t4, 0
    HALT