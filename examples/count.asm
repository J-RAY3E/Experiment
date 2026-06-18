    .text 0
    J main
    .data 0
data_start:
    .word 0  ; i
    .text 4
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 0
    wc_1:
    LW t0, gp, 0
    ADDI t1, zero, 10
    BGE t0, t1, en_2
    LUI t2, 0
    ADDI t2, t2, -12
    LW t3, gp, 0
    ADDI t4, t3, 48
    SW t4, t2, 0
    LW t5, gp, 0
    ADDI t6, t5, 1
    SW t6, gp, 0
    J wc_1
    en_2:
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, zero, 10
    SW t1, t0, 0
    HALT