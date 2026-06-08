from __future__ import annotations

import struct
import tempfile
from pathlib import Path

import pytest

from src.translator import assemble, imm, main, rnum


def test_rnum() -> None:
    assert rnum("zero") == 0
    assert rnum("s0") == 18
    assert rnum("ra") == 1
    assert rnum("r5") == 5
    with pytest.raises(ValueError, match="bad register"):
        rnum("bad")


def test_imm() -> None:
    assert imm("42") == 42
    assert imm("0xFF") == 255
    assert imm("0X10") == 16


def test_assemble_halt() -> None:
    data, _lst = assemble("HALT")
    assert len(data) == 4
    assert data == struct.pack("<I", 0xFC000000)


def test_assemble_nop() -> None:
    data, _lst = assemble("NOP")
    assert len(data) == 4


def test_assemble_addi() -> None:
    data, _lst = assemble("ADDI s0, zero, 42")
    assert len(data) == 4


def test_assemble_with_label() -> None:
    src = """
    ADDI s0, zero, 10
loop:
    ADDI s0, s0, -1
    BNE zero, s0, loop
    HALT
"""
    data, _lst = assemble(src)
    assert len(data) == 16


def test_assemble_pseudo_mv() -> None:
    data, _lst = assemble("MV s0, s1")
    assert len(data) == 4


def test_assemble_pseudo_li_small() -> None:
    data, _lst = assemble("LI s0, 42")
    assert len(data) == 4


def test_assemble_org_word() -> None:
    src = """
.org 100
.word 1 2 3
"""
    data, _lst = assemble(src)
    assert len(data) == 12


def test_main_roundtrip() -> None:
    src = "ADDI s0, zero, 7\nHALT\n"
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        src_path = tmpdir / "test.asm"
        src_path.write_text(src, encoding="utf-8")
        n_bytes = main(str(src_path), str(tmpdir / "out"))
        assert n_bytes == 8
        bin_path = tmpdir / "out.bin"
        assert bin_path.exists()
        data = bin_path.read_bytes()
        assert len(data) == 8
