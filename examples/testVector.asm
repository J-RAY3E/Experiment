; Vector version: add two 4-element arrays using vector instructions
; Array A at .org 200 (values: 1, 2, 3, 4)
; Array B at .org 204 (values: 10, 20, 30, 40)
; Array C at .org 208 (result, initialized to 0)
; Prints: "11 22 33 44\n"

    .org 0
    ADDI s0, zero, 200   ; s0 = base of array A
    ADDI s1, zero, 204   ; s1 = base of array B
    ADDI s2, zero, 208   ; s2 = base of array C
    VLD  V0, [s0+0]      ; load A[0..3] into V0
    VLD  V1, [s1+0]      ; load B[0..3] into V1
    VADD V2, V0, V1      ; V2 = V0 + V1 (element-wise)
    VST  V2, [s2+0]      ; store result to C[0..3]

    ADDI s3, zero, 0     ; loop index i = 0
    ADDI t0, zero, 4     ; loop bound

print_loop:
    BGE  s3, t0, done
    ADD  t1, s2, s3      ; address of C[i]
    LW   t2, t1, 0       ; load C[i]
    ADDI t3, zero, 10
    DIV  t4, t2, t3      ; tens digit
    REM  t5, t2, t3      ; ones digit
    ADDI t4, t4, 48
    SW   t4, zero, 0xFFF4
    ADDI t5, t5, 48
    SW   t5, zero, 0xFFF4
    ADDI t6, zero, 32    ; space
    SW   t6, zero, 0xFFF4
    ADDI s3, s3, 1
    J print_loop

done:
    ADDI t0, zero, 10    ; newline
    SW   t0, zero, 0xFFF4
    HALT

    .org 200
    .word 1
    .word 2
    .word 3
    .word 4
    .org 204
    .word 10
    .word 20
    .word 30
    .word 40
    .org 208
    .word 0
    .word 0
    .word 0
    .word 0
