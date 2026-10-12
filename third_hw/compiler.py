import json
import sys


class CompilerError(Exception):
    pass


END_LABEL = "L_end_0"
BODY_PREFIX = "while_body"
COND_PREFIX = "while_cond"
FIRST_FREE_LABEL = 1


class Compiler:
    def __init__(self):
        self.instructions = []
        self.label_counter = FIRST_FREE_LABEL

    def emit(self, instruction):
        self.instructions.append(instruction)

    def new_label(self, prefix):
        label = f"L_{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    @staticmethod
    def require_object(value, name):
        if not isinstance(value, dict):
            raise CompilerError(f"{name} must contain an object")

    @staticmethod
    def require_keys(obj, keys, name):
        for key in keys:
            if key not in obj:
                raise CompilerError(f"{name} must contain '{key}'")

    def compile_expr(self, expr):
        if not isinstance(expr, dict):
            raise CompilerError(f"Expected expression object, got: {expr!r}")

        if "const" in expr:
            self.emit({"CONST": expr["const"]})
            return

        if "var" in expr:
            self.emit({"LD": expr["var"]})
            return

        if "binop" in expr:
            op = expr["binop"]
            if "left" not in expr or "right" not in expr:
                raise CompilerError(
                    f"Binary operation '{op}' must have 'left' and 'right'"
                )
            self.compile_expr(expr["left"])
            self.compile_expr(expr["right"])
            self.emit({"BINOP": op})
            return

        raise CompilerError(f"Unknown expression: {expr!r}")

    def compile_stmt(self, node, lab):
        if node == "skip":
            return False

        if not isinstance(node, dict):
            raise CompilerError(f"Expected statement object, got: {node!r}")

        if "seq" in node:
            return self.compile_seq(node["seq"], lab)
        if "assn" in node:
            return self.compile_assn(node["assn"])
        if "read" in node:
            self.emit("READ")
            self.emit({"ST": node["read"]})
            return False
        if "write" in node:
            self.compile_expr(node["write"])
            self.emit("WRITE")
            return False
        if "if" in node:
            return self.compile_if(node["if"], lab)
        if "while" in node:
            return self.compile_while(node["while"])
        if "do" in node:
            return self.compile_do(node["do"])

        raise CompilerError(f"Unknown statement: {node!r}")

    def compile_seq(self, seq, lab):
        self.require_object(seq, "seq")
        self.require_keys(seq, ("left", "right"), "seq")

        lab2 = self.new_label("seq")
        f1 = self.compile_stmt(seq["left"], lab2)
        if f1:
            self.emit({"LABEL": lab2})
        return self.compile_stmt(seq["right"], lab)

    def compile_assn(self, assn):
        self.require_object(assn, "assn")
        self.require_keys(assn, ("dst", "src"), "Assignment")

        self.compile_expr(assn["src"])
        self.emit({"ST": assn["dst"]})
        return False

    def compile_if(self, stmt, lab):
        self.require_object(stmt, "if")
        self.require_keys(stmt, ("cond", "then"), "if")

        lab2 = self.new_label("else")

        self.compile_expr(stmt["cond"])
        self.emit({"JZ": lab2})

        self.compile_stmt(stmt["then"], lab)
        self.emit({"JMP": lab})
        self.emit({"LABEL": lab2})

        if "else" in stmt:
            self.compile_stmt(stmt["else"], lab)

        return True

    def compile_while(self, stmt):
        self.require_object(stmt, "while")
        self.require_keys(stmt, ("cond", "body"), "while")

        body_label = self.new_label(BODY_PREFIX)
        cond_label = self.new_label(COND_PREFIX)

        self.emit({"JMP": cond_label})
        self.emit({"LABEL": body_label})
        self.compile_stmt(stmt["body"], cond_label)
        self.emit({"LABEL": cond_label})
        self.compile_expr(stmt["cond"])
        self.emit({"JNZ": body_label})

        return False

    def compile_do(self, stmt):
        self.require_object(stmt, "do")
        self.require_keys(stmt, ("cond", "body"), "do")

        body_label = self.new_label(BODY_PREFIX)
        cond_label = self.new_label(COND_PREFIX)

        self.emit({"LABEL": body_label})
        self.compile_stmt(stmt["body"], cond_label)
        self.emit({"LABEL": cond_label})
        self.compile_expr(stmt["cond"])
        self.emit({"JNZ": body_label})

        return False

    def compile(self, ast):
        self.instructions = []
        self.label_counter = FIRST_FREE_LABEL

        f = self.compile_stmt(ast, END_LABEL)
        if f:
            self.emit({"LABEL": END_LABEL})
        return self.instructions


def main():
    if len(sys.argv) < 2:
        print("Usage: python compiler2.py <input.json> [output.json]",
              file=sys.stderr)
        sys.exit(1)

    input_filename = sys.argv[1]

    try:
        with open(input_filename, "r", encoding="utf-8") as file:
            ast = json.load(file)
    except FileNotFoundError:
        print(f'File not found: "{input_filename}"', file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as error:
        print(f"Invalid JSON: {error}", file=sys.stderr)
        sys.exit(1)

    try:
        machine_program = Compiler().compile(ast)
    except CompilerError as error:
        print(f"Compilation error: {error}", file=sys.stderr)
        sys.exit(1)

    dumped = json.dumps(machine_program, ensure_ascii=False, indent=2)

    if len(sys.argv) >= 3:
        with open(sys.argv[2], "w", encoding="utf-8") as file:
            file.write(dumped)
    else:
        print(dumped)


if __name__ == "__main__":
    main()