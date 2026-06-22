function main() {
    let name[256] = {};
    print_str("What is your name? ");
    readln(name);
    print_str("Hello, ");
    let j = 0;
    while (j < 256) {
        if (name[j] == 0) { j = 256; }
        if (name[j] == 10) { j = 256; }
        if (j < 256) {
            print(name[j]);
            j = j + 1;
        }
    }
    print_str("!\n");
    halt;
}
