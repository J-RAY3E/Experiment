    .data 0
data_start:
    .word 0  ; a
    .word 0  ; b
    .word 0  ; c
    .text 0
    J main
    main:
    ADDI gp, zero, data_start
    ADDI t0, zero, 10
    SW t0, gp, 0
    ADDI t1, zero, 20
    SW t1, gp, 4
    LW t2, gp, 0
    LW t3, gp, 4
    ADD t4, t2, t3
    SW t4, gp, 8
    LUI t5, 0
    ADDI t5, t5, -12
    LW t6, gp, 8
    ADDI t0, t6, 48
    SW t0, t5, 0
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, zero, 10
    SW t2, t1, 0
    HALT