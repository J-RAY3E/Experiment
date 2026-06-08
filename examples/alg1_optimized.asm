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
    ADDI t2, zero, 999
    MUL t3, s1, t2
    BLE t3, s0, el_3
    ADDI s2, zero, 999
    wc_5:
    ADDI t4, zero, 99
    BLE s2, t4, en_6
    MUL s3, s1, s2
    BLE s3, s0, el_7
    MV s4, s3
    MV s5, zero
    wc_9:
    BLE s4, zero, en_10
    ADDI t5, zero, 10
    REM s6, s4, t5
    ADDI t0, zero, 10
    MUL t1, s5, t0
    ADD s5, t1, s6
    ADDI t2, zero, 10
    DIV s4, s4, t2
    J wc_9
    en_10:
    BNE s5, s3, el_11
    MV s0, s3
    el_11:
    en_12:
    J en_8
    el_7:
    ADDI s2, zero, 99
    en_8:
    ADDI s2, s2, -1
    J wc_5
    en_6:
    J en_4
    el_3:
    ADDI s1, zero, 99
    en_4:
    ADDI s1, s1, -1
    J wc_1
    en_2:
    MV s7, s0
    ADDI s6, zero, 1
    wc_13:
    BLE s7, zero, en_14
    ADDI t3, zero, 10
    DIV s7, s7, t3
    ADDI t4, zero, 10
    MUL s6, s6, t4
    J wc_13
    en_14:
    wc_15:
    ADDI t5, zero, 1
    BLE s6, t5, en_16
    ADDI t6, zero, 10
    DIV s6, s6, t6
    DIV s7, s0, s6
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, s7, 48
    SW t1, t0, 0
    REM s0, s0, s6
    J wc_15
    en_16:
    LUI t2, 0
    ADDI t2, t2, -12
    ADDI t3, zero, 10
    SW t3, t2, 0
    HALT