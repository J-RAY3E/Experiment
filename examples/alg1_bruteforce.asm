    .org 0
    J main
    .org 256
data_start:
    .org 1
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    ADDI s1, zero, 999
    w_1:
    ADDI t0, zero, 99
    BLE s1, t0, ew_2
    ADDI s2, zero, 999
    w_3:
    ADDI t1, zero, 99
    BLE s2, t1, ew_4
    MUL s3, s1, s2
    BLE s3, s0, el_5
    MV s4, s3
    MV s5, zero
    w_7:
    BLE s4, zero, ew_8
    ADDI t2, zero, 10
    REM s6, s4, t2
    ADDI t4, zero, 10
    MUL t5, s5, t4
    ADD s5, t5, s6
    ADDI t6, zero, 10
    DIV s4, s4, t6
    J w_7
    ew_8:
    BNE s5, s3, el_9
    MV s0, s3
    J en_10
    el_9:
    en_10:
    J en_6
    el_5:
    en_6:
    ADDI s2, s2, -1
    J w_3
    ew_4:
    ADDI s1, s1, -1
    J w_1
    ew_2:
    MV s7, s0
    ADDI s6, zero, 1
    w_11:
    BLE s7, zero, ew_12
    ADDI t0, zero, 10
    DIV s7, s7, t0
    ADDI t1, zero, 10
    MUL s6, s6, t1
    J w_11
    ew_12:
    w_13:
    ADDI t2, zero, 1
    BLE s6, t2, ew_14
    ADDI t3, zero, 10
    DIV s6, s6, t3
    DIV s7, s0, s6
    ADDI t4, s7, 48
    LUI t5, 0
    ADDI t5, t5, -12
    SW t4, t5, 0
    REM s0, s0, s6
    J w_13
    ew_14:
    ADDI t6, zero, 10
    LUI t0, 0
    ADDI t0, t0, -12
    SW t6, t0, 0
    HALT