function main() {
    let arr[10] = {};
    let n = 0;
    let num = 0;
    let have = 0;
    let reading = 1;
    while (reading) {
        let c = read();
        if (c == 0) { reading = 0; }
        if (c == 10) {
            if (have) {
                arr[n] = num;
                n = n + 1;
                num = 0;
                have = 0;
            }
            reading = 0;
        }
        if (c == 32 || c == 13) {
            if (have) {
                arr[n] = num;
                n = n + 1;
                num = 0;
                have = 0;
            }
        }
        if (!(c == 0 || c == 10 || c == 32 || c == 13)) {
            num = num * 10 + (c - 48);
            have = 1;
        }
    }
    let i = 0;
    while (i < n - 1) {
        let j = 0;
        while (j < n - 1 - i) {
            if (arr[j] > arr[j + 1]) {
                let tmp = arr[j];
                arr[j] = arr[j + 1];
                arr[j + 1] = tmp;
            }
            j = j + 1;
        }
        i = i + 1;
    }
    i = 0;
    while (i < n) {
        print_num(arr[i]);
        if (i < n - 1) { print(32); }
        i = i + 1;
    }
    print(10);
    halt;
}
