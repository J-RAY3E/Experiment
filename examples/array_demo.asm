    .text 0
    J main
    .data 0
data_start:
    .word 10  ; arr[0]
    .word 20  ; arr[1]
    .word 30  ; arr[2]
    .word 40  ; arr[3]
    .word 50  ; arr[4]
    .word 0  ; i
    .text 4
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 20
    wc_1:
    LW t0, gp, 20
    ADDI t1, zero, 5
    BGE t0, t1, en_2
    LUI t2, 0
    ADDI t2, t2, -12
    LW t3, gp, 20
    SLLI t4, t3, 2
    ADDI t4, t4, 0
    ADD t4, t4, gp
    LW t5, t4, 0
    ADDI t6, t5, 48
    SW t6, t2, 0
    LW t0, gp, 20
    ADDI t1, t0, 1
    SW t1, gp, 20
    J wc_1
    en_2:
    LUI t2, 0
    ADDI t2, t2, -12
    ADDI t3, zero, 10
    SW t3, t2, 0
    ADDI t4, zero, 99
    SLLI t5, zero, 2
    ADDI t5, t5, 0
    ADD t5, t5, gp
    SW t4, t5, 0
    LUI t6, 0
    ADDI t6, t6, -12
    SLLI t0, zero, 2
    ADDI t0, t0, 0
    ADD t0, t0, gp
    LW t1, t0, 0
    ADDI t2, t1, 48
    SW t2, t6, 0
    LUI t3, 0
    ADDI t3, t3, -12
    ADDI t4, zero, 10
    SW t4, t3, 0
    HALT