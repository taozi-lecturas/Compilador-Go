# semant.py
from mg_ast import *
from typing import Dict, List, Optional

class SymbolTable:
    """Tabla de símbolos con soporte para ámbitos anidados"""
    def __init__(self):
        self.scopes = [{}]  # Pila de ámbitos. El primero es global.

    def declare(self, name: str, type_name: str, lineno=None) -> bool:
        """Declara una variable en el ámbito actual. Retorna False si ya existe."""
        if name in self.scopes[-1]:
            return False
        self.scopes[-1][name] = type_name
        return True

    def lookup(self, name: str) -> Optional[str]:
        """Busca una variable desde el ámbito más interno al externo. Retorna su tipo o None."""
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        return None

    def enter_scope(self):
        """Abre un nuevo ámbito (ej: dentro de { ... })"""
        self.scopes.append({})

    def exit_scope(self):
        """Cierra el ámbito actual"""
        if len(self.scopes) > 1:
            self.scopes.pop()
        else:
            raise Exception("No se puede salir del ámbito global")


class SemanticError(Exception):
    """Excepción para errores semánticos"""
    def __init__(self, message: str, lineno=None):
        self.message = message
        self.lineno = lineno
        super().__init__(self.message)


class SemanticAnalyzer:
    """Recorre el AST y verifica reglas semánticas"""
    
    def __init__(self):
        self.symbol_table = SymbolTable()
        self.errors: List[SemanticError] = []

    def error(self, msg: str, node=None):
        """Agrega un error semántico"""
        # Aún no tenemos número de línea en los nodos, pero podrías agregarlo
        self.errors.append(SemanticError(msg))

    def analyze(self, node: Node):
        """Punto de entrada"""
        self.visit(node)
        return len(self.errors) == 0  # True si no hay errores

    def visit(self, node: Node):
        """Despacha al método específico"""
        if node is None:
            return
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        visitor(node)

    def generic_visit(self, node: Node):
        """Visita todos los atributos del nodo"""
        for key in vars(node):
            value = getattr(node, key)
            if isinstance(value, list):
                for item in value:
                    self.visit(item)
            elif isinstance(value, Node):
                self.visit(value)

    # ====================
    # Visitantes específicos
    # ====================

    def visit_Program(self, node: Program):
        self.visit(node.func_main)

    def visit_Function(self, node: Function):
        if node.name == "main":
            self.visit(node.body)
        else:
            self.error(f"Función no soportada: {node.name}")

    def visit_Block(self, node: Block):
        self.symbol_table.enter_scope()
        for stmt in node.statements:
            self.visit(stmt)
        self.symbol_table.exit_scope()

    def visit_VarDecl(self, node: VarDecl):
        # Verificar que el tipo sea válido
        if node.type_name not in ['int', 'bool']:
            self.error(f"Tipo desconocido '{node.type_name}'")
            return

        # Verificar que no esté ya declarada
        if not self.symbol_table.declare(node.name, node.type_name):
            self.error(f"Variable '{node.name}' ya fue declarada en este ámbito")
            return

        # Si tiene valor inicial, verificar tipo
        if node.expr:
            self.visit(node.expr)
            expr_type = self.infer_type(node.expr)
            if expr_type and expr_type != node.type_name:
                self.error(f"Tipo incompatible en declaración: esperado {node.type_name}, obtenido {expr_type}")

    def visit_Assign(self, node: Assign):
        var_type = self.symbol_table.lookup(node.name)
        if var_type is None:
            self.error(f"Variable '{node.name}' no declarada")
            return

        self.visit(node.expr)
        expr_type = self.infer_type(node.expr)
        if expr_type and expr_type != var_type:
            self.error(f"Tipo incompatible en asignación: '{node.name}' es {var_type}, pero se asigna {expr_type}")

    def visit_Identifier(self, node: Identifier):
        if self.symbol_table.lookup(node.name) is None:
            self.error(f"Variable '{node.name}' no declarada")

    def visit_BinOp(self, node: BinOp):
        self.visit(node.left)
        self.visit(node.right)

        left_type = self.infer_type(node.left)
        right_type = self.infer_type(node.right)

        # Operadores aritméticos: deben ser int
        if node.op in ['+', '-', '*', '/', '%']:
            if left_type != 'int' or right_type != 'int':
                self.error(f"Operador '{node.op}' espera operandos int")

        # Comparaciones: <, <=, >, >= → int → bool
        elif node.op in ['<', '<=', '>', '>=', '==']:
            if node.op == '==':
                # Ya validamos compatibilidad antes
                return 'bool'
            else:
                if left_type != 'int' or right_type != 'int':
                    self.error(f"Comparación '{node.op}' requiere int")
                return 'bool'
            
        # Igualdad: ambos operandos del mismo tipo
        elif node.op == '==':
            if left_type and right_type:
                if left_type != right_type:
                    self.error(f"Comparación de igualdad entre tipos incompatibles: {left_type} y {right_type}")
            return 'bool'  # ← Agregar retorno aquí también

        # Lógicos: &&, || → bool
        elif node.op in ['&&', '||']:
            if left_type != 'bool' or right_type != 'bool':
                self.error(f"Operador lógico '{node.op}' espera bool")

    def visit_UnaryOp(self, node: UnaryOp):
        self.visit(node.expr)
        expr_type = self.infer_type(node.expr)

        if node.op == '!':
            if expr_type != 'bool':
                self.error(f"Operador '!' espera un operando bool, no {expr_type}")
        elif node.op == '-':  # -unario
            if expr_type != 'int':
                self.error(f"Operador '-' unario espera int, no {expr_type}")

    def visit_IfStmt(self, node: IfStmt):
        self.visit(node.cond)
        cond_type = self.infer_type(node.cond)
        if cond_type != 'bool':
            self.error(f"Condición de 'if' debe ser bool, no {cond_type}")
        self.visit(node.then_body)
        if node.else_body:
            self.visit(node.else_body)

    def visit_ForStmt(self, node: ForStmt):
        self.visit(node.cond)
        cond_type = self.infer_type(node.cond)
        if cond_type != 'bool':
            self.error(f"Condición de 'for' debe ser bool, no {cond_type}")
        self.visit(node.body)

    def visit_Call(self, node: Call):
        # Por ahora, asumimos que print/println aceptan cualquier cosa
        for arg in node.args:
            self.visit(arg)
        # Podrías validar aquí que los argumentos sean int/string

    def visit_Literal(self, node: Literal):
        pass  # No necesita verificación adicional

    # ====================
    # Inferencia de tipo
    # ====================

    def infer_type(self, node: Node) -> Optional[str]:
        """Infiere el tipo de una expresión"""
        if isinstance(node, Literal):
            return node.type_tag
        elif isinstance(node, Identifier):
            return self.symbol_table.lookup(node.name)
        elif isinstance(node, BinOp):
            left_type = self.infer_type(node.left)
            right_type = self.infer_type(node.right)

            if node.op in ['+', '-', '*', '/', '%']:
                return 'int'
            elif node.op in ['<', '<=', '>', '>=', '==']:
                # Ya validamos en visit_BinOp que los operandos sean válidos
                return 'bool'
            elif node.op in ['&&', '||']:
                return 'bool'
        elif isinstance(node, UnaryOp):
            if node.op == '!':
                return 'bool'
            elif node.op == '-':
                return 'int'
        elif isinstance(node, Call):
            # println podría devolver void, pero no se usa
            return None
        return None  # Desconocido