    .org 0
    J main
    .org 256
data_start:
    .word 0  ; dummy
    .string "Hello, World!\n"
    .org 1
    main:
    ADDI gp, zero, data_start
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t0, gp, 1
    LW t1, t0, 0
    ADDI t2, zero, 0
    ps_1:
    BGE t2, t1, pe_2
    ADDI t3, t0, 1
    ADD t3, t3, t2
    LW t4, t3, 0
    SW t4, t5, 0
    ADDI t2, t2, 1
    J ps_1
    pe_2:
    HALT