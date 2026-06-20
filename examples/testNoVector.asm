    .data 0
data_start:
    .word 1  ; a[0]
    .word 2  ; a[1]
    .word 3  ; a[2]
    .word 4  ; a[3]
    .word 10  ; b[0]
    .word 20  ; b[1]
    .word 30  ; b[2]
    .word 40  ; b[3]
    .word 0  ; c[0]
    .word 0  ; c[1]
    .word 0  ; c[2]
    .word 0  ; c[3]
    .word 0  ; i
    .word 0  ; tens
    .word 0  ; ones
    .text 0
    J main
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 48
    wc_1:
    LW t0, gp, 48
    ADDI t1, zero, 4
    BGE t0, t1, en_2
    LW t2, gp, 48
    SLLI t3, t2, 2
    ADDI t3, t3, 0
    ADD t3, t3, gp
    LW t4, t3, 0
    LW t5, gp, 48
    SLLI t6, t5, 2
    ADDI t6, t6, 16
    ADD t6, t6, gp
    LW t0, t6, 0
    ADD t1, t4, t0
    LW t2, gp, 48
    SLLI t3, t2, 2
    ADDI t3, t3, 32
    ADD t3, t3, gp
    SW t1, t3, 0
    LW t4, gp, 48
    SLLI t5, t4, 2
    ADDI t5, t5, 32
    ADD t5, t5, gp
    LW t6, t5, 0
    ADDI t1, zero, 10
    DIV t2, t6, t1
    SW t2, gp, 52
    LW t3, gp, 48
    SLLI t4, t3, 2
    ADDI t4, t4, 32
    ADD t4, t4, gp
    LW t5, t4, 0
    ADDI t0, zero, 10
    REM t1, t5, t0
    SW t1, gp, 56
    LUI t2, 0
    ADDI t2, t2, -12
    LW t3, gp, 52
    ADDI t4, t3, 48
    SW t4, t2, 0
    LUI t5, 0
    ADDI t5, t5, -12
    LW t6, gp, 56
    ADDI t0, t6, 48
    SW t0, t5, 0
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, zero, 32
    SW t2, t1, 0
    LW t3, gp, 48
    ADDI t4, t3, 1
    SW t4, gp, 48
    J wc_1
    en_2:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    HALT