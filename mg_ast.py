# mg_ast.py
# Representación del Árbol de Sintaxis Abstracta para MiniGo

class Node:
    """Clase base para todos los nodos del AST"""
    pass


class Program(Node):
    """Representa el programa completo (por ahora solo main)"""
    def __init__(self, func_main):
        self.func_main = func_main  # Nodo Function

    def __repr__(self):
        return f"Program({self.func_main})"


class Function(Node):
    """Función (solo main por ahora)"""
    def __init__(self, name, body):
        self.name = name      # str, ej: "main"
        self.body = body      # Block

    def __repr__(self):
        return f"Function({self.name}, {self.body})"


class Block(Node):
    """Bloque de sentencias: { stmt1; stmt2; ... }"""
    def __init__(self, statements):
        self.statements = statements  # Lista de Statement

    def __repr__(self):
        return f"Block({self.statements})"


class VarDecl(Node):
    """Declaración de variable: var x int = 42"""
    def __init__(self, name, type_name, expr=None):
        self.name = name        # str
        self.type_name = type_name  # str, ej: "int"
        self.expr = expr        # Expression, opcional

    def __repr__(self):
        return f"VarDecl({self.name}: {self.type_name} = {self.expr})"


class Assign(Node):
    """Asignación: x = x + 1"""
    def __init__(self, name, expr):
        self.name = name    # str
        self.expr = expr    # Expression

    def __repr__(self):
        return f"Assign({self.name} = {self.expr})"


class BinOp(Node):
    """Operación binaria: +, -, *, /, %, ==, !=, <, <=, >, >=, &&, ||"""
    def __init__(self, left, op, right):
        self.left = left    # Expression
        self.op = op        # str
        self.right = right  # Expression

    def __repr__(self):
        return f"BinOp({self.left}, {self.op}, {self.right})"


class UnaryOp(Node):
    """Operación unaria: !"""
    def __init__(self, op, expr):
        self.op = op     # str, ej: "!"
        self.expr = expr # Expression

    def __repr__(self):
        return f"UnaryOp({self.op}, {self.expr})"


class IfStmt(Node):
    """Sentencia if: if cond { then } else { else_body }"""
    def __init__(self, cond, then_body, else_body=None):
        self.cond = cond         # Expression
        self.then_body = then_body   # Block
        self.else_body = else_body   # Block or None

    def __repr__(self):
        return f"IfStmt({self.cond}, {self.then_body}, {self.else_body})"


class ForStmt(Node):
    """Bucle for: for cond { body }"""
    def __init__(self, cond, body):
        self.cond = cond  # Expression
        self.body = body  # Block

    def __repr__(self):
        return f"ForStmt({self.cond}, {self.body})"


class Identifier(Node):
    """Referencia a una variable: x"""
    def __init__(self, name):
        self.name = name  # str

    def __repr__(self):
        return f"Id({self.name})"


class Literal(Node):
    """Literal: número, string, true, false"""
    def __init__(self, value, type_tag):
        self.value = value     # int, str, bool
        self.type_tag = type_tag  # 'int', 'string', 'bool'

    def __repr__(self):
        return f"Lit({self.value}:{self.type_tag})"


class Call(Node):
    """Llamada a función: print(...)"""
    def __init__(self, func_name, args):
        self.func_name = func_name  # str
        self.args = args            # Lista de Expression

    def __repr__(self):
        return f"Call({self.func_name}, {self.args})"