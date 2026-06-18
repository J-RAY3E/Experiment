    .text 0
    J main
    .data 0
data_start:
    .string "Hello, World!\n"
    .text 4
    main:
    ADDI gp, zero, data_start
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t0, gp, 0
    LW t1, t0, 0
    ADDI t0, t0, 4
    ADDI t2, zero, 0
    ps_1:
    BGE t2, t1, pe_2
    ADD t3, t0, t2
    LB t3, t3, 0
    SW t3, t4, 0
    ADDI t2, t2, 1
    J ps_1
    pe_2:
    HALT