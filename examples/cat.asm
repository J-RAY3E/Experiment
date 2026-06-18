    .text 0
    J main
    .data 0
data_start:
    .word 0  ; c
    .text 4
    main:
    ADDI gp, zero, data_start
    LUI t1, 0
    ADDI t1, t1, -16
    LW t0, t1, 0
    SW t0, gp, 0
    wc_1:
    LW t2, gp, 0
    BEQ t2, zero, en_2
    LUI t3, 0
    ADDI t3, t3, -12
    LW t4, gp, 0
    SW t4, t3, 0
    LUI t6, 0
    ADDI t6, t6, -16
    LW t5, t6, 0
    SW t5, gp, 0
    J wc_1
    en_2:
    HALT