; Compute-bound vector benchmark
; 1024 iterations: VLD + VLDconst + VADD + VST per iteration (4 elements at once)
    .org 0
    ADDI s0, zero, 200
    ADDI s2, zero, 216    ; const vector [1,1,1,1] after 4 ints
    ADDI t0, zero, 1024
    ADDI s1, zero, 0
vloop:
    VLD  V0, [s0+0]
    VLD  V1, [s2+0]
    VADD V0, V0, V1
    VST  V0, [s0+0]
    ADDI s1, s1, 1
    BLT  s1, t0, vloop
    HALT
    .org 200
    .word 0
    .word 0
    .word 0
    .word 0
    .org 216
    .word 1
    .word 1
    .word 1
    .word 1
