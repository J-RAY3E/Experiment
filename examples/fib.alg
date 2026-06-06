function main() {
    let a = 0;
    let b = 1;
    let i = 0;
    while (i < 10) {
        print(a + 48);
        print(32);
        let c = a + b;
        a = b;
        b = c;
        i = i + 1;
    }
    print(10);
    halt;
}
