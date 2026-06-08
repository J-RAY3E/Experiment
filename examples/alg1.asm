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
    wc_1:
    ADDI t0, zero, 100
    BGE s1, t0, en_2
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
    el_5:
    en_6:
    en_4:
    ADDI s1, s1, 1
    J wc_1
    en_2:
    MV s2, s0
    ADDI s3, zero, 1000
    wc_7:
    BLE s3, zero, en_8
    DIV s4, s2, s3
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, s4, 48
    SW t1, t0, 0
    REM s2, s2, s3
    ADDI t2, zero, 10
    DIV s3, s3, t2
    J wc_7
    en_8:
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 10
    SW t4, t3, 0
    HALT