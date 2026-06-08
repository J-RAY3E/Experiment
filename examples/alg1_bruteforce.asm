    .org 0
    J main
    .org 4
data_start:
    .word 0  ; dummy
    .org 8
    main:
    ADDI gp, zero, data_start
    MV s0, zero
    ADDI s1, zero, 999
    wc_1:
    ADDI t0, zero, 99
    BLE s1, t0, en_2
    ADDI s2, zero, 999
    wc_3:
    ADDI t1, zero, 99
    BLE s2, t1, en_4
    MUL s3, s1, s2
    BLE s3, s0, el_5
    MV s4, s3
    MV s5, zero
    wc_7:
    BLE s4, zero, en_8
    ADDI t2, zero, 10
    REM s6, s4, t2
    ADDI t4, zero, 10
    MUL t5, s5, t4
    ADD s5, t5, s6
    ADDI t6, zero, 10
    DIV s4, s4, t6
    J wc_7
    en_8:
    BNE s5, s3, el_9
    MV s0, s3
    el_9:
    en_10:
    el_5:
    en_6:
    ADDI s2, s2, -1
    J wc_3
    en_4:
    ADDI s1, s1, -1
    J wc_1
    en_2:
    MV s7, s0
    ADDI s6, zero, 1
    wc_11:
    BLE s7, zero, en_12
    ADDI t0, zero, 10
    DIV s7, s7, t0
    ADDI t1, zero, 10
    MUL s6, s6, t1
    J wc_11
    en_12:
    wc_13:
    ADDI t2, zero, 1
    BLE s6, t2, en_14
    ADDI t3, zero, 10
    DIV s6, s6, t3
    DIV s7, s0, s6
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t5, s7, 48
    SW t5, t4, 0
    REM s0, s0, s6
    J wc_13
    en_14:
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, zero, 10
    SW t0, t6, 0
    HALT