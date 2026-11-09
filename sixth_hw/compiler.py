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

    def new_label(self, prefix):
        label = f"L_{prefix}_{self.label_counter}"
        self.label_counter += 1
        return label

    def compile_expr(self, expr):
        if not isinstance(expr, dict):
            raise CompilerError(f"Expected expression object, got: {expr!r}")
        if "const" in expr:
            self.emit({"CONST": expr["const"]})
        elif "string" in expr:
            self.emit({"STRING": expr["string"]})
        elif "var" in expr:
            self.emit({"LD": expr["var"]})
        elif "binop" in expr:
            self.compile_expr(expr["left"])
            self.compile_expr(expr["right"])
            self.emit({"BINOP": expr["binop"]})
        elif "array" in expr:
            for item in expr["array"]:
                self.compile_expr(item)
            self.emit({"ARRAY": len(expr["array"])})
        elif "sexp" in expr:
            for item in expr["args"]:
                self.compile_expr(item)
            self.emit({"SEXP": [expr["sexp"], len(expr["args"])]})
        elif "elem" in expr:
            self.compile_expr(expr["elem"])
            self.compile_expr(expr["index"])
            self.emit("ELEM")
        elif "length" in expr:
            self.compile_expr(expr["length"])
            self.emit("LENGTH")
        else:
            raise CompilerError(f"Unknown expression: {expr!r}")

    def compile_stmt(self, node):
        if node == "skip":
            return
        if not isinstance(node, dict):
            raise CompilerError(f"Expected statement object, got: {node!r}")
        if "seq" in node:
            self.compile_stmt(node["seq"]["left"])
            self.compile_stmt(node["seq"]["right"])
        elif "assn" in node:
            stmt = node["assn"]
            self.compile_expr(stmt["src"])
            self.emit({"ST": stmt["dst"]})
        elif "set" in node:
            stmt = node["set"]
            self.compile_expr(stmt["dst"])
            self.compile_expr(stmt["idx"])
            self.compile_expr(stmt["value"])
            self.emit("SET")
        elif "read" in node:
            self.emit("READ")
            self.emit({"ST": node["read"]})
        elif "write" in node:
            self.compile_expr(node["write"])
            self.emit("WRITE")
        elif "if" in node:
            stmt = node["if"]
            else_label = self.new_label("else")
            end_label = self.new_label("end")
            self.compile_expr(stmt["cond"])
            self.emit({"JZ": else_label})
            self.compile_stmt(stmt["then"])
            self.emit({"JMP": end_label})
            self.emit({"LABEL": else_label})
            self.compile_stmt(stmt.get("else", "skip"))
            self.emit({"LABEL": end_label})
        elif "while" in node or "do" in node:
            stmt = node.get("while", node.get("do"))
            body_label = self.new_label("body")
            cond_label = self.new_label("cond")
            if "while" in node:
                self.emit({"JMP": cond_label})
            self.emit({"LABEL": body_label})
            self.compile_stmt(stmt["body"])
            self.emit({"LABEL": cond_label})
            self.compile_expr(stmt["cond"])
            self.emit({"JNZ": body_label})
        elif "switch" in node:
            self.compile_switch(node["switch"])
        else:
            raise CompilerError(f"Unknown statement: {node!r}")

    def compile_switch(self, stmt):
        end_label = self.new_label("switch_end")
        self.compile_expr(stmt["scrutinee"])
        for branch in stmt["branches"]:
            next_label = self.new_label("case")
            self.emit("DUP")
            self.emit({"MATCH": {"pattern": branch["pattern"], "fail": next_label}})
            self.compile_stmt(branch["branch"])
            self.emit("LEAVE")
            self.emit({"JMP": end_label})
            self.emit({"LABEL": next_label})
        self.emit("FAIL")
        self.emit({"LABEL": end_label})
        self.emit("POP")

    def compile(self, ast):
        self.instructions = []
        self.label_counter = 0
        self.compile_stmt(ast)
        return self.instructions


def main():
    if len(sys.argv) not in (2, 3):
        print("Usage: python3 compiler.py <input.json> [output.json]", file=sys.stderr)
        sys.exit(1)
    try:
        with open(sys.argv[1], encoding="utf-8") as file:
            ast = json.load(file)
        program = Compiler().compile(ast)
        dumped = json.dumps(program, ensure_ascii=False, indent=2)
        if len(sys.argv) == 3:
            with open(sys.argv[2], "w", encoding="utf-8") as file:
                file.write(dumped + "\n")
        else:
            print(dumped)
    except (OSError, ValueError, KeyError, CompilerError) as error:
        print(f"Compilation error: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
