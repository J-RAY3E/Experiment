function main() {
    let max = 0;
    let a = 999;
    while (a > 99) {
        if (a * 999 > max) {
            let b = 999;
            while (b > 99) {
                let p = a * b;
                if (p > max) {
                    let n = p;
                    let rev = 0;
                    while (n > 0) {
                        let d = n % 10;
                        rev = rev * 10 + d;
                        n = n / 10;
                    }
                    if (rev == p) {
                        max = p;
                    }
                } else {
                    b = 99;
                }
                b = b - 1;
            }
        } else {
            a = 99;
        }
        a = a - 1;
    }
    let t = max;
    let d = 1;
    while (t > 0) {
        t = t / 10;
        d = d * 10;
    }
    while (d > 1) {
        d = d / 10;
        t = max / d;
        print(t + 48);
        max = max % d;
    }
    print(10);
    halt;
}
