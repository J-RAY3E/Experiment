"""AST nodes for the JavaScript-like high-level language.

Each node implements ``to_dict()`` to produce a human-readable, JSON-serializable
representation. The whole tree can be dumped via ``repr(node)`` to inspect the
AST in tests and golden output (see ``tests/test_ast.py``).

The structure is intentionally simple (no visitor pattern, no generic typing)
because the only consumer is the single-pass compiler in ``hl_logic.py``.
"""

from __future__ import annotations

import json
from typing import Any


class ASTNode:
    """Base class for every AST node."""

    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    def __repr__(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class Program(ASTNode):
    def __init__(self, functions: list[FunctionDef]) -> None:
        self.functions = functions

    def to_dict(self) -> dict[str, Any]:
        return {"program": [f.to_dict() for f in self.functions]}


class FunctionDef(ASTNode):
    def __init__(self, name: str, body: list[ASTNode]) -> None:
        self.name = name
        self.body = body

    def to_dict(self) -> dict[str, Any]:
        return {"function": self.name, "body": [s.to_dict() for s in self.body]}


class LetStmt(ASTNode):
    def __init__(self, name: str, init: ASTNode | None = None, array_size: ASTNode | None = None) -> None:
        self.name = name
        self.init = init
        self.array_size = array_size

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"let": self.name}
        if self.init is not None:
            d["init"] = self.init.to_dict()
        if self.array_size is not None:
            d["array_size"] = self.array_size.to_dict()
        return d


class AssignStmt(ASTNode):
    def __init__(self, name: str, value: ASTNode) -> None:
        self.name = name
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"assign": self.name, "value": self.value.to_dict()}


class IndexAssignStmt(ASTNode):
    def __init__(self, target: IndexExpr, value: ASTNode) -> None:
        self.target = target
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"index_assign": self.target.to_dict(), "value": self.value.to_dict()}


class IfStmt(ASTNode):
    def __init__(self, cond: ASTNode, then_body: list[ASTNode], else_body: list[ASTNode] | None = None) -> None:
        self.cond = cond
        self.then_body = then_body
        self.else_body = else_body

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"if": self.cond.to_dict(), "then": [s.to_dict() for s in self.then_body]}
        if self.else_body:
            d["else"] = [s.to_dict() for s in self.else_body]
        return d


class WhileStmt(ASTNode):
    def __init__(self, cond: ASTNode, body: list[ASTNode]) -> None:
        self.cond = cond
        self.body = body

    def to_dict(self) -> dict[str, Any]:
        return {"while": self.cond.to_dict(), "body": [s.to_dict() for s in self.body]}


class ReturnStmt(ASTNode):
    def __init__(self, value: ASTNode | None = None) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"return": None}
        if self.value is not None:
            d["return"] = self.value.to_dict()
        return d


class ExprStmt(ASTNode):
    def __init__(self, expr: ASTNode) -> None:
        self.expr = expr

    def to_dict(self) -> dict[str, Any]:
        return {"expr_stmt": self.expr.to_dict()}


class BlockStmt(ASTNode):
    def __init__(self, body: list[ASTNode]) -> None:
        self.body = body

    def to_dict(self) -> dict[str, Any]:
        return {"block": [s.to_dict() for s in self.body]}


class HaltStmt(ASTNode):
    def to_dict(self) -> dict[str, Any]:
        return {"halt": True}


class ArrayLiteral(ASTNode):
    def __init__(self, elements: list[ASTNode]) -> None:
        self.elements = elements

    def to_dict(self) -> dict[str, Any]:
        return {"array": [e.to_dict() for e in self.elements]}


class IndexExpr(ASTNode):
    def __init__(self, array: ASTNode, index: ASTNode) -> None:
        self.array = array
        self.index = index

    def to_dict(self) -> dict[str, Any]:
        return {"index": self.array.to_dict(), "at": self.index.to_dict()}


class IntLiteral(ASTNode):
    def __init__(self, value: int) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"int": self.value}


class BoolLiteral(ASTNode):
    def __init__(self, value: bool) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"bool": self.value}


class StringLiteral(ASTNode):
    def __init__(self, value: str) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"string": self.value}


class CharLiteral(ASTNode):
    def __init__(self, value: int) -> None:
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {"char": self.value}


class VarRef(ASTNode):
    def __init__(self, name: str) -> None:
        self.name = name

    def to_dict(self) -> dict[str, Any]:
        return {"var": self.name}


class BinaryOp(ASTNode):
    def __init__(self, op: str, left: ASTNode, right: ASTNode) -> None:
        self.op = op
        self.left = left
        self.right = right

    def to_dict(self) -> dict[str, Any]:
        return {"binop": self.op, "left": self.left.to_dict(), "right": self.right.to_dict()}


class UnaryOp(ASTNode):
    def __init__(self, op: str, operand: ASTNode) -> None:
        self.op = op
        self.operand = operand

    def to_dict(self) -> dict[str, Any]:
        return {"unary": self.op, "operand": self.operand.to_dict()}


class CallExpr(ASTNode):
    def __init__(self, name: str, args: list[ASTNode]) -> None:
        self.name = name
        self.args = args

    def to_dict(self) -> dict[str, Any]:
        return {"call": self.name, "args": [a.to_dict() for a in self.args]}


__all__ = [
    "ASTNode",
    "ArrayLiteral",
    "AssignStmt",
    "BinaryOp",
    "BlockStmt",
    "BoolLiteral",
    "CallExpr",
    "CharLiteral",
    "ExprStmt",
    "FunctionDef",
    "HaltStmt",
    "IfStmt",
    "IndexAssignStmt",
    "IndexExpr",
    "IntLiteral",
    "LetStmt",
    "Program",
    "ReturnStmt",
    "StringLiteral",
    "UnaryOp",
    "VarRef",
    "WhileStmt",
]
