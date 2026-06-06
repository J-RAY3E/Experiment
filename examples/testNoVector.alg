function main() {
    let i = 0;
    let a = 0;
    let b = 0;
    let c = 0;
    let tens = 0;
    let ones = 0;

    while (i < 4) {
        if (i == 0) { a = 1;  b = 10; }
        if (i == 1) { a = 2;  b = 20; }
        if (i == 2) { a = 3;  b = 30; }
        if (i == 3) { a = 4;  b = 40; }

        c = a + b;
        tens = c / 10;
        ones = c % 10;

        print(tens + 48);
        print(ones + 48);
        print(32);

        i = i + 1;
    }

    print(10);
    halt;
}
