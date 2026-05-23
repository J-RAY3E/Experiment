; Print H e l l o via memory-mapped I/O
.org 0
    LI r1, 72     ; 'H'
    SW r1, zero, 0xFFF4
    LI r1, 101    ; 'e'
    SW r1, zero, 0xFFF4
    LI r1, 108    ; 'l'
    SW r1, zero, 0xFFF4
    SW r1, zero, 0xFFF4
    LI r1, 111    ; 'o'
    SW r1, zero, 0xFFF4
    LI r1, 10     ; newline
    SW r1, zero, 0xFFF4
    HALT
