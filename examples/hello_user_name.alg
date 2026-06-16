function main() {
    let name[256] = {};
    let i = 0;
    let running = 1;
    print_str("What is your name? ");
    while (running) {
        let c = read();
        if (c == 0) { running = 0; }
        if (c == 10) { running = 0; }
        if (running) {
            name[i] = c;
            i = i + 1;
        }
    }
    print_str("Hello, ");
    let j = 0;
    while (j < i) {
        print(name[j]);
        j = j + 1;
    }
    print_str("!\n");
    halt;
}
