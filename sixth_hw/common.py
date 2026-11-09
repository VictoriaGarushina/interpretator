import ast
import json
import re


class InterpreterError(Exception):
    pass


class StringValue:
    def __init__(self, text):
        self.chars = [ord(char) for char in text]

    def text(self):
        return "".join(chr(char) for char in self.chars)

    def __eq__(self, other):
        return isinstance(other, StringValue) and self.chars == other.chars


class SExpression:
    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __eq__(self, other):
        return (
            isinstance(other, SExpression)
            and self.name == other.name
            and self.args == other.args
        )


def is_int(value):
    return type(value) is int


def truth(value):
    if not is_int(value):
        raise InterpreterError("Condition must be an integer")
    return value != 0


def literal_value(value):
    if isinstance(value, str):
        return StringValue(value)
    if isinstance(value, list):
        return [literal_value(item) for item in value]
    return value


def format_value(value):
    if isinstance(value, SExpression):
        elements = []
        current = value
        while current.name == "cons" and len(current.args) == 2:
            elements.append(current.args[0])
            current = current.args[1]
            if not isinstance(current, SExpression):
                break
        if isinstance(current, SExpression) and current.name == "nil" and not current.args:
            return "{" + ", ".join(format_value(x) for x in elements) + "}"
        if not value.args:
            return value.name
        return value.name + " (" + ", ".join(format_value(x) for x in value.args) + ")"
    if isinstance(value, list):
        return "[" + ", ".join(format_value(x) for x in value) + "]"
    if isinstance(value, StringValue):
        return json.dumps(value.text(), ensure_ascii=False)
    return str(value)


def elements(value):
    if isinstance(value, StringValue):
        return value.chars
    if isinstance(value, SExpression):
        return value.args
    if isinstance(value, list):
        return value
    raise InterpreterError("Array, string or S-expression expected")


def check_index(value, index):
    items = elements(value)
    if not is_int(index):
        raise InterpreterError("Index must be an integer")
    if not 0 <= index < len(items):
        raise InterpreterError(f"Index {index} out of range (length {len(items)})")
    return items


def get_element(value, index):
    return check_index(value, index)[index]


def set_element(value, index, item):
    items = check_index(value, index)
    if isinstance(value, StringValue) and (not is_int(item) or not 0 <= item <= 255):
        raise InterpreterError("Character code must be between 0 and 255")
    items[index] = item


def compare(left, right):
    if type(left) is not type(right):
        raise InterpreterError("Cannot compare values of different types")
    if is_int(left):
        return (left > right) - (left < right)
    if isinstance(left, StringValue):
        return (left.chars > right.chars) - (left.chars < right.chars)
    if isinstance(left, SExpression):
        if left.name != right.name:
            return (left.name > right.name) - (left.name < right.name)
        left, right = left.args, right.args
    for a, b in zip(left, right):
        result = compare(a, b)
        if result != 0:
            return result
    return (len(left) > len(right)) - (len(left) < len(right))


def binop(operator, left, right):
    if operator == ":":
        return SExpression("cons", [left, right])
    if operator in ("==", "!=", "<", "<=", ">", ">="):
        result = compare(left, right)
        return int({
            "==": result == 0, "!=": result != 0,
            "<": result < 0, "<=": result <= 0,
            ">": result > 0, ">=": result >= 0,
        }[operator])
    if operator == "+" and isinstance(left, (int, StringValue)) and isinstance(right, (int, StringValue)):
        if isinstance(left, StringValue) or isinstance(right, StringValue):
            a = left.text() if isinstance(left, StringValue) else str(left)
            b = right.text() if isinstance(right, StringValue) else str(right)
            return StringValue(a + b)
    if not (is_int(left) and is_int(right)):
        raise InterpreterError(f'Operator "{operator}" requires integers')
    if operator == "+":
        return left + right
    if operator == "-":
        return left - right
    if operator == "*":
        return left * right
    if operator in ("/", "%"):
        if right == 0:
            raise InterpreterError("Division by zero")
        quotient = abs(left) // abs(right)
        if (left < 0) != (right < 0):
            quotient = -quotient
        return quotient if operator == "/" else left - quotient * right
    if operator == "&&":
        return int(left != 0 and right != 0)
    if operator in ("!!", "||"):
        return int(left != 0 or right != 0)
    raise InterpreterError(f'Unknown operator: "{operator}"')


