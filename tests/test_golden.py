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

SRC_MAP = {
    "hello_test": "hello.alg",
    "hello_user_name_test": "hello_user_name.alg",
    "cat_test": "cat.alg",
    "alg1_test": "alg1.alg",
    "sort_test": "sort.alg",
    "function_call_test": "function_call.alg",
    "double_precision_test": "double_precision.alg",
}


def _yaml_scalar(value: str) -> str:
    if not value:
        return '""'
    lines = value.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    if len(lines) <= 1:
        esc = value.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
        return f'"{esc}"'
    out = "|\n"
    for line in lines:
        out += f"  {line}\n" if line else "\n"
    return out


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for k, v in data.items():
            if k in ("in_stdin", "out_stdout") and isinstance(v, str):
                esc = v.replace("\\", "\\\\").replace('"', '\\"').replace("\r", "\\r").replace("\n", "\\n")
                f.write(f'{k}: "{esc}"\n')
            elif isinstance(v, str) and "\n" in v:
                f.write(f"{k}: {_yaml_scalar(v)}")
            elif isinstance(v, str):
                f.write(f"{k}: {v}\n")
            elif isinstance(v, bool):
                f.write(f"{k}: {'true' if v else 'false'}\n")
            elif isinstance(v, int):
                f.write(f"{k}: {v}\n")
            else:
                f.write(f"{k}: {v}\n")


def _make_single_line(data: str) -> str:
    return data.replace("\n", r"\n").replace("\r", "")


def _recompile_alg(alg_name: str) -> tuple[str | None, str | None]:
    src_path = EXAMPLES_DIR / alg_name
    if not src_path.exists():
        return None, None
    import subprocess
    import sys

    asm_path = Path(tempfile.mkdtemp()) / "out.asm"
    r = subprocess.run(
        [sys.executable, "-m", "src.cli", "compile", str(src_path), str(asm_path)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if r.returncode != 0:
        return None, None
    return src_path.read_text(), asm_path.read_text()


def load_golden_cases() -> list[tuple[Path, dict[str, Any]]]:
    cases = []
    for yaml_path in sorted(GOLDEN_DIR.glob("*.yaml")):
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

        log = "\n".join(log_lines).replace("\r", "") + "EOF"

        return {
            "out_stdout": stdout_capture.getvalue().replace("\r", ""),
            "out_log": log,
            "halted": m.halted,
        }


@pytest.mark.parametrize(("yaml_path", "golden"), load_golden_cases())
def test_translator_and_machine(yaml_path: Path, golden: dict[str, Any], caplog: pytest.LogCaptureFixture) -> None:
    in_source: str | None = cast(str | None, golden.get("asm_src") or golden.get("in_src") or golden.get("in_source"))
    source_file: str | None = cast(str | None, golden.get("src") or golden.get("source_file"))

    if in_source is None and source_file is None:
        pytest.skip("no source provided")

    if UPDATE_GOLDENS:
        name = yaml_path.stem
        alg_name = SRC_MAP.get(name)
        if alg_name:
            _alg_src, compiled = _recompile_alg(alg_name)
            if compiled:
                in_source = compiled

    if in_source is None and source_file:
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

    actual_norm = {k: _make_single_line(v) for k, v in actual.items() if isinstance(v, str)}
    actual_norm["out_log"] = actual["out_log"].replace("\r", "")
    actual_norm["out_stdout"] = actual["out_stdout"].replace("\r", "")

    if UPDATE_GOLDENS:
        name = yaml_path.stem
        in_stdin = golden.get("in_stdin", "")
        limit = cast(int, golden.get("max_ticks") or 6000)

        alg_name = SRC_MAP.get(name)
        alg_src, recompiled = _recompile_alg(alg_name) if alg_name else (None, None)

        new_data: dict[str, Any] = {}
        new_data["max_ticks"] = golden.get("max_ticks") or limit

        if recompiled:
            new_data["src"] = alg_name
            if alg_src is not None:
                new_data["alg_src"] = alg_src
            new_data["asm_src"] = recompiled
            actual = run_test_case(recompiled, in_stdin, limit)
            actual_norm = {k: _make_single_line(v) for k, v in actual.items() if isinstance(v, str)}
            actual_norm["out_log"] = actual["out_log"].replace("\r", "")
            actual_norm["out_stdout"] = actual["out_stdout"].replace("\r", "")
        else:
            new_data["src"] = alg_name if alg_name else "N/A (manual assembly)"
            new_data["asm_src"] = golden.get("asm_src") or golden.get("in_src") or golden.get("in_source", "")

        new_data["in_stdin"] = in_stdin
        new_data["out_stdout"] = actual_norm["out_stdout"]
        new_data["halted"] = actual.get("halted", True)
        new_data["out_log"] = actual_norm["out_log"]

        _write_yaml(yaml_path, new_data)
        return

    assert actual_norm["out_stdout"].rstrip("\n") == golden["out_stdout"].rstrip("\n")
    assert actual_norm["out_log"].rstrip("\n") == golden["out_log"].rstrip("\n")
    if "halted" in golden:
        assert actual.get("halted") == golden["halted"]
