import copy
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

    @staticmethod
    def is_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    def pop_int(self, what="value"):
        value = self.pop()
        if not self.is_int(value):
            raise InterpreterError(
                f"Integer expected for {what}, got {value!r}"
            )
        return value

    def pop_array(self):
        value = self.pop()
        if not isinstance(value, list):
            raise InterpreterError(f"Array expected, got {value!r}")
        return value

    def check_index(self, container, index):
        if not self.is_int(index):
            raise InterpreterError(
                f"Index must be an integer, got {index!r}"
            )
        if not 0 <= index < len(container):
            raise InterpreterError(
                f"Index {index} out of range (length {len(container)})"
            )

    def execute_binop(self, operator):
        right = self.pop()
        left = self.pop()

        both_int = self.is_int(left) and self.is_int(right)
        both_str = isinstance(left, str) and isinstance(right, str)
        both_arr = isinstance(left, list) and isinstance(right, list)

        if operator == "+":
            if not (both_int or both_str or both_arr):
                raise InterpreterError(
                    f"Cannot apply + to {left!r} and {right!r}"
                )
            result = left + right
        elif operator in ("-", "*", "/", "%"):
            if not both_int:
                raise InterpreterError(
                    f'Operator "{operator}" requires integers'
                )
            if operator == "-":
                result = left - right
            elif operator == "*":
                result = left * right
            else:
                if right == 0:
                    raise InterpreterError("Division by zero")
                result = left // right if operator == "/" else left % right
        elif operator == "==":
            result = int(left == right)
        elif operator == "!=":
            result = int(left != right)
        elif operator in ("<", "<=", ">", ">="):
            if not (both_int or both_str):
                raise InterpreterError(
                    f'Cannot compare {left!r} and {right!r} with "{operator}"'
                )
            result = int({
                "<": left < right,
                "<=": left <= right,
                ">": left > right,
                ">=": left >= right,
            }[operator])
        elif operator == "&&":
            result = int(bool(left) and bool(right))
        elif operator in ("||", "!!"):
            result = int(bool(left) or bool(right))
        else:
            raise InterpreterError(
                f'Unknown binary operator: "{operator}"'
            )

        self.stack.append(result)

    def execute_simple(self, name):
        if name == "READ":
            try:
                value = int(input())
            except (EOFError, ValueError):
                raise InterpreterError(
                    'Input error: "decimal constant" expected'
                )
            self.stack.append(value)
        elif name == "READS":
            try:
                self.stack.append(input())
            except EOFError:
                raise InterpreterError("Input error: string expected")
        elif name == "WRITE":
            value = self.pop()
            if isinstance(value, list):
                print(json.dumps(value, ensure_ascii=False))
            else:
                print(value)
        elif name == "NEWARR":
            size = self.pop_int("array size")
            if size < 0:
                raise InterpreterError("Negative array size")
            self.stack.append([0] * size)
        elif name == "ALEN":
            value = self.pop()
            if not isinstance(value, (list, str)):
                raise InterpreterError(
                    f"Array or string expected, got {value!r}"
                )
            self.stack.append(len(value))
        elif name == "ALOAD":
            index = self.pop()
            container = self.pop()
            if not isinstance(container, (list, str)):
                raise InterpreterError(
                    f"Array or string expected, got {container!r}"
                )
            self.check_index(container, index)
            self.stack.append(container[index])
        elif name == "ASTORE":
            value = self.pop()
            index = self.pop()
            array = self.pop_array()
            self.check_index(array, index)
            array[index] = value
        elif name == "APPEND":
            value = self.pop()
            array = self.pop_array()
            array.append(value)
        elif name == "APOP":
            array = self.pop_array()
            if not array:
                raise InterpreterError("Pop from empty array")
            self.stack.append(array.pop())
        elif name == "SUBSTR":
            end = self.pop_int("end")
            start = self.pop_int("start")
            string = self.pop()
            if not isinstance(string, str):
                raise InterpreterError(f"String expected, got {string!r}")
            self.stack.append(string[start:end])
        else:
            raise InterpreterError(f'Unknown instruction: "{name}"')

        self.pc += 1

    def execute(self, instruction):
        if isinstance(instruction, str):
            self.execute_simple(instruction)
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
            self.stack.append(copy.deepcopy(argument))
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
            "Usage: python3 interpreter3.py <program.json>",
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