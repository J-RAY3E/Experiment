    .data 0
data_start:
    .word 0  ; arr[0]
    .word 0  ; arr[1]
    .word 0  ; arr[2]
    .word 0  ; arr[3]
    .word 0  ; arr[4]
    .word 0  ; arr[5]
    .word 0  ; arr[6]
    .word 0  ; arr[7]
    .word 0  ; arr[8]
    .word 0  ; arr[9]
    .word 0  ; n
    .word 0  ; num
    .word 0  ; have
    .word 0  ; reading
    .word 0  ; c
    .word 0  ; i
    .word 0  ; j
    .word 0  ; tmp
    .text 0
    J main
    main:
    ADDI gp, zero, data_start
    SW zero, gp, 40
    SW zero, gp, 44
    SW zero, gp, 48
    ADDI t0, zero, 1
    SW t0, gp, 52
    wc_1:
    LW t1, gp, 52
    BEQ t1, zero, en_2
    LUI t3, 0
    ADDI t3, t3, -16
    LW t2, t3, 0
    SW t2, gp, 56
    LW t4, gp, 56
    BNE t4, zero, el_3
    SW zero, gp, 52
    el_3:
    en_4:
    LW t5, gp, 56
    ADDI t6, zero, 10
    BNE t5, t6, el_5
    LW t0, gp, 48
    BEQ t0, zero, el_7
    LW t1, gp, 44
    LW t2, gp, 40
    SLLI t3, t2, 2
    ADDI t3, t3, 0
    ADD t3, t3, gp
    SW t1, t3, 0
    LW t4, gp, 40
    ADDI t5, t4, 1
    SW t5, gp, 40
    SW zero, gp, 44
    SW zero, gp, 48
    el_7:
    en_8:
    SW zero, gp, 52
    el_5:
    en_6:
    LW t0, gp, 56
    ADDI t1, zero, 32
    SUB t2, t0, t1
    SLT t3, zero, t2
    SLT t4, t2, zero
    OR t2, t3, t4
    XORI t2, t2, 1
    MV t6, t2
    MV s0, t6
    BNE s0, zero, sc_11
    LW t5, gp, 56
    ADDI t6, zero, 13
    SUB t0, t5, t6
    SLT t1, zero, t0
    SLT t2, t0, zero
    OR t0, t1, t2
    XORI t0, t0, 1
    OR s0, s0, t0
    sc_11:
    BEQ s0, zero, el_9
    LW t3, gp, 48
    BEQ t3, zero, el_12
    LW t4, gp, 44
    LW t5, gp, 40
    SLLI t6, t5, 2
    ADDI t6, t6, 0
    ADD t6, t6, gp
    SW t4, t6, 0
    LW t0, gp, 40
    ADDI t1, t0, 1
    SW t1, gp, 40
    SW zero, gp, 44
    SW zero, gp, 48
    el_12:
    en_13:
    el_9:
    en_10:
    LW t5, gp, 56
    SUB t6, t5, zero
    SLT t0, zero, t6
    SLT t1, t6, zero
    OR t6, t0, t1
    XORI t6, t6, 1
    MV t4, t6
    MV s2, t4
    BNE s2, zero, sc_16
    LW t2, gp, 56
    ADDI t3, zero, 10
    SUB t4, t2, t3
    SLT t5, zero, t4
    SLT t6, t4, zero
    OR t4, t5, t6
    XORI t4, t4, 1
    OR s2, s2, t4
    sc_16:
    MV t3, s2
    MV s1, t3
    BNE s1, zero, sc_17
    LW t0, gp, 56
    ADDI t1, zero, 32
    SUB t2, t0, t1
    SLT t3, zero, t2
    SLT t4, t2, zero
    OR t2, t3, t4
    XORI t2, t2, 1
    OR s1, s1, t2
    sc_17:
    MV t2, s1
    MV s0, t2
    BNE s0, zero, sc_18
    LW t5, gp, 56
    ADDI t6, zero, 13
    SUB t0, t5, t6
    SLT t1, zero, t0
    SLT t2, t0, zero
    OR t0, t1, t2
    XORI t0, t0, 1
    OR s0, s0, t0
    sc_18:
    XORI t3, s0, 1
    BEQ t3, zero, el_14
    LW t4, gp, 44
    ADDI t6, zero, 10
    MUL t0, t4, t6
    LW t1, gp, 56
    ADDI t2, t1, -48
    ADD t3, t0, t2
    SW t3, gp, 44
    ADDI t4, zero, 1
    SW t4, gp, 48
    el_14:
    en_15:
    J wc_1
    en_2:
    SW zero, gp, 60
    wc_19:
    LW t5, gp, 60
    LW t6, gp, 40
    ADDI t0, t6, -1
    BGE t5, t0, en_20
    SW zero, gp, 64
    wc_21:
    LW t1, gp, 64
    LW t2, gp, 40
    ADDI t3, t2, -1
    LW t4, gp, 60
    SUB t5, t3, t4
    BGE t1, t5, en_22
    LW t6, gp, 64
    SLLI t0, t6, 2
    ADDI t0, t0, 0
    ADD t0, t0, gp
    LW t1, t0, 0
    LW t2, gp, 64
    ADDI t3, t2, 1
    SLLI t4, t3, 2
    ADDI t4, t4, 0
    ADD t4, t4, gp
    LW t5, t4, 0
    BLE t1, t5, el_23
    LW t6, gp, 64
    SLLI t0, t6, 2
    ADDI t0, t0, 0
    ADD t0, t0, gp
    LW t1, t0, 0
    SW t1, gp, 68
    LW t2, gp, 64
    ADDI t3, t2, 1
    SLLI t4, t3, 2
    ADDI t4, t4, 0
    ADD t4, t4, gp
    LW t5, t4, 0
    LW t6, gp, 64
    SLLI t0, t6, 2
    ADDI t0, t0, 0
    ADD t0, t0, gp
    SW t5, t0, 0
    LW t1, gp, 68
    LW t2, gp, 64
    ADDI t3, t2, 1
    SLLI t4, t3, 2
    ADDI t4, t4, 0
    ADD t4, t4, gp
    SW t1, t4, 0
    el_23:
    en_24:
    LW t5, gp, 64
    ADDI t6, t5, 1
    SW t6, gp, 64
    J wc_21
    en_22:
    LW t0, gp, 60
    ADDI t1, t0, 1
    SW t1, gp, 60
    J wc_19
    en_20:
    SW zero, gp, 60
    wc_25:
    LW t2, gp, 60
    LW t3, gp, 40
    BGE t2, t3, en_26
    LW t4, gp, 60
    SLLI t5, t4, 2
    ADDI t5, t5, 0
    ADD t5, t5, gp
    LW t6, t5, 0
    MV t0, t6
    LUI t4, 0
    ADDI t4, t4, -12
    ADDI t3, zero, 10
    ADDI t1, zero, 1
    pnl_27:
    DIV t2, t0, t1
    BLT t2, t3, pn2_28
    MUL t1, t1, t3
    J pnl_27
    pn2_28:
    pn3_29:
    DIV t2, t0, t1
    REM t0, t0, t1
    ADDI t2, t2, 48
    SW t2, t4, 0
    DIV t1, t1, t3
    BNE t1, zero, pn3_29
    LW t5, gp, 60
    LW t6, gp, 40
    ADDI t0, t6, -1
    BGE t5, t0, el_30
    LUI t1, 0
    ADDI t1, t1, -12
    ADDI t2, zero, 32
    SW t2, t1, 0
    el_30:
    en_31:
    LW t3, gp, 60
    ADDI t4, t3, 1
    SW t4, gp, 60
    J wc_25
    en_26:
    LUI t5, 0
    ADDI t5, t5, -12
    ADDI t6, zero, 10
    SW t6, t5, 0
    HALT