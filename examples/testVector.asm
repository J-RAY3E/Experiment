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
    ADDI t0, gp, 0
    ADDI t1, gp, 16
    ADDI t2, gp, 32
    ADDI t3, zero, 1
    vh_1:
    VLD V0, [t0+0]
    VLD V1, [t1+0]
    VADD V2, V0, V1
    VST V2, [t2+0]
    ADDI t0, t0, 16
    ADDI t1, t1, 16
    ADDI t2, t2, 16
    ADDI t3, t3, -1
    BNE t3, zero, vh_1
    MV s3, zero
    wc_2:
    ADDI t4, zero, 4
    BGE s3, t4, en_3
    SLLI t5, s3, 2
    ADDI t5, t5, 32
    ADD t5, t5, gp
    LW t6, t5, 0
    ADDI t0, zero, 10
    DIV s4, t6, t0
    SLLI t1, s3, 2
    ADDI t1, t1, 32
    ADD t1, t1, gp
    LW t2, t1, 0
    ADDI t3, zero, 10
    REM s5, t2, t3
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t5, s4, 48
    SW t5, t4, 0
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, s5, 48
    SW t0, t6, 0
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, zero, 32
    SW t2, t1, 0
    ADDI s3, s3, 1
    J wc_2
    en_3:
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 10
    SW t4, t3, 0
    HALT