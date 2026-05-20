; hello — print "Hello, World!\n" via memory-mapped I/O (pstr)
; Demonstrates: Pascal string in data memory, loop, MMIO OUT_PORT
.org 0
    ; s0 = address of the pstr in data memory
    ADDI s0, zero, 100
    ; s1 = string length (first word of pstr)
    LW   s1, s0, 0
    ; s2 = index = 0
    ADDI s2, zero, 0

print_loop:
    BGE  s2, s1, done
    ADDI t0, s0, 1          ; t0 = &str[0] (skip length word)
    ADD  t1, t0, s2         ; t1 = &str[index]
    LW   t2, t1, 0          ; t2 = str[index]
    SW   t2, zero, 0xFFF4   ; write to OUT_PORT
    ADDI s2, s2, 1
    J print_loop

done:
    HALT

; --- Data segment ---
.org 100
    .string "Hello, World!\n"
