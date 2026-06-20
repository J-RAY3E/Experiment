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
    .text 0
    J main
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 0
    ADDI t0, zero, 999
    SW t0, gp, 4
    wc_1:
    LW t1, gp, 4
    ADDI t2, zero, 99
    BLE t1, t2, en_2
    LW t3, gp, 4
    ADDI t5, zero, 999
    MUL t6, t3, t5
    LW t0, gp, 0
    BLE t6, t0, el_3
    ADDI t1, zero, 999
    SW t1, gp, 8
    wc_5:
    LW t2, gp, 8
    ADDI t3, zero, 99
    BLE t2, t3, en_6
    LW t4, gp, 4
    LW t5, gp, 8
    MUL t6, t4, t5
    SW t6, gp, 12
    LW t0, gp, 12
    LW t1, gp, 0
    BLE t0, t1, el_7
    LW t2, gp, 12
    SW t2, gp, 16
    SW zero, gp, 20
    wc_9:
    LW t3, gp, 16
    BLE t3, zero, en_10
    LW t4, gp, 16
    ADDI t6, zero, 10
    REM t0, t4, t6
    SW t0, gp, 24
    LW t1, gp, 20
    ADDI t3, zero, 10
    MUL t4, t1, t3
    LW t5, gp, 24
    ADD t6, t4, t5
    SW t6, gp, 20
    LW t0, gp, 16
    ADDI t2, zero, 10
    DIV t3, t0, t2
    SW t3, gp, 16
    J wc_9
    en_10:
    LW t4, gp, 20
    LW t5, gp, 12
    BNE t4, t5, el_11
    LW t6, gp, 12
    SW t6, gp, 0
    el_11:
    en_12:
    J en_8
    el_7:
    ADDI t0, zero, 99
    SW t0, gp, 8
    en_8:
    LW t1, gp, 8
    ADDI t2, t1, -1
    SW t2, gp, 8
    J wc_5
    en_6:
    J en_4
    el_3:
    ADDI t3, zero, 99
    SW t3, gp, 4
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
    wc_13:
    LW t1, gp, 28
    BLE t1, zero, en_14
    LW t2, gp, 28
    ADDI t4, zero, 10
    DIV t5, t2, t4
    SW t5, gp, 28
    LW t6, gp, 24
    ADDI t1, zero, 10
    MUL t2, t6, t1
    SW t2, gp, 24
    J wc_13
    en_14:
    wc_15:
    LW t3, gp, 24
    ADDI t4, zero, 1
    BLE t3, t4, en_16
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
    J wc_15
    en_16:
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t5, zero, 10
    SW t5, t4, 0
    HALT