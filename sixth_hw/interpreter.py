import json
import sys

from common import (
    InputReader, InterpreterError, SExpression, State, binop,
    elements, format_value, get_element, literal_value, match_pattern, set_element, truth,
)


class Interpreter(State):
    def __init__(self, program):
        super().__init__()
        self.program = program
        self.reader = InputReader()

    def eval_expr(self, expr):
        if "const" in expr:
            return literal_value(expr["const"])
        if "string" in expr:
            return literal_value(expr["string"])
        if "var" in expr:
            return self.load(expr["var"])
        if "binop" in expr:
            left = self.eval_expr(expr["left"])
            right = self.eval_expr(expr["right"])
            return binop(expr["binop"], left, right)
        if "array" in expr:
            return [self.eval_expr(item) for item in expr["array"]]
        if "sexp" in expr:
            return SExpression(expr["sexp"], [self.eval_expr(x) for x in expr["args"]])
        if "elem" in expr:
            value = self.eval_expr(expr["elem"])
            index = self.eval_expr(expr["index"])
            return get_element(value, index)
        if "length" in expr:
            return len(elements(self.eval_expr(expr["length"])))
        raise InterpreterError(f"Unknown expression: {expr!r}")

    def execute(self, node):
        if node == "skip":
            return
        if "seq" in node:
            self.execute(node["seq"]["left"])
            self.execute(node["seq"]["right"])
        elif "assn" in node:
            stmt = node["assn"]
            self.store(stmt["dst"], self.eval_expr(stmt["src"]))
        elif "set" in node:
            stmt = node["set"]
            value = self.eval_expr(stmt["dst"])
            index = self.eval_expr(stmt["idx"])
            item = self.eval_expr(stmt["value"])
            set_element(value, index, item)
        elif "read" in node:
            self.store(node["read"], self.reader.read())
        elif "write" in node:
            print(format_value(self.eval_expr(node["write"])))
        elif "if" in node:
            stmt = node["if"]
            branch = "then" if truth(self.eval_expr(stmt["cond"])) else "else"
            self.execute(stmt.get(branch, "skip"))
        elif "while" in node:
            stmt = node["while"]
            while truth(self.eval_expr(stmt["cond"])):
                self.execute(stmt["body"])
        elif "do" in node:
            stmt = node["do"]
            while True:
                self.execute(stmt["body"])
                if not truth(self.eval_expr(stmt["cond"])):
                    break
        elif "switch" in node:
            stmt = node["switch"]
            value = self.eval_expr(stmt["scrutinee"])
            for branch in stmt["branches"]:
                bindings = {}
                if match_pattern(branch["pattern"], value, bindings):
                    self.scopes.append(bindings)
                    try:
                        self.execute(branch["branch"])
                    finally:
                        self.scopes.pop()
                    return
            raise InterpreterError(f"No matching pattern for {format_value(value)}")
        else:
            raise InterpreterError(f"Unknown statement: {node!r}")

    def run(self):
        self.execute(self.program)


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 interpreter.py <program.json>", file=sys.stderr)
        sys.exit(1)
    try:
        with open(sys.argv[1], encoding="utf-8") as file:
            program = json.load(file)
        Interpreter(program).run()
    except (OSError, ValueError, InterpreterError) as error:
        print(f"Interpreter error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