def match_pattern(pattern, value, bindings):
    if isinstance(pattern, str) and pattern in ("#int", "#array", "#string", "#sexp"):
        return {
            "#int": is_int(value),
            "#array": isinstance(value, list),
            "#string": isinstance(value, StringValue),
            "#sexp": isinstance(value, SExpression),
        }[pattern]
    if not isinstance(pattern, dict):
        if isinstance(pattern, str):
            return isinstance(value, StringValue) and pattern == value.text()
        return type(pattern) is type(value) and pattern == value
    if "wildcard" in pattern:
        return True
    if "bind" in pattern:
        binding = pattern["bind"]
        if not match_pattern(binding["pattern"], value, bindings):
            return False
        bindings[binding["name"]] = value
        return True
    if "array" in pattern:
        if not isinstance(value, list):
            return False
        patterns, values = pattern["array"], value
    elif "sexp" in pattern:
        if not isinstance(value, SExpression) or pattern["sexp"] != value.name:
            return False
        patterns, values = pattern["args"], value.args
    else:
        raise InterpreterError(f"Unknown pattern: {pattern!r}")
    return len(patterns) == len(values) and all(
        match_pattern(p, v, bindings) for p, v in zip(patterns, values)
    )


class State:
    def __init__(self):
        self.variables = {}
        self.scopes = []

    def load(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if name not in self.variables:
            raise InterpreterError(f'Undefined variable: "{name}"')
        return self.variables[name]

    def store(self, name, value):
        for scope in reversed(self.scopes):
            if name in scope:
                scope[name] = value
                return
        self.variables[name] = value


class InputReader:
    token = re.compile(r'\s*(-?\d+|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|[A-Za-z_][A-Za-z_0-9\']*|[][(){},:])')

    def __init__(self):
        self.tokens = []
        self.position = 0

    def fill(self):
        while self.position == len(self.tokens):
            try:
                line = input()
            except EOFError:
                raise InterpreterError("Input exhausted")
            self.tokens = []
            self.position = 0
            offset = 0
            while offset < len(line):
                if not line[offset:].strip():
                    break
                match = self.token.match(line, offset)
                if not match:
                    raise InterpreterError("Invalid input value")
                self.tokens.append(match[1])
                offset = match.end()

    def peek(self):
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self):
        self.fill()
        value = self.tokens[self.position]
        self.position += 1
        return value

    def sequence(self, closing):
        values = []
        self.fill()
        if self.peek() == closing:
            self.take()
            return values
        while True:
            values.append(self.value())
            separator = self.take()
            if separator == closing:
                return values
            if separator != ",":
                raise InterpreterError(f'Expected "," or "{closing}" in input')

    def value(self):
        token = self.take()
        if token == "[":
            value = self.sequence("]")
        elif token == "{":
            values = self.sequence("}")
            value = SExpression("nil", [])
            for item in reversed(values):
                value = SExpression("cons", [item, value])
        elif token == "(":
            value = self.value()
            if self.take() != ")":
                raise InterpreterError('Expected ")" in input')
        elif token.startswith('"'):
            try:
                value = StringValue(json.loads(token))
            except ValueError:
                raise InterpreterError("Invalid input string")
        elif token.startswith("'"):
            try:
                value = ast.literal_eval(token)
                if len(value) != 1:
                    raise ValueError()
                value = ord(value)
            except (ValueError, SyntaxError):
                raise InterpreterError("Invalid input character")
        elif re.fullmatch(r"-?\d+", token):
            value = int(token)
        elif token[0].isupper() or token in ("cons", "nil"):
            args = []
            if self.peek() == "(":
                self.take()
                args = self.sequence(")")
            value = SExpression(token, args)
        else:
            raise InterpreterError(f"Unexpected input token: {token}")
        if self.peek() == ":":
            self.take()
            value = SExpression("cons", [value, self.value()])
        return value

    def read(self):
        self.fill()
        if self.peek() == ",":
            self.take()
        return self.value()
