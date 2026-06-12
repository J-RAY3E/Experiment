    .org 0
    J main
    .org 4
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
    .org 52
    main:
    ADDI gp, zero, data_start
    MV s3, zero
    wc_1:
    ADDI t0, zero, 4
    BGE s3, t0, en_2
    SLLI t1, s3, 2
    ADDI t1, t1, 0
    ADD t1, t1, gp
    LW t2, t1, 0
    SLLI t3, s3, 2
    ADDI t3, t3, 16
    ADD t3, t3, gp
    LW t4, t3, 0
    ADD t5, t2, t4
    SLLI t6, s3, 2
    ADDI t6, t6, 32
    ADD t6, t6, gp
    SW t5, t6, 0
    SLLI t0, s3, 2
    ADDI t0, t0, 32
    ADD t0, t0, gp
    LW t1, t0, 0
    ADDI t2, zero, 10
    DIV s4, t1, t2
    SLLI t3, s3, 2
    ADDI t3, t3, 32
    ADD t3, t3, gp
    LW t4, t3, 0
    ADDI t5, zero, 10
    REM s5, t4, t5
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, s4, 48
    SW t0, t6, 0
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, s5, 48
    SW t2, t1, 0
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 32
    SW t4, t3, 0
    ADDI s3, s3, 1
    J wc_1
    en_2:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    HALT