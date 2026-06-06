import json

from src.hl_logic import HL


def test_ast_empty_function():
    h = HL()
    ast = h.dump_ast("function main() {}")
    assert ast == {"program": [{"function": "main", "body": []}]}


def test_ast_halt():
    h = HL()
    ast = h.dump_ast("function main() { halt; }")
    assert ast == {"program": [{"function": "main", "body": [{"halt": True}]}]}


def test_ast_let_init():
    h = HL()
    ast = h.dump_ast("function main() { let x = 42; halt; }")
    assert ast == {
        "program": [
            {
                "function": "main",
                "body": [
                    {"let": "x", "init": {"int": 42}},
                    {"halt": True},
                ],
            }
        ]
    }


def test_ast_let_no_init():
    h = HL()
    ast = h.dump_ast("function main() { let x; halt; }")
    assert ast == {"program": [{"function": "main", "body": [{"let": "x"}, {"halt": True}]}]}


def test_ast_assign():
    h = HL()
    ast = h.dump_ast("function main() { let x = 0; x = x + 1; halt; }")
    body = ast["program"][0]["body"]
    assert body[0] == {"let": "x", "init": {"int": 0}}
    assert body[1] == {
        "assign": "x",
        "value": {
            "binop": "+",
            "left": {"var": "x"},
            "right": {"int": 1},
        },
    }
    assert body[2] == {"halt": True}


def test_ast_if_else():
    h = HL()
    ast = h.dump_ast("function main() { if (1) { let x = 1; } else { let y = 2; } halt; }")
    body = ast["program"][0]["body"]
    assert body[0]["if"] == {"int": 1}
    assert body[0]["then"] == [{"let": "x", "init": {"int": 1}}]
    assert body[0]["else"] == [{"let": "y", "init": {"int": 2}}]
    assert body[1] == {"halt": True}


def test_ast_while():
    h = HL()
    ast = h.dump_ast("function main() { while (i < 10) { i = i + 1; } halt; }")
    body = ast["program"][0]["body"]
    assert body[0] == {
        "while": {
            "binop": "<",
            "left": {"var": "i"},
            "right": {"int": 10},
        },
        "body": [
            {
                "assign": "i",
                "value": {
                    "binop": "+",
                    "left": {"var": "i"},
                    "right": {"int": 1},
                },
            }
        ],
    }
    assert body[1] == {"halt": True}


def test_ast_print_str():
    h = HL()
    ast = h.dump_ast('function main() { print_str("hello"); halt; }')
    body = ast["program"][0]["body"]
    assert body[0] == {"expr_stmt": {"call": "print_str", "args": [{"string": "hello"}]}}
    assert body[1] == {"halt": True}


def test_ast_complex_expression():
    h = HL()
    ast = h.dump_ast("function main() { let x = (1 + 2) * 3; halt; }")
    body = ast["program"][0]["body"]
    expected = {
        "let": "x",
        "init": {
            "binop": "*",
            "left": {"binop": "+", "left": {"int": 1}, "right": {"int": 2}},
            "right": {"int": 3},
        },
    }
    assert body[0] == expected


def test_ast_bool_and_unary():
    h = HL()
    ast = h.dump_ast("function main() { let a = true; let b = !a; halt; }")
    body = ast["program"][0]["body"]
    assert body[0] == {"let": "a", "init": {"bool": True}}
    assert body[1] == {
        "let": "b",
        "init": {"unary": "!", "operand": {"var": "a"}},
    }


def test_ast_various_literals():
    h = HL()
    ast = h.dump_ast("function main() { let a = 0xFF; let b = 'A'; halt; }")
    body = ast["program"][0]["body"]
    assert body[0]["let"] == "a"
    assert body[0]["init"]["int"] == 255
    assert body[1]["let"] == "b"
    assert body[1]["init"]["char"] == 65


def test_ast_to_dict_json_serializable():
    h = HL()
    ast = h.dump_ast("function main() { halt; }")
    serialized = json.dumps(ast, ensure_ascii=False)
    assert isinstance(serialized, str)


def test_ast_human_readable_repr():
    h = HL()
    h.parse("function main() { halt; }")
    ast = h.get_ast()
    s = repr(ast)
    assert "program" in s
    assert "function" in s
    assert "main" in s
    assert "halt" in s
