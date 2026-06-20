    .data 0
data_start:
    .word 0  ; n
    .word 0  ; result
    .word 0  ; x
    .word 0  ; y
    .text 0
    J main
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
    LW t1, gp, 12
    MV t2, t1
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t5, zero, 10
    ADDI t3, zero, 1
    pnl_1:
    DIV t4, t2, t3
    BLT t4, t5, pn2_2
    MUL t3, t3, t5
    J pnl_1
    pn2_2:
    pn3_3:
    DIV t4, t2, t3
    REM t2, t2, t3
    ADDI t4, t4, 48
    SW t4, t6, 0
    DIV t3, t3, t5
    BNE t3, zero, pn3_3
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, zero, 10
    SW t1, t0, 0
    HALT
