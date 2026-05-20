; vector_demo — compare scalar vs vector addition of 4-element arrays
; Demonstrates: VLD, VADD, VST instructions, vector register usage
;
; Computes: C[i] = A[i] + B[i] for i in 0..3
; A = [10, 20, 30, 40], B = [1, 2, 3, 4], expected C = [11, 22, 33, 44]
; Prints each result element as decimal
.org 0
    ; --- Vector version (1 VADD instead of 4 scalar ADDs) ---
    ADDI s0, zero, 200      ; s0 = base of array A
    ADDI s1, zero, 204      ; s1 = base of array B
    ADDI s2, zero, 208      ; s2 = base of array C

    ; Load vectors
    VLD  V0, [s0+0]          ; V0 = A
    VLD  V1, [s1+0]          ; V1 = B

    ; Vector add
    VADD V2, V0, V1          ; V2 = A + B

    ; Store result
    VST  V2, [s2+0]          ; C = V2

    ; Print results: C[0]..C[3]
    ADDI s3, zero, 0         ; index
print_vec:
    ADDI t0, zero, 4
    BGE  s3, t0, done
    ADD  t1, s2, s3          ; &C[index]
    LW   t2, t1, 0           ; C[index]
    ; print as 2-digit decimal
    ADDI t3, zero, 10
    DIV  t4, t2, t3           ; tens digit
    REM  t5, t2, t3           ; ones digit
    ADDI t4, t4, 48
    SW   t4, zero, 0xFFF4    ; print tens
    ADDI t5, t5, 48
    SW   t5, zero, 0xFFF4    ; print ones
    ; space separator
    ADDI t0, zero, 32
    SW   t0, zero, 0xFFF4
    ADDI s3, s3, 1
    J print_vec

done:
    ADDI t0, zero, 10        ; newline
    SW   t0, zero, 0xFFF4
    HALT

; --- Data ---
.org 200
    .word 10                  ; A[0]
    .word 20                  ; A[1]
    .word 30                  ; A[2]
    .word 40                  ; A[3]
.org 204
    .word 1                   ; B[0]
    .word 2                   ; B[1]
    .word 3                   ; B[2]
    .word 4                   ; B[3]
.org 208
    .word 0                   ; C[0]
    .word 0                   ; C[1]
    .word 0                   ; C[2]
    .word 0                   ; C[3]
