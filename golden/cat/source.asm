; cat — echo input to output until EOF (char == 0)
; Demonstrates: stream I/O, memory-mapped IN_PORT / OUT_PORT
.org 0
loop:
    LW   t0, zero, 0xFFF0   ; read char from IN_PORT
    BEQZ t0, done            ; if 0 (EOF), stop
    SW   t0, zero, 0xFFF4   ; write char to OUT_PORT
    J loop
done:
    HALT
