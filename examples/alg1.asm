    .text 0
    J main
    .data 0
data_start:
    .word 0  ; sum
    .word 0  ; i
    .word 0  ; t
    .word 0  ; d
    .word 0  ; q
    .text 4
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 0
    SW zero, gp, 4
    wc_1:
    LW t0, gp, 4
    ADDI t1, zero, 100
    BGE t0, t1, en_2
    LW t2, gp, 4
    ADDI t4, zero, 3
    REM t5, t2, t4
    BNE t5, zero, el_3
    LW t6, gp, 0
    LW t0, gp, 4
    ADD t1, t6, t0
    SW t1, gp, 0
    J en_4
    el_3:
    LW t2, gp, 4
    ADDI t4, zero, 5
    REM t5, t2, t4
    BNE t5, zero, el_5
    LW t6, gp, 0
    LW t0, gp, 4
    ADD t1, t6, t0
    SW t1, gp, 0
    el_5:
    en_6:
    en_4:
    LW t2, gp, 4
    ADDI t3, t2, 1
    SW t3, gp, 4
    J wc_1
    en_2:
    LW t4, gp, 0
    SW t4, gp, 8
    ADDI t5, zero, 1000
    SW t5, gp, 12
    wc_7:
    LW t6, gp, 12
    BLE t6, zero, en_8
    LW t0, gp, 8
    LW t1, gp, 12
    DIV t2, t0, t1
    SW t2, gp, 16
    LUI t3, 0
    ADDI t3, t3, -12
    LW t4, gp, 16
    ADDI t5, t4, 48
    SW t5, t3, 0
    LW t6, gp, 8
    LW t0, gp, 12
    REM t1, t6, t0
    SW t1, gp, 8
    LW t2, gp, 12
    ADDI t4, zero, 10
    DIV t5, t2, t4
    SW t5, gp, 12
    J wc_7
    en_8:
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, zero, 10
    SW t0, t6, 0
    HALT