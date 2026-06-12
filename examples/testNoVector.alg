function main() {
    let a = {1, 2, 3, 4};
    let b = {10, 20, 30, 40};
    let c[4];
    let i = 0;

    while (i < 4) {
        c[i] = a[i] + b[i];
        let tens = c[i] / 10;
        let ones = c[i] % 10;
        print(tens + 48);
        print(ones + 48);
        print(32);
        i = i + 1;
    }

    print(10);
    halt;
}
