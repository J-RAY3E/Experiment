    .text 0
    J main
    .data 0
data_start:
    .word 0  ; n
    .word 0  ; result
    .word 0  ; x
    .word 0  ; y
    .text 4
    double:
    ADDI sp, sp, -4
    SW ra, sp, 0
    SW a0, gp, 0
    LW t0, gp, 0
    ADDI t2, zero, 2
    MUL t3, t0, t2
    SW t3, gp, 4
    LW t4, gp, 4
    MV a0, t4
    LW ra, sp, 0
    ADDI sp, sp, 4
    JR ra
    main:
    ADDI gp, zero, data_start
    ADDI t5, zero, 21
    SW t5, gp, 8
    LW t6, gp, 8
    MV a0, t6
    JAL ra, double
    MV t0, a0
    SW t0, gp, 12
    LUI t1, 0
    ADDI t1, t1, -12
    LW t2, gp, 12
    SW t2, t1, 0
    HALT