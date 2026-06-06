// HL vector version: uses array syntax to generate VLD/VADD/VST
// a = {1, 2, 3, 4}, b = {10, 20, 30, 40}
// c = a + b  => auto-generates VLD/VADD/VST
// Prints: "11 22 33 44\n"
function main() {
    let a = {1, 2, 3, 4};
    let b = {10, 20, 30, 40};
    let c = a + b;
    let i = 0;
    while (i < 4) {
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
