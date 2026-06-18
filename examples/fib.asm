    .text 0
    J main
    .data 0
data_start:
    .word 0  ; a
    .word 0  ; b
    .word 0  ; i
    .word 0  ; c
    .text 4
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 0
    ADDI t0, zero, 1
    SW t0, gp, 4
    SW zero, gp, 8
    wc_1:
    LW t1, gp, 8
    ADDI t2, zero, 10
    BGE t1, t2, en_2
    LUI t3, 0
    ADDI t3, t3, -12
    LW t4, gp, 0
    ADDI t5, t4, 48
    SW t5, t3, 0
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, zero, 32
    SW t0, t6, 0
    LW t1, gp, 0
    LW t2, gp, 4
    ADD t3, t1, t2
    SW t3, gp, 12
    LW t4, gp, 4
    SW t4, gp, 0
    LW t5, gp, 12
    SW t5, gp, 4
    LW t6, gp, 8
    ADDI t0, t6, 1
    SW t0, gp, 8
    J wc_1
    en_2:
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, zero, 10
    SW t2, t1, 0
    HALT