# codegen.py
from llvmlite import ir, binding
from mg_ast import *
import sys

# Configuración básica
INT_TYPE = ir.IntType(32)
INT_PTR = ir.PointerType(INT_TYPE)
BOOL_TYPE = ir.IntType(1)
STRING_TYPE = ir.PointerType(ir.IntType(8))

# Mapeo simple de tipos MiniGo → LLVM
TYPE_MAP = {
    'int': INT_TYPE,
    'bool': BOOL_TYPE,
}

class CodeGen:
    def __init__(self):
        # Crear módulo LLVM
        self.module = ir.Module(name="minigo_module")
        self.module.triple = binding.get_default_triple()  # Ej: x86_64-pc-linux-gnu

        # El builder maneja dónde insertar instrucciones
        self.builder: ir.IRBuilder = None

        # Tabla de variables: nombre → alloca (dirección en memoria)
        self.vars = {}

        # Función actual
        self.current_func = None

        # Inicializar funciones externas
        self.declare_printf()
        self.declare_main()

    def declare_printf(self):
        """Declara printf correctamente"""
        # int printf(i8*, ...)
        printf_ty = ir.FunctionType(INT_TYPE, [STRING_TYPE], var_arg=True)
        printf = ir.Function(self.module, printf_ty, name="printf")
        self.printf = printf

    def declare_main(self):
        """Declara la función main (void -> int)"""
        func_ty = ir.FunctionType(INT_TYPE, [])
        main_func = ir.Function(self.module, func_ty, name="main")
        # Bloque de entrada
        block = main_func.append_basic_block(name="entry")
        self.builder = ir.IRBuilder(block)
        self.current_func = main_func

    def compile(self, node: Node):
        """Compila el AST completo"""
        if isinstance(node, Program):
            self.visit(node)
            # Asegurar retorno final en main
            if not self.builder.block.is_terminated:
                self.builder.ret(ir.Constant(INT_TYPE, 0))
        else:
            raise RuntimeError(f"Nodo raíz inesperado: {type(node)}")

    def visit(self, node: Node):
        method_name = f'visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node):
        raise NotImplementedError(f"No se implementó visit_{type(node).__name__}")

    def visit_Program(self, node: Program):
        self.visit(node.func_main)

    def visit_Function(self, node: Function):
        if node.name == "main":
            self.visit(node.body)
        else:
            raise RuntimeError(f"Función no soportada: {node.name}")

    def visit_Block(self, node: Block):
        for stmt in node.statements:
            self.visit(stmt)  # sin asignar resultado

    def visit_VarDecl(self, node: VarDecl):
        # Reservar espacio en stack
        alloca = self.builder.alloca(TYPE_MAP[node.type_name], name=node.name)
        self.vars[node.name] = alloca

        # Si hay valor inicial, asignarlo
        if node.expr:
            value = self.visit(node.expr)
            self.builder.store(value, alloca)

    def visit_Assign(self, node: Assign):
        # Buscar dirección de la variable
        alloca = self.vars.get(node.name)
        if alloca is None:
            raise RuntimeError(f"Variable no declarada (en generación): {node.name}")

        value = self.visit(node.expr)
        self.builder.store(value, alloca)
        return value

    def visit_Identifier(self, node: Identifier):
        alloca = self.vars.get(node.name)
        if alloca is None:
            raise RuntimeError(f"Variable no encontrada: {node.name}")
        return self.builder.load(alloca, name=node.name)

    def visit_Literal(self, node: Literal):
        if node.type_tag == 'int':
            return ir.Constant(INT_TYPE, node.value)
        elif node.type_tag == 'bool':
            return ir.Constant(BOOL_TYPE, 1 if node.value else 0)
        elif node.type_tag == 'string':
            # ✅ Codificar correctamente a UTF-8 + \0
            encoded = (node.value + '\0').encode('utf8')
            n = len(encoded)
            cstr = ir.Constant(
                ir.ArrayType(ir.IntType(8), n),
                bytearray(encoded)
            )
            global_str = ir.GlobalVariable(self.module, cstr.type, name=f"str.{len(self.module.globals)}")
            global_str.linkage = 'private'
            global_str.global_constant = True
            global_str.initializer = cstr
            return self.builder.bitcast(global_str, STRING_TYPE)
        else:
            raise RuntimeError(f"Tipo literal desconocido: {node.type_tag}")

    def visit_BinOp(self, node: BinOp):
        left = self.visit(node.left)
        right = self.visit(node.right)

        if node.op == '+':
            return self.builder.add(left, right)
        elif node.op == '-':
            return self.builder.sub(left, right)
        elif node.op == '*':
            return self.builder.mul(left, right)
        elif node.op == '/':
            return self.builder.sdiv(left, right)
        elif node.op == '%':
            return self.builder.srem(left, right)
        elif node.op == '==':
            if left.type == INT_TYPE:
                return self.builder.icmp_signed('==', left, right)
            elif left.type == BOOL_TYPE:
                return self.builder.icmp_signed('==', left, right)
        elif node.op in ['<', '<=', '>', '>=']:
            # Usar el operador directamente, no el nombre de instrucción LLVM
            return self.builder.icmp_signed(node.op, left, right)
        elif node.op == '&&':
            # Cortocircuito: evaluar left && right
            # Resultado final en r0 (i1)
            
            # Evaluar left
            left_val = self.visit(node.left)
            if left_val.type == INT_TYPE:
                zero = ir.Constant(INT_TYPE, 0)
                left_bool = self.builder.icmp_signed('!=', left_val, zero)
            else:
                left_bool = left_val

            # Si left es falso → resultado = falso
            # Si left es verdadero → evaluar right
            end_block = self.builder.function.append_basic_block("and.end")
            right_block = self.builder.function.append_basic_block("and.right")
            merge_block = self.builder.function.append_basic_block("and.merge")

            # from left: br i1 left_bool, label %right_block, label %end_block
            self.builder.cbranch(left_bool, right_block, end_block)

            # Bloque 'right': evaluar right
            self.builder.position_at_end(right_block)
            right_val = self.visit(node.right)
            if right_val.type == INT_TYPE:
                zero = ir.Constant(INT_TYPE, 0)
                right_bool = self.builder.icmp_signed('!=', right_val, zero)
            else:
                right_bool = right_val
            self.builder.branch(merge_block)

            # Bloque 'end': resultado = false
            self.builder.position_at_end(end_block)
            false_val = ir.Constant(BOOL_TYPE, False)
            self.builder.branch(merge_block)

            # Merge: phi[true → right_bool, false → false]
            self.builder.position_at_end(merge_block)
            phi = self.builder.phi(BOOL_TYPE)
            phi.add_incoming(right_bool, right_block)
            phi.add_incoming(false_val, end_block)
            return phi

        elif node.op == '||':
            # similar, pero invertido
            left_val = self.visit(node.left)
            if left_val.type == INT_TYPE:
                zero = ir.Constant(INT_TYPE, 0)
                left_bool = self.builder.icmp_signed('!=', left_val, zero)
            else:
                left_bool = left_val

            end_block = self.builder.function.append_basic_block("or.end")
            right_block = self.builder.function.append_basic_block("or.right")
            merge_block = self.builder.function.append_basic_block("or.merge")

            self.builder.cbranch(left_bool, end_block, right_block)

            self.builder.position_at_end(right_block)
            right_val = self.visit(node.right)
            if right_val.type == INT_TYPE:
                zero = ir.Constant(INT_TYPE, 0)
                right_bool = self.builder.icmp_signed('!=', right_val, zero)
            else:
                right_bool = right_val
            self.builder.branch(merge_block)

            self.builder.position_at_end(end_block)
            true_val = ir.Constant(BOOL_TYPE, True)
            self.builder.branch(merge_block)

            self.builder.position_at_end(merge_block)
            phi = self.builder.phi(BOOL_TYPE)
            phi.add_incoming(true_val, end_block)
            phi.add_incoming(right_bool, right_block)
            return phi

    def visit_UnaryOp(self, node: UnaryOp):
        expr = self.visit(node.expr)
        if node.op == '!':
            zero = ir.Constant(BOOL_TYPE, 0)
            return self.builder.icmp_signed('==', expr, zero)
        elif node.op == '-':
            zero = ir.Constant(INT_TYPE, 0)
            return self.builder.sub(zero, expr)
        else:
            raise RuntimeError(f"Operador unario desconocido: {node.op}")

    def visit_IfStmt(self, node: IfStmt):
        cond = self.visit(node.cond)

        # Convertir a bool si es necesario (los enteros pueden usarse como condiciones)
        if cond.type == INT_TYPE:
            zero = ir.Constant(INT_TYPE, 0)
            cond = self.builder.icmp_signed('!=', cond, zero)
        elif cond.type != BOOL_TYPE:
            raise RuntimeError(f"Condición debe ser bool, no {cond.type}")

        # Crear bloques
        then_block = self.builder.append_basic_block("if.then")
        merge_block = self.builder.append_basic_block("if.merge")
        else_block = merge_block

        if node.else_body:
            else_block = self.builder.append_basic_block("if.else")

        self.builder.cbranch(cond, then_block, else_block)

        # Then
        self.builder.position_at_end(then_block)
        self.visit(node.then_body)
        self.builder.branch(merge_block)

        # Else
        if node.else_body:
            self.builder.position_at_end(else_block)
            self.visit(node.else_body)
            self.builder.branch(merge_block)

        # Merge
        self.builder.position_at_end(merge_block)

    def visit_ForStmt(self, node: ForStmt):
        header = self.builder.append_basic_block("for.header")
        body = self.builder.append_basic_block("for.body")
        after = self.builder.append_basic_block("for.after")

        self.builder.branch(header)

        self.builder.position_at_end(header)
        cond = self.visit(node.cond)
        if cond.type == INT_TYPE:
            zero = ir.Constant(INT_TYPE, 0)
            cond = self.builder.icmp_signed('!=', cond, zero)
        self.builder.cbranch(cond, body, after)

        self.builder.position_at_end(body)
        self.visit(node.body)
        self.builder.branch(header)

        self.builder.position_at_end(after)
        # No return

    def visit_Call(self, node: Call):
        if node.func_name in ['print', 'println']:
            arg = node.args[0]
            self.visit(node.args[0])  # Asegura que el valor esté en r0 (para expresiones)

            # Determinar formato y argumentos
            if isinstance(arg, Literal) and arg.type_tag == 'string':
                # Texto literal: usar %s
                fmt_str = arg.value
                if node.func_name == 'println':
                    fmt_str += '\n'
                # Codificar a UTF-8 + \0
                encoded = fmt_str.encode('utf8') + b'\x00'
                n = len(encoded)
                cfmt = ir.Constant(
                    ir.ArrayType(ir.IntType(8), n),
                    bytearray(encoded)
                )
                global_fmt = ir.GlobalVariable(
                    self.module, cfmt.type,
                    name=f"fmt.{len(self.module.globals)}"
                )
                global_fmt.linkage = 'private'
                global_fmt.global_constant = True
                global_fmt.initializer = cfmt
                fmt_ptr = self.builder.bitcast(global_fmt, STRING_TYPE)
                # Llamar: printf(fmt)
                self.builder.call(self.printf, [fmt_ptr])

            elif isinstance(arg, Identifier) or isinstance(arg, BinOp) or isinstance(arg, UnaryOp):
                # Imprimir entero
                fmt_str = "%d"
                if node.func_name == 'println':
                    fmt_str += '\n'
                encoded = fmt_str.encode('utf8') + b'\x00'
                n = len(encoded)
                cfmt = ir.Constant(
                    ir.ArrayType(ir.IntType(8), n),
                    bytearray(encoded)
                )
                global_fmt = ir.GlobalVariable(
                    self.module, cfmt.type,
                    name=f"fmt.{len(self.module.globals)}"
                )
                global_fmt.linkage = 'private'
                global_fmt.global_constant = True
                global_fmt.initializer = cfmt
                fmt_ptr = self.builder.bitcast(global_fmt, STRING_TYPE)
                # Promover int a i64 para var_arg
                int_val = self.visit(arg)
                int64_val = self.builder.zext(int_val, ir.IntType(64))
                # Llamar: printf(fmt, value)
                self.builder.call(self.printf, [fmt_ptr, int64_val])

            else:
                raise RuntimeError(f"Tipo no soportado en print: {arg}")
        else:
            raise RuntimeError(f"Función no soportada: {node.func_name}")
        
    def print_clean_ir(self):
        """Imprime el IR sin nombres internos ni metadatos"""
        lines = str(self.module).splitlines()
        clean_lines = []
        for line in lines:
            # Eliminar comentarios
            if '!' in line and not line.startswith('!'):
                continue
            # Eliminar nombres temporales como %".1", pero mantener %printf
            if 'declare' in line and 'printf' in line:
                clean_lines.append('declare i32 @printf(i8*, ...)')
            elif '@fmt.' in line or '@str.' in line:
                # Mantener constantes, pero limpiar posible metadata
                if 'private constant' in line:
                    clean_lines.append(line.split(',')[0] + '}')
                else:
                    clean_lines.append(line)
            else:
                # Eliminar nombres de temporales si están entre comillas
                cleaned = line.replace('"', '')
                clean_lines.append(cleaned)
        return '\n'.join(clean_lines)