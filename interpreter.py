import json
import sys

variables = {}
output = []

class InterpreterError(Exception):
    pass

def eval_expr(expr):
    if "const" in expr:
        return expr["const"]

    if "var" in expr:
        name = expr["var"]
        if name not in variables:
            raise InterpreterError(f'L0.State.Undefined_variable("{name}")')
        return variables[name]

    if "binop" in expr:
        op = expr["binop"]
        left = eval_expr(expr["left"])
        right = eval_expr(expr["right"])

        if op == "+":
            return left + right
        elif op == "-":
            return left - right
        elif op == "*":
            return left * right
        elif op == "/":
            if right == 0:
                raise InterpreterError("Division_by_zero")
            return left // right
        elif op == "%":
            if right == 0:
                raise InterpreterError("Division_by_zero")
            return left % right
        
        elif op == "==":
            return int(left == right)
        elif op == "!=":
            return int(left != right)
        elif op == "<":
            return int(left < right)
        elif op == "<=":
            return int(left <= right)
        elif op == ">":
            return int(left > right)
        elif op == ">=":
            return int(left >= right)

        elif op == "&&":
            return int(bool(left) and bool(right))
        elif op == "!!":
            return int(bool(left) or bool(right))


def execute(node):
    if node == "skip":
        return

    elif "assn" in node:
        name = node["assn"]["dst"]
        value = eval_expr(node["assn"]["src"])
        variables[name] = value

    elif "write" in node:
        value = eval_expr(node["write"])
        output.append(str(value))

    elif "seq" in node:
        execute(node["seq"]["left"])
        execute(node["seq"]["right"])

    elif "if" in node:
        condition = eval_expr(node["if"]["cond"])
        if condition:
            execute(node["if"]["then"])
        else:
            execute(node["if"]["else"])

    elif "while" in node:
        while eval_expr(node["while"]["cond"]):
            execute(node["while"]["body"])

    elif "read" in node:
        name = node["read"]
        try:
            value = int(input())
        except ValueError:
            raise InterpreterError('Input error: "decimal constant" expected')
        variables[name] = value

    elif "do" in node:
        execute(node["do"]["body"])
        while eval_expr(node["do"]["cond"]):
            execute(node["do"]["body"])

    
def main():
    filename = sys.argv[1]
    with open(filename, "r", encoding="utf-8") as file:
        ast = json.load(file)
    try:
        execute(ast)
        print("; ".join(output))
    except InterpreterError as error:
        print(error)


if __name__ == "__main__":
    main()