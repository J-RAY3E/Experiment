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
    .org 36
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
    ADDI t0, gp, 0
    ADDI t1, gp, 16
    ADDI t2, gp, 36
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
    SW zero, gp, 52
    wc_2:
    LW t4, gp, 52
    ADDI t5, zero, 4
    BGE t4, t5, en_3
    LW t6, gp, 52
    SLLI t0, t6, 2
    ADDI t0, t0, 36
    ADD t0, t0, gp
    LW t1, t0, 0
    ADDI t3, zero, 10
    DIV t4, t1, t3
    SW t4, gp, 56
    LW t5, gp, 52
    SLLI t6, t5, 2
    ADDI t6, t6, 36
    ADD t6, t6, gp
    LW t0, t6, 0
    ADDI t2, zero, 10
    REM t3, t0, t2
    SW t3, gp, 60
    LUI t4, 0
    ADDI t4, t4, -12
    LW t5, gp, 56
    ADDI t6, t5, 48
    SW t6, t4, 0
    LUI t0, 0
    ADDI t0, t0, -12
    LW t1, gp, 60
    ADDI t2, t1, 48
    SW t2, t0, 0
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 32
    SW t4, t3, 0
    LW t5, gp, 52
    ADDI t6, t5, 1
    SW t6, gp, 52
    J wc_2
    en_3:
    LUI t0, 0
    ADDI t0, t0, -12
    ADDI t1, zero, 10
    SW t1, t0, 0
    HALT