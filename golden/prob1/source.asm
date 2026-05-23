    .org 0
    main:
    ADDI s0, zero, 999
    w_1:
    ADDI t0, zero, 100
    BLT s0, t0, ew_2
    MV s1, s0
    ADDI t1, zero, 100
    DIV s1, s1, t1
    MV s2, s0
    ADDI t2, zero, 10
    DIV s2, s2, t2
    ADDI t3, zero, 10
    REM s2, s2, t3
    MV s3, s0
    ADDI t4, zero, 10
    REM s3, s3, t4
    MV s4, s0
    ADDI t5, zero, 1000
    MUL s4, s4, t5
    ADDI t0, zero, 100
    MUL t1, s3, t0
    ADD s4, s4, t1
    ADDI t3, zero, 10
    MUL t4, s2, t3
    ADD s4, s4, t4
    ADD s4, s4, s1
    ADDI s5, zero, 999
    w_3:
    ADDI t5, zero, 100
    BLT s5, t5, ew_4
    MUL t6, s5, s5
    BGE t6, s4, el_5
    MV s5, zero
    J en_6
    el_5:
    REM t0, s4, s5
    BNE t0, zero, el_7
    MV s6, s4
    DIV s6, s6, s5
    ADDI t1, zero, 100
    BLT s6, t1, el_9
    ADDI t2, zero, 999
    BGT s6, t2, el_11
    LUI t3, 49
    ADDI t3, t3, -352
    DIV t4, s4, t3
    ADDI t6, zero, 10
    REM t0, t4, t6
    ADDI t1, t0, 48
    LUI t2, 0
    ADDI t2, t2, -12
    SW t1, t2, 0
    LUI t3, 5
    ADDI t3, t3, -240
    DIV t4, s4, t3
    ADDI t6, zero, 10
    REM t0, t4, t6
    ADDI t1, t0, 48
    LUI t2, 0
    ADDI t2, t2, -12
    SW t1, t2, 0
    ADDI t4, zero, 1000
    DIV t5, s4, t4
    ADDI t0, zero, 10
    REM t1, t5, t0
    ADDI t2, t1, 48
    LUI t3, 0
    ADDI t3, t3, -12
    SW t2, t3, 0
    ADDI t5, zero, 100
    DIV t6, s4, t5
    ADDI t1, zero, 10
    REM t2, t6, t1
    ADDI t3, t2, 48
    LUI t4, 0
    ADDI t4, t4, -12
    SW t3, t4, 0
    ADDI t6, zero, 10
    DIV t0, s4, t6
    ADDI t2, zero, 10
    REM t3, t0, t2
    ADDI t4, t3, 48
    LUI t5, 0
    ADDI t5, t5, -12
    SW t4, t5, 0
    ADDI t0, zero, 10
    REM t1, s4, t0
    ADDI t2, t1, 48
    LUI t3, 0
    ADDI t3, t3, -12
    SW t2, t3, 0
    ADDI t4, zero, 10
    LUI t5, 0
    ADDI t5, t5, -12
    SW t4, t5, 0
    HALT
    J en_12
    el_11:
    en_12:
    J en_10
    el_9:
    en_10:
    J en_8
    el_7:
    en_8:
    ADDI s5, s5, -1
    en_6:
    J w_3
    ew_4:
    ADDI s0, s0, -1
    J w_1
    ew_2:
    HALT
    HALT

.org 100