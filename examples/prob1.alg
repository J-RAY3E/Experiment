function main() {
    let sum = 0;
    let i = 0;
    while (i < 100) {
        if (i % 3 == 0) {
            sum = sum + i;
        } else {
            if (i % 5 == 0) {
                sum = sum + i;
            }
        }
        i = i + 1;
    }
    let t = sum;
    let d = 1000;
    while (d > 0) {
        let q = t / d;
        print(q + 48);
        t = t % d;
        d = d / 10;
    }
    print(10);
    halt;
}
