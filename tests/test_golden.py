from __future__ import annotations

import contextlib
import io
import logging
import os
import tempfile
from pathlib import Path
from typing import Any,cast

import pytest
import yaml

import machine
import translator

MAX_LOG = 700
UPDATE_GOLDENS = os.environ.get("UPDATE_GOLDENS") == "1"

GOLDEN_DIR = Path(__file__).parent.parent / "golden"


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
    for yaml_path in sorted(GOLDEN_DIR.glob("**/*.yaml")):
        with open(yaml_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        cases.append((yaml_path, data))
    return cases


def run_test_case(in_source: str, in_stdin: str, limit: int) -> dict[str, Any]:
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

        with open(target + ".cmem", "rb") as f:
            cmem_data = f.read()
        trimmed = cmem_data.rstrip(b"\x00")
        out_code = trimmed.hex(" ").upper()

        with open(target + ".hex", encoding="utf-8") as f:
            out_code_hex = f.read()

        with open(target + ".mem", "rb") as f:
            mem_data = f.read()
        trimmed_mem = mem_data.rstrip(b"\x00")
        out_data = trimmed_mem.hex(" ").upper() if trimmed_mem else ""

        with open(target + ".mem.hex", encoding="utf-8") as f:
            out_data_hex = f.read()

        log = "\n".join(log_lines).replace("\r", "") + "EOF"

        return {
            "out_code": out_code,
            "out_code_hex": out_code_hex,
            "out_data": out_data,
            "out_data_hex": out_data_hex,
            "out_stdout": stdout_capture.getvalue().replace("\r", ""),
            "out_log": log,
        }


@pytest.mark.parametrize(("yaml_path", "golden"), load_golden_cases())
def test_translator_and_machine(yaml_path: Path, golden: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    in_source = golden.get("in_source")

    if in_source is None:
        pytest.skip("empty golden file")

    in_stdin = golden.get("in_stdin", "")
    limit = cast(int, golden.get("in_limit") or 6000)

    caplog.set_level(logging.DEBUG)
    caplog.handler.setFormatter(logging.Formatter("%(message)s"))

    actual = run_test_case(in_source, in_stdin, limit)

    actual_norm = {k: _make_single_line(v) for k, v in actual.items()}
    actual_norm["out_log"] = actual["out_log"].replace("\r", "")

    if UPDATE_GOLDENS:
        golden["out_code"] = actual_norm["out_code"]
        golden["out_code_hex"] = actual_norm["out_code_hex"]
        golden["out_data"] = actual_norm["out_data"]
        golden["out_data_hex"] = actual_norm["out_data_hex"]
        golden["out_stdout"] = actual_norm["out_stdout"]
        golden["out_log"] = actual_norm["out_log"]

        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(golden, f, allow_unicode=True, sort_keys=False, Dumper=SingleLineDumper)
        return

    assert actual_norm["out_code"] == golden["out_code"]
    assert actual_norm["out_code_hex"] == golden["out_code_hex"]
    assert actual_norm["out_data"] == golden["out_data"]
    assert actual_norm["out_data_hex"] == golden["out_data_hex"]
    assert actual_norm["out_stdout"] == golden["out_stdout"]
    assert actual_norm["out_log"] == golden["out_log"]
