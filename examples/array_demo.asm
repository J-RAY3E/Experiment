    .org 0
    J main
    .org 4
data_start:
    .word 10  ; arr[0]
    .word 20  ; arr[1]
    .word 30  ; arr[2]
    .word 40  ; arr[3]
    .word 50  ; arr[4]
    .org 24
    main:
    ADDI gp, zero, data_start
    MV s1, zero
    wc_1:
    ADDI t0, zero, 5
    BGE s1, t0, en_2
    LUI t1, 0
    ADDI t1, t1, -12
    SLLI t2, s1, 2
    ADDI t2, t2, 0
    ADD t2, t2, gp
    LW t3, t2, 0
    ADDI t4, t3, 48
    SW t4, t1, 0
    ADDI s1, s1, 1
    J wc_1
    en_2:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    ADDI t0, zero, 99
    SLLI t1, zero, 2
    ADDI t1, t1, 0
    ADD t1, t1, gp
    SW t0, t1, 0
    LUI t2, 0
    ADDI t2, t2, -12
    SLLI t3, zero, 2
    ADDI t3, t3, 0
    ADD t3, t3, gp
    LW t4, t3, 0
    ADDI t5, t4, 48
    SW t5, t2, 0
    LUI t6, 0
    ADDI t6, t6, -12
    ADDI t0, zero, 10
    SW t0, t6, 0
    HALT