    .text 0
    J main
data_start:
    .word 0  ; dummy
    .text 4
    main:
    ADDI gp, zero, data_start
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, zero, 50
    SW t1, t0, 0
    LUI t2, 0
    ADDI t2, t2, -12
    ADDI t3, zero, 58
    SW t3, t2, 0
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t5, zero, 49
    SW t5, t4, 0
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, zero, 10
    SW t0, t6, 0
    HALT