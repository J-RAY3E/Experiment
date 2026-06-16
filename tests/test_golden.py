from __future__ import annotations

import contextlib
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

import machine
import translator

MAX_LOG = 700
UPDATE_GOLDENS = os.environ.get("UPDATE_GOLDENS") == "1"

GOLDEN_DIR = Path(__file__).parent.parent / "golden"
EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class SingleLineDumper(yaml.SafeDumper):
    def represent_str(self, data: str):
        if "\n" in data:
            return self.represent_scalar("tag:yaml.org,2002:str", data, style="|")
        return self.represent_scalar("tag:yaml.org,2002:str", data)


SingleLineDumper.add_representer(str, SingleLineDumper.represent_str)


def _make_single_line(data: str) -> str:
    return data.replace("\n", r"\n").replace("\r", "")


def load_golden_cases() -> list[tuple[Path, dict[str, Any]]]:
    cases = []
    for yaml_path in sorted(GOLDEN_DIR.glob("*.yaml")):
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cases.append((yaml_path, data))
    return cases


def run_test_case(in_source: str, in_stdin: str, limit: int) -> dict[str, str]:
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        source = tmpdir / "source.asm"
        target = str(tmpdir / "source")

        with open(source, "w", encoding="utf-8") as f:
            f.write(in_source)

        stdout_capture = io.StringIO()
        with contextlib.redirect_stdout(stdout_capture):
            translator.main(str(source), target)

            bin_path = target + ".bin"
            lst_candidate = Path(target + ".lst")
            lst_path: str | None = str(lst_candidate) if lst_candidate.exists() else None

            m = machine.Machine(bin_path, lst_path, in_stdin)
            out = m.run(max_ticks=limit)
            m.write_outputs(target)
            print(out, end="")

        log_lines = m.get_journal().split("\n")[:MAX_LOG]
        for line in log_lines:
            logging.info(line)

        log = "\n".join(log_lines).replace("\r", "") + "EOF"

        return {
            "out_stdout": stdout_capture.getvalue().replace("\r", ""),
            "out_log": log,
        }


@pytest.mark.parametrize(("yaml_path", "golden"), load_golden_cases())
def test_translator_and_machine(yaml_path: Path, golden: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    in_source: str | None = cast(str | None, golden.get("in_source"))
    source_file: str | None = cast(str | None, golden.get("source_file"))

    if in_source is None and source_file is None:
        pytest.skip("no source provided")

    if source_file:
        src_path = EXAMPLES_DIR / source_file
        if not src_path.exists():
            src_path = EXAMPLES_DIR.parent / source_file
        with open(src_path, encoding="utf-8") as f:
            in_source = f.read()

    assert in_source is not None
    in_stdin: str = golden.get("in_stdin", "")
    limit: int = cast(int, golden.get("max_ticks") or 6000)

    caplog.set_level(logging.DEBUG)
    caplog.handler.setFormatter(logging.Formatter("%(message)s"))

    actual = run_test_case(in_source, in_stdin, limit)

    actual_norm = {k: _make_single_line(v) for k, v in actual.items()}
    actual_norm["out_log"] = actual["out_log"].replace("\r", "")

    if UPDATE_GOLDENS:
        golden["out_stdout"] = actual_norm["out_stdout"]
        golden["out_log"] = actual_norm["out_log"]

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(golden, f, allow_unicode=True, sort_keys=False, Dumper=SingleLineDumper)
        return

    assert actual_norm["out_stdout"] == golden["out_stdout"]
    assert actual_norm["out_log"] == golden["out_log"]
