    .org 0
    main:
    ADDI t0, zero, 0
    SW t0, gp, 0
    ADDI t1, zero, 100
    SW t1, gp, 1
    ADDI t2, zero, 0
    SW t2, gp, 2
    ADDI t3, zero, 0
    SW t3, gp, 3
    ADDI t4, zero, 0
    SW t4, gp, 4
    ADDI t5, zero, 0
    SW t5, gp, 5
    ADDI t6, zero, 0
    SW t6, gp, 6
    w_1:
    LW t0, gp, 1
    ADDI t1, zero, 1000
    SLT t2, t0, t1
    BEQZ t2, ew_2
    ADDI t3, zero, 100
    SW t3, gp, 2
    w_3:
    LW t4, gp, 2
    ADDI t5, zero, 1000
    SLT t6, t4, t5
    BEQZ t6, ew_4
    LW t0, gp, 1
    LW t1, gp, 2
    MUL t2, t0, t1
    SW t2, gp, 3
    LW t3, gp, 3
    LW t4, gp, 0
    SLT t5, t4, t3
    BEQZ t5, el_5
    LW t6, gp, 3
    SW t6, gp, 4
    ADDI t0, zero, 0
    SW t0, gp, 5
    w_7:
    LW t1, gp, 4
    ADDI t2, zero, 0
    SLT t3, t2, t1
    BEQZ t3, ew_8
    LW t4, gp, 4
    ADDI t5, zero, 10
    REM t6, t4, t5
    SW t6, gp, 6
    LW t0, gp, 5
    ADDI t1, zero, 10
    MUL t2, t0, t1
    LW t3, gp, 6
    ADD t4, t2, t3
    SW t4, gp, 5
    LW t5, gp, 4
    ADDI t6, zero, 10
    DIV t0, t5, t6
    SW t0, gp, 4
    J w_7
    ew_8:
    LW t1, gp, 5
    LW t2, gp, 3
    SUB t3, t1, t2
    BEQZ t3, eq_9
    ADDI t3, zero, 1; J eq_9_s
    eq_9: ADDI t3, zero, 1
    eq_9_s:
    BEQZ t3, el_10
    LW t4, gp, 3
    SW t4, gp, 0
    J en_11
    el_10:
    en_11:
    J en_6
    el_5:
    en_6:
    LW t5, gp, 2
    ADDI t6, zero, 1
    ADD t0, t5, t6
    SW t0, gp, 2
    J w_3
    ew_4:
    LW t1, gp, 1
    ADDI t2, zero, 1
    ADD t3, t1, t2
    SW t3, gp, 1
    J w_1
    ew_2:
    LW t4, gp, 0
    SW t4, gp, 7
    ADDI t5, zero, 0
    SW t5, gp, 8
    ADDI t6, zero, 1
    SW t6, gp, 9
    w_12:
    LW t0, gp, 7
    ADDI t1, zero, 0
    SLT t2, t1, t0
    BEQZ t2, ew_13
    LW t3, gp, 8
    ADDI t4, zero, 1
    ADD t5, t3, t4
    SW t5, gp, 8
    LW t6, gp, 7
    ADDI t0, zero, 10
    DIV t1, t6, t0
    SW t1, gp, 7
    LW t2, gp, 9
    ADDI t3, zero, 10
    MUL t4, t2, t3
    SW t4, gp, 9
    J w_12
    ew_13:
    LW t5, gp, 9
    ADDI t6, zero, 10
    DIV t0, t5, t6
    SW t0, gp, 9
    w_14:
    LW t1, gp, 9
    ADDI t2, zero, 0
    SLT t3, t2, t1
    BEQZ t3, ew_15
    LW t4, gp, 0
    LW t5, gp, 9
    DIV t6, t4, t5
    SW t6, gp, 6
    LW t0, gp, 6
    ADDI t1, zero, 48
    ADD t2, t0, t1
    SW t2, zero, 0xFFF4
    LW t3, gp, 0
    LW t4, gp, 6
    LW t5, gp, 9
    MUL t6, t4, t5
    SUB t0, t3, t6
    SW t0, gp, 0
    LW t1, gp, 9
    ADDI t2, zero, 10
    DIV t3, t1, t2
    SW t3, gp, 9
    J w_14
    ew_15:
    ADDI t4, zero, 10
    SW t4, zero, 0xFFF4
    HALT
    HALT

.org 110
    .word 0  ; max
    .word 0  ; a
    .word 0  ; b
    .word 0  ; p
    .word 0  ; n
    .word 0  ; rev
    .word 0  ; d
    .word 0  ; t
    .word 0  ; digits
    .word 0  ; div
