; sort — bubble sort of numbers loaded as pstr-style (length-prefixed array)
; Input: numbers read from stream as ASCII digits separated by spaces
; Output: sorted numbers printed as ASCII digits separated by spaces
; Demonstrates: arrays in data memory, nested loops, comparison
.org 0
    ; --- Read numbers from input into array at addr 300 ---
    ADDI s0, zero, 300      ; s0 = array base
    ADDI s1, zero, 0        ; s1 = count
    ADDI s5, zero, 0        ; s5 = current number accumulator
    ADDI s6, zero, 0        ; s6 = has_digits flag

read_nums:
    LW   t0, zero, 0xFFF0   ; read char
    BEQZ t0, store_last      ; EOF
    ADDI t1, zero, 32        ; space
    BEQ  t0, t1, got_sep
    ADDI t1, zero, 10        ; newline
    BEQ  t0, t1, got_sep
    ; it's a digit: acc = acc * 10 + (ch - 48)
    ADDI t2, zero, 10
    MUL  s5, s5, t2
    ADDI t0, t0, -48
    ADD  s5, s5, t0
    ADDI s6, zero, 1
    J read_nums

got_sep:
    BEQZ s6, read_nums       ; skip consecutive separators
    ; store number
    ADDI t3, s0, 1
    ADD  t4, t3, s1
    SW   s5, t4, 0
    ADDI s1, s1, 1
    ADDI s5, zero, 0
    ADDI s6, zero, 0
    J read_nums

store_last:
    BEQZ s6, sort_start
    ADDI t3, s0, 1
    ADD  t4, t3, s1
    SW   s5, t4, 0
    ADDI s1, s1, 1

sort_start:
    ; store length
    SW   s1, s0, 0

    ; --- Bubble sort ---
    ; for i = 0 to n-2
    ADDI s2, zero, 0        ; s2 = i
outer:
    ADDI t0, s1, -1
    BGE  s2, t0, print_arr
    ; for j = 0 to n-2-i
    ADDI s3, zero, 0        ; s3 = j
    SUB  s4, t0, s2         ; s4 = n-1-i
inner:
    BGE  s3, s4, next_i
    ; load arr[j] and arr[j+1]
    ADDI t0, s0, 1
    ADD  t1, t0, s3         ; &arr[j]
    LW   t2, t1, 0          ; arr[j]
    LW   t3, t1, 1          ; arr[j+1]
    BLE  t2, t3, no_swap
    ; swap
    SW   t3, t1, 0
    SW   t2, t1, 1
no_swap:
    ADDI s3, s3, 1
    J inner
next_i:
    ADDI s2, s2, 1
    J outer

print_arr:
    ; --- Print sorted array as space-separated decimal numbers ---
    ADDI s2, zero, 0        ; index
print_loop:
    BGE  s2, s1, finish
    ; load arr[s2]
    ADDI t0, s0, 1
    ADD  t1, t0, s2
    LW   s5, t1, 0          ; s5 = number to print

    ; print number as decimal (up to 5 digits for simplicity)
    ; find leading divisor
    ADDI s6, zero, 1        ; divisor
    MV   s7, s5
find_div:
    ADDI t0, zero, 10
    BGE  s6, s7, print_digits
    MUL  s6, s6, t0
    J find_div

print_digits:
    ; s6 might be 10x too big, fix
    ADDI t0, zero, 10
    DIV  s6, s6, t0
    BEQZ s6, zero_case
digit_loop:
    BEQZ s6, next_num
    DIV  t0, s5, s6          ; digit
    ADDI t1, t0, 48          ; ASCII
    SW   t1, zero, 0xFFF4
    MUL  t2, t0, s6
    SUB  s5, s5, t2
    ADDI t0, zero, 10
    DIV  s6, s6, t0
    J digit_loop

zero_case:
    ADDI t0, zero, 48
    SW   t0, zero, 0xFFF4

next_num:
    ; print space (unless last)
    ADDI t0, s2, 1
    BGE  t0, s1, no_space
    ADDI t0, zero, 32       ; space
    SW   t0, zero, 0xFFF4
no_space:
    ADDI s2, s2, 1
    J print_loop

finish:
    ADDI t0, zero, 10       ; newline
    SW   t0, zero, 0xFFF4
    HALT
