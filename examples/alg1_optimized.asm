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
    ADDI t2, zero, 999
    MUL t3, s1, t2
    BLE t3, s0, el_3
    ADDI s2, zero, 999
    w_5:
    ADDI t4, zero, 99
    BLE s2, t4, ew_6
    MUL s3, s1, s2
    BLE s3, s0, el_7
    MV s4, s3
    MV s5, zero
    w_9:
    BLE s4, zero, ew_10
    ADDI t5, zero, 10
    REM s6, s4, t5
    ADDI t0, zero, 10
    MUL t1, s5, t0
    ADD s5, t1, s6
    ADDI t2, zero, 10
    DIV s4, s4, t2
    J w_9
    ew_10:
    BNE s5, s3, el_11
    MV s0, s3
    J en_12
    el_11:
    en_12:
    J en_8
    el_7:
    ADDI s2, zero, 99
    en_8:
    ADDI s2, s2, -1
    J w_5
    ew_6:
    J en_4
    el_3:
    ADDI s1, zero, 99
    en_4:
    ADDI s1, s1, -1
    J w_1
    ew_2:
    MV s7, s0
    ADDI s6, zero, 1
    w_13:
    BLE s7, zero, ew_14
    ADDI t3, zero, 10
    DIV s7, s7, t3
    ADDI t4, zero, 10
    MUL s6, s6, t4
    J w_13
    ew_14:
    w_15:
    ADDI t5, zero, 1
    BLE s6, t5, ew_16
    ADDI t6, zero, 10
    DIV s6, s6, t6
    DIV s7, s0, s6
    ADDI t0, s7, 48
    LUI t1, 0
    ADDI t1, t1, -12
    SW t0, t1, 0
    REM s0, s0, s6
    J w_15
    ew_16:
    ADDI t2, zero, 10
    LUI t3, 0
    ADDI t3, t3, -12
    SW t2, t3, 0
    HALT