; hello_user_name — ask name, read it, greet the user
; Demonstrates: pstr, stream I/O read+write, loops
;
; Flow: print "What is your name?\n", read name, print "Hello, " + name + "!\n"
.org 0
    ; --- print prompt (pstr at data offset) ---
    LUI s0, 0               ; s0 = 0 (data base for prompt)
    ADDI s0, s0, 200        ; s0 = 200 (prompt_str address)
    LW  s1, s0, 0           ; s1 = prompt length
    ADDI s2, zero, 0        ; s2 = index
print_prompt:
    BGE s2, s1, read_name
    ADDI t0, s0, 1
    ADD  t1, t0, s2
    LW   t2, t1, 0
    SW   t2, zero, 0xFFF4
    ADDI s2, s2, 1
    J print_prompt

read_name:
    ; --- read name chars into buffer at 240 ---
    ADDI s3, zero, 240      ; s3 = name buffer base
    ADDI s4, zero, 0        ; s4 = name length
read_loop:
    LW   t0, zero, 0xFFF0   ; read char
    BEQZ t0, print_hello    ; EOF -> done reading
    ADDI t1, zero, 10       ; newline
    BEQ  t0, t1, print_hello ; newline -> done
    ; store char: buffer[1 + s4] = t0
    ADDI t2, s3, 1
    ADD  t3, t2, s4
    SW   t0, t3, 0
    ADDI s4, s4, 1
    J read_loop

print_hello:
    ; store name length
    SW   s4, s3, 0

    ; --- print "Hello, " (pstr at 220) ---
    ADDI s0, zero, 220      ; s0 = hello_str address
    LW   s1, s0, 0          ; s1 = hello length
    ADDI s2, zero, 0
print_hello_str:
    BGE  s2, s1, print_name_chars
    ADDI t0, s0, 1
    ADD  t1, t0, s2
    LW   t2, t1, 0
    SW   t2, zero, 0xFFF4
    ADDI s2, s2, 1
    J print_hello_str

print_name_chars:
    ; --- print the name ---
    ADDI s2, zero, 0
print_name_loop:
    BGE  s2, s4, print_end
    ADDI t0, s3, 1
    ADD  t1, t0, s2
    LW   t2, t1, 0
    SW   t2, zero, 0xFFF4
    ADDI s2, s2, 1
    J print_name_loop

print_end:
    ; print "!\n"
    ADDI t0, zero, 33       ; '!'
    SW   t0, zero, 0xFFF4
    ADDI t0, zero, 10       ; '\n'
    SW   t0, zero, 0xFFF4
    HALT

; --- Data segment ---
.org 200
    .string "What is your name?\n"

.org 220
    .string "Hello, "
