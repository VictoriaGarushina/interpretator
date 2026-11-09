import json
import sys

from common import (
    InputReader, InterpreterError, SExpression, State, binop, elements,
    format_value, get_element, is_int, literal_value, match_pattern, set_element, truth,
)


class Interpreter(State):
    def __init__(self, program):
        super().__init__()
        if not isinstance(program, list):
            raise InterpreterError("Program must be a JSON array")
        self.program = program
        self.stack = []
        self.labels = {}
        self.pc = 0
        self.reader = InputReader()
        for index, instruction in enumerate(program):
            if isinstance(instruction, dict) and "LABEL" in instruction:
                label = instruction["LABEL"]
                if label in self.labels:
                    raise InterpreterError(f'Duplicate label: "{label}"')
                self.labels[label] = index

    def pop(self):
        if not self.stack:
            raise InterpreterError("Stack is empty")
        return self.stack.pop()

    def pop_args(self, count):
        if not is_int(count) or count < 0:
            raise InterpreterError("Invalid argument count")
        args = [self.pop() for _ in range(count)]
        return list(reversed(args))

    def jump(self, label):
        if label not in self.labels:
            raise InterpreterError(f'Unknown label: "{label}"')
        self.pc = self.labels[label]

    def execute_simple(self, name):
        if name == "READ":
            self.stack.append(self.reader.read())
        elif name == "WRITE":
            print(format_value(self.pop()))
        elif name == "DUP":
            value = self.pop()
            self.stack.extend([value, value])
        elif name == "POP":
            self.pop()
        elif name == "LENGTH":
            self.stack.append(len(elements(self.pop())))
        elif name == "ELEM":
            index = self.pop()
            value = self.pop()
            self.stack.append(get_element(value, index))
        elif name == "SET":
            item = self.pop()
            index = self.pop()
            value = self.pop()
            set_element(value, index, item)
        elif name == "LEAVE":
            if not self.scopes:
                raise InterpreterError("No pattern scope to leave")
            self.scopes.pop()
        elif name == "FAIL":
            raise InterpreterError(f"No matching pattern for {format_value(self.pop())}")
        else:
            raise InterpreterError(f'Unknown instruction: "{name}"')

    def execute(self, instruction):
        self.pc += 1
        if isinstance(instruction, str):
            self.execute_simple(instruction)
            return
        if not isinstance(instruction, dict) or len(instruction) != 1:
            raise InterpreterError(f"Invalid instruction: {instruction!r}")
        operation, argument = next(iter(instruction.items()))
        if operation == "CONST":
            self.stack.append(literal_value(argument))
        elif operation == "STRING":
            self.stack.append(literal_value(argument))
        elif operation == "LD":
            self.stack.append(self.load(argument))
        elif operation == "ST":
            self.store(argument, self.pop())
        elif operation == "BINOP":
            right = self.pop()
            left = self.pop()
            self.stack.append(binop(argument, left, right))
        elif operation == "ARRAY":
            self.stack.append(self.pop_args(argument))
        elif operation == "SEXP":
            name, count = argument
            self.stack.append(SExpression(name, self.pop_args(count)))
        elif operation == "LABEL":
            pass
        elif operation == "JMP":
            self.jump(argument)
        elif operation == "JZ":
            if not truth(self.pop()):
                self.jump(argument)
        elif operation == "JNZ":
            if truth(self.pop()):
                self.jump(argument)
        elif operation == "MATCH":
            bindings = {}
            if match_pattern(argument["pattern"], self.pop(), bindings):
                self.scopes.append(bindings)
            else:
                self.jump(argument["fail"])
        else:
            raise InterpreterError(f'Unknown instruction: "{operation}"')

    def run(self):
        while self.pc < len(self.program):
            self.execute(self.program[self.pc])


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 vm.py <program.json>", file=sys.stderr)
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
