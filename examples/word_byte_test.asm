.data 0
data_start:
.word 65
.byte 66
.text 0
J main
main:
ADDI gp, zero, data_start
LW t0, gp, 0
LB t1, gp, 4
HALT
