import json
import sys


class CompilerError(Exception):
    pass


class Compiler:
    def __init__(self):
        self.instructions = []
        self.label_counter = 0

    def emit(self, instruction):
        self.instructions.append(instruction)

    def new_label(self, prefix="L"):
        label = f"{prefix}{self.label_counter}"
        self.label_counter += 1
        return label

    def compile_expr(self, expr):

        if not isinstance(expr, dict):
            raise CompilerError(
                f"Expected expression object, got: {expr!r}"
            )

        if "const" in expr:
            self.emit({
                "CONST": expr["const"]
            })
            return

        if "var" in expr:
            self.emit({
                "LD": expr["var"]
            })
            return

        if "binop" in expr:
            op = expr["binop"]

            if "left" not in expr or "right" not in expr:
                raise CompilerError(
                    f"Binary operation '{op}' must have "
                    f"'left' and 'right'"
                )

            self.compile_expr(expr["left"])
            self.compile_expr(expr["right"])

            self.emit({
                "BINOP": op
            })
            return

        raise CompilerError(
            f"Unknown expression: {expr!r}"
        )

    def compile_stmt(self, node):

        if node == "skip":
            return

        if not isinstance(node, dict):
            raise CompilerError(
                f"Expected statement object, got: {node!r}"
            )

        if "seq" in node:
            seq = node["seq"]

            self.compile_stmt(seq["left"])
            self.compile_stmt(seq["right"])
            return

        if "assn" in node:
            assn = node["assn"]

            if "dst" not in assn or "src" not in assn:
                raise CompilerError(
                    "Assignment must contain 'dst' and 'src'"
                )

            variable = assn["dst"]

            self.compile_expr(assn["src"])

            self.emit({
                "ST": variable
            })
            return

        if "read" in node:
            variable = node["read"]

            self.emit("READ")
            self.emit({
                "ST": variable
            })
            return

        if "write" in node:
            self.compile_expr(node["write"])
            self.emit("WRITE")
            return

        if "if" in node:
            statement = node["if"]

            if "cond" not in statement:
                raise CompilerError(
                    "if must contain 'cond'"
                )

            if "then" not in statement:
                raise CompilerError(
                    "if must contain 'then'"
                )

            else_label = self.new_label("else")
            end_label = self.new_label("end")

            self.compile_expr(statement["cond"])

            self.emit({
                "JZ": else_label
            })

            self.compile_stmt(statement["then"])

            self.emit({
                "JMP": end_label
            })

            self.emit({
                "LABEL": else_label
            })

            if "else" in statement:
                self.compile_stmt(statement["else"])

            self.emit({
                "LABEL": end_label
            })

            return

        if "while" in node:
            statement = node["while"]

            if "cond" not in statement:
                raise CompilerError(
                    "while must contain 'cond'"
                )

            if "body" not in statement:
                raise CompilerError(
                    "while must contain 'body'"
                )

            start_label = self.new_label("while")
            end_label = self.new_label("end")

            self.emit({
                "LABEL": start_label
            })

            self.compile_expr(statement["cond"])

            self.emit({
                "JZ": end_label
            })

            self.compile_stmt(statement["body"])

            self.emit({
                "JMP": start_label
            })

            self.emit({
                "LABEL": end_label
            })

            return

        if "do" in node:
            statement = node["do"]

            if "body" not in statement:
                raise CompilerError(
                    "do must contain 'body'"
                )

            if "cond" not in statement:
                raise CompilerError(
                    "do must contain 'cond'"
                )

            start_label = self.new_label("do")

            self.emit({
                "LABEL": start_label
            })

            self.compile_stmt(statement["body"])

            self.compile_expr(statement["cond"])

            self.emit({
                "JNZ": start_label
            })

            return

        if "for" in node:
            statement = node["for"]

            init = statement.get("init")
            cond = statement.get("cond")
            update = statement.get("step")

            if update is None:
                update = statement.get("update")

            if update is None:
                update = statement.get("post")

            body = statement.get("body")

            if cond is None:
                raise CompilerError(
                    "for must contain 'cond'"
                )

            if body is None:
                raise CompilerError(
                    "for must contain 'body'"
                )

            start_label = self.new_label("for")
            end_label = self.new_label("end")

            if init is not None:
                self.compile_stmt(init)

            self.emit({
                "LABEL": start_label
            })

            self.compile_expr(cond)

            self.emit({
                "JZ": end_label
            })

            self.compile_stmt(body)

            if update is not None:
                self.compile_stmt(update)

            self.emit({
                "JMP": start_label
            })

            self.emit({
                "LABEL": end_label
            })

            return

        raise CompilerError(
            f"Unknown statement: {node!r}"
        )

    def compile(self, ast):

        self.instructions = []
        self.label_counter = 0

        self.compile_stmt(ast)

        return self.instructions


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: python compiler.py <input.json> [output.json]",
            file=sys.stderr
        )
        sys.exit(1)

    input_filename = sys.argv[1]

    try:
        with open(
            input_filename,
            "r",
            encoding="utf-8"
        ) as file:
            ast = json.load(file)

    except FileNotFoundError:
        print(
            f'File not found: "{input_filename}"',
            file=sys.stderr
        )
        sys.exit(1)

    except json.JSONDecodeError as error:
        print(
            f"Invalid JSON: {error}",
            file=sys.stderr
        )
        sys.exit(1)

    try:
        compiler = Compiler()
        machine_program = compiler.compile(ast)

    except CompilerError as error:
        print(
            f"Compilation error: {error}",
            file=sys.stderr
        )
        sys.exit(1)

    if len(sys.argv) >= 3:
        output_filename = sys.argv[2]

        with open(
            output_filename,
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(
                machine_program,
                file,
                ensure_ascii=False,
                indent=2
            )

    else:
        print(
            json.dumps(
                machine_program,
                ensure_ascii=False,
                indent=2
            )
        )


if __name__ == "__main__":
    main()