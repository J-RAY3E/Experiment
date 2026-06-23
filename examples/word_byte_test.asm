    .data 0
data_start:
    .word 65    ; 'A'
    .byte 66    ; 'B'
    .text 0
    J main
main:
    ADDI gp, zero, data_start
    LW t0, gp, 0
    LB t1, gp, 4
    LUI t2, 0
    ADDI t2, t2, -12
    SW t0, t2, 0
    SW t1, t2, 0
    HALT
