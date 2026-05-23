"""Golden test runner for the RISC-IV processor.

Each subdirectory in golden/ is a test case containing:
  - source.asm          — assembly source code
  - input.txt           — input stream data (may be empty)
  - expected_output.txt — expected output from the processor

The runner assembles the source, simulates it, and compares the actual
output against expected_output.txt.  It also saves the processor journal
for each test case.

Usage:
    python tests/test_golden.py           # run all golden tests
    python tests/test_golden.py hello     # run only the 'hello' test
"""

import os
import sys

import yaml

# Ensure project root is on the path
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

# Force block style for multi-line strings
def str_presenter(dumper, data):
    if '\n' in data:
        return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
    return dumper.represent_scalar('tag:yaml.org,2002:str', data)

yaml.add_representer(str, str_presenter)

from src.assembler import write_binary  # noqa: E402
from src.Machine import Machine  # noqa: E402

GOLDEN_DIR = os.path.join(ROOT, "golden")
MAX_TICKS = 50_000_000


def discover_cases(filter_name=None):
    """Find all test case directories in golden/."""
    cases = []
    if not os.path.isdir(GOLDEN_DIR):
        return cases
    for name in sorted(os.listdir(GOLDEN_DIR)):
        path = os.path.join(GOLDEN_DIR, name)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "source.asm")):
            if filter_name and name != filter_name:
                continue
            cases.append(name)
    return cases


def run_case(name, update=False):
    """Assemble, simulate, and compare output for one test case.

    Returns (passed: bool, actual_output: str, expected_output: str, ticks: int).
    """
    base = os.path.join(GOLDEN_DIR, name)
    src_path = os.path.join(base, "source.asm")
    inp_path = os.path.join(base, "input.txt")
    exp_path = os.path.join(base, "expected_output.txt")

    with open(src_path, encoding="utf-8") as f:
        source = f.read()

    input_text = ""
    if os.path.exists(inp_path):
        with open(inp_path, encoding="utf-8") as f:
            input_text = f.read()

    expected = ""
    if os.path.exists(exp_path):
        with open(exp_path, encoding="utf-8") as f:
            expected = f.read()

    # Assemble
    bin_path = os.path.join(base, "program.bin")
    lst_path = os.path.join(base, "program.lst")
    write_binary(source, bin_path, lst_path)

    # Simulate
    m = Machine(bin_path, lst_path, input_text)
    actual = m.run(max_ticks=MAX_TICKS)

    # Save journal
    journal_path = os.path.join(base, "journal.log")
    journal = m.get_journal()
    with open(journal_path, "w", encoding="utf-8") as f:
        f.write(journal)
        f.write(f"\n\nTotal ticks: {m.tick_count}\n")

    if update:
        with open(exp_path, "w", encoding="utf-8") as f:
            f.write(actual)
        return True, actual, actual, m.tick_count

    passed = actual.rstrip() == expected.rstrip()
    return passed, actual, expected, m.tick_count


def main():
    update = "--update" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--update"]
    filter_name = args[0] if len(args) > 0 else None
    cases = discover_cases(filter_name)

    if not cases:
        print("No golden test cases found.")
        sys.exit(1)

    total = len(cases)
    passed_count = 0
    failed = []

    print(f"Running {total} golden test(s)...\n")

    for name in cases:
        try:
            ok, actual, expected, ticks = run_case(name, update=update)
        except Exception as e:
            print(f"  FAIL  {name}: {e}")
            failed.append(name)
            continue

        if ok:
            print(f"  PASS  {name}  ({ticks} ticks)")
            passed_count += 1
        else:
            print(f"  FAIL  {name}  ({ticks} ticks)")
            print(f"        expected: {repr(expected.rstrip()[:80])}")
            print(f"        actual:   {repr(actual.rstrip()[:80])}")
            failed.append(name)

    print(f"\n{passed_count}/{total} passed")
    if failed:
        print(f"Failed: {', '.join(failed)}")
    sys.exit(0 if not failed else 1)


if __name__ == "__main__":
    main()
