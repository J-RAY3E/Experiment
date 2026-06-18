    .text 0
    J main
    .data 0
data_start:
    .word 0  ; max
    .word 0  ; a
    .word 0  ; b
    .word 0  ; p
    .word 0  ; n
    .word 0  ; rev
    .word 0  ; d
    .word 0  ; t
    .text 4
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 0
    ADDI t0, zero, 999
    SW t0, gp, 4
    wc_1:
    LW t1, gp, 4
    ADDI t2, zero, 99
    BLE t1, t2, en_2
    ADDI t3, zero, 999
    SW t3, gp, 8
    wc_3:
    LW t4, gp, 8
    ADDI t5, zero, 99
    BLE t4, t5, en_4
    LW t6, gp, 4
    LW t0, gp, 8
    MUL t1, t6, t0
    SW t1, gp, 12
    LW t2, gp, 12
    LW t3, gp, 0
    BLE t2, t3, el_5
    LW t4, gp, 12
    SW t4, gp, 16
    SW zero, gp, 20
    wc_7:
    LW t5, gp, 16
    BLE t5, zero, en_8
    LW t6, gp, 16
    ADDI t1, zero, 10
    REM t2, t6, t1
    SW t2, gp, 24
    LW t3, gp, 20
    ADDI t5, zero, 10
    MUL t6, t3, t5
    LW t0, gp, 24
    ADD t1, t6, t0
    SW t1, gp, 20
    LW t2, gp, 16
    ADDI t4, zero, 10
    DIV t5, t2, t4
    SW t5, gp, 16
    J wc_7
    en_8:
    LW t6, gp, 20
    LW t0, gp, 12
    BNE t6, t0, el_9
    LW t1, gp, 12
    SW t1, gp, 0
    el_9:
    en_10:
    el_5:
    en_6:
    LW t2, gp, 8
    ADDI t3, t2, -1
    SW t3, gp, 8
    J wc_3
    en_4:
    LW t4, gp, 4
    ADDI t5, t4, -1
    SW t5, gp, 4
    J wc_1
    en_2:
    LW t6, gp, 0
    SW t6, gp, 28
    ADDI t0, zero, 1
    SW t0, gp, 24
    wc_11:
    LW t1, gp, 28
    BLE t1, zero, en_12
    LW t2, gp, 28
    ADDI t4, zero, 10
    DIV t5, t2, t4
    SW t5, gp, 28
    LW t6, gp, 24
    ADDI t1, zero, 10
    MUL t2, t6, t1
    SW t2, gp, 24
    J wc_11
    en_12:
    wc_13:
    LW t3, gp, 24
    ADDI t4, zero, 1
    BLE t3, t4, en_14
    LW t5, gp, 24
    ADDI t0, zero, 10
    DIV t1, t5, t0
    SW t1, gp, 24
    LW t2, gp, 0
    LW t3, gp, 24
    DIV t4, t2, t3
    SW t4, gp, 28
    LUI t5, 0
    ADDI t5, t5, -12
    LW t6, gp, 28
    ADDI t0, t6, 48
    SW t0, t5, 0
    LW t1, gp, 0
    LW t2, gp, 24
    REM t3, t1, t2
    SW t3, gp, 0
    J wc_13
    en_14:
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t5, zero, 10
    SW t5, t4, 0
    HALT