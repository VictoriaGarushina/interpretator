import json
import sys


class InterpreterError(Exception):
    pass


class Interpreter:
    def __init__(self, program):
        if not isinstance(program, list):
            raise InterpreterError("Program must be a JSON array")

        self.program = program
        self.stack = []
        self.variables = {}
        self.labels = {}
        self.pc = 0

        self.collect_labels()

    def collect_labels(self):
        for index, instruction in enumerate(self.program):
            if not isinstance(instruction, dict):
                continue

            if "LABEL" not in instruction:
                continue

            label = instruction["LABEL"]

            if label in self.labels:
                raise InterpreterError(
                    f'Duplicate label: "{label}"'
                )

            self.labels[label] = index

    def pop(self):
        if not self.stack:
            raise InterpreterError("Stack is empty")

        return self.stack.pop()

    def jump(self, label):
        if label not in self.labels:
            raise InterpreterError(
                f'Unknown label: "{label}"'
            )

        self.pc = self.labels[label]

    def execute_binop(self, operator):
        right = self.pop()
        left = self.pop()

        if operator == "+":
            result = left + right
        elif operator == "-":
            result = left - right
        elif operator == "*":
            result = left * right
        elif operator == "/":
            if right == 0:
                raise InterpreterError("Division by zero")
            result = left // right
        elif operator == "%":
            if right == 0:
                raise InterpreterError("Division by zero")
            result = left % right
        elif operator == "==":
            result = int(left == right)
        elif operator == "!=":
            result = int(left != right)
        elif operator == "<":
            result = int(left < right)
        elif operator == "<=":
            result = int(left <= right)
        elif operator == ">":
            result = int(left > right)
        elif operator == ">=":
            result = int(left >= right)
        elif operator == "&&":
            result = int(bool(left) and bool(right))
        elif operator in ("||", "!!"):
            result = int(bool(left) or bool(right))
        else:
            raise InterpreterError(
                f'Unknown binary operator: "{operator}"'
            )

        self.stack.append(result)

    def execute(self, instruction):
        if instruction == "READ":
            try:
                value = int(input())
            except (EOFError, ValueError):
                raise InterpreterError(
                    'Input error: "decimal constant" expected'
                )

            self.stack.append(value)
            self.pc += 1
            return

        if instruction == "WRITE":
            print(self.pop())
            self.pc += 1
            return

        if not isinstance(instruction, dict):
            raise InterpreterError(
                f"Invalid instruction: {instruction!r}"
            )

        if len(instruction) != 1:
            raise InterpreterError(
                "Instruction must contain exactly one operation"
            )

        operation, argument = next(iter(instruction.items()))

        if operation == "CONST":
            self.stack.append(argument)
            self.pc += 1
        elif operation == "LD":
            if argument not in self.variables:
                raise InterpreterError(
                    f'Undefined variable: "{argument}"'
                )

            self.stack.append(self.variables[argument])
            self.pc += 1
        elif operation == "ST":
            self.variables[argument] = self.pop()
            self.pc += 1
        elif operation == "BINOP":
            self.execute_binop(argument)
            self.pc += 1
        elif operation == "LABEL":
            self.pc += 1
        elif operation == "JMP":
            self.jump(argument)
        elif operation == "JZ":
            if self.pop() == 0:
                self.jump(argument)
            else:
                self.pc += 1
        elif operation == "JNZ":
            if self.pop() != 0:
                self.jump(argument)
            else:
                self.pc += 1
        else:
            raise InterpreterError(
                f'Unknown instruction: "{operation}"'
            )

    def run(self):
        while self.pc < len(self.program):
            self.execute(self.program[self.pc])


def main():
    if len(sys.argv) != 2:
        print(
            "Usage: python3 bytecode_interpreter.py <program.json>",
            file=sys.stderr
        )
        sys.exit(1)

    filename = sys.argv[1]

    try:
        with open(filename, "r", encoding="utf-8") as file:
            program = json.load(file)
    except FileNotFoundError:
        print(f'File not found: "{filename}"', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        sys.exit(1)

    try:
        machine = Interpreter(program)
        machine.run()
    except InterpreterError as error:
        print(f"Interpreter error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
