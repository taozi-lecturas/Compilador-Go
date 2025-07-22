# mg_parser.py
# Asume que el código ya fue preprocesado: sin package, sin import, y fmt.Print → print. 

from ply import yacc
from mg_ast import *
from mg_lexer import tokens, lexer  # ← ¡Importamos tokens aquí!

# Precedencia para operadores (de menor a mayor prioridad)
precedence = (
    ('left', 'OR'),           # Menor precedencia
    ('left', 'AND'),
    ('left', 'EQUALS'),
    ('left', 'LT', 'LE', 'GT', 'GE'),
    ('left', 'PLUS', 'MINUS'),
    ('left', 'TIMES', 'DIVIDE', 'MOD'),
    ('right', 'NOT'),
    ('right', 'UMINUS'),      # Mayor precedencia
)

# ====================
# Reglas del Parser
# ====================

def p_program(p):
    'program : func_main'
    p[0] = Program(p[1])

def p_func_main(p):
    'func_main : FUNC MAIN LPAREN RPAREN LBRACE block RBRACE'
    p[0] = Function(name="main", body=p[6])

def p_block(p):
    'block : statement_list'
    p[0] = Block(statements=p[1])

def p_statement_list_empty(p):
    'statement_list :'
    p[0] = []

def p_statement_list_many(p):
    'statement_list : statement_list statement'
    p[0] = p[1] + [p[2]]

# --------------------
# Sentencias
# --------------------
def p_type_spec(p):
    '''type_spec : TYPE_INT
                 | TYPE_BOOL'''
    p[0] = p[1]  # Devuelve el nombre del tipo como string: 'int' o 'bool'

def p_statement_var_decl(p):
    'statement : VAR IDENTIFIER type_spec ASSIGN expression'
    p[0] = VarDecl(name=p[2], type_name=p[3], expr=p[5])

def p_statement_assign(p):
    'statement : IDENTIFIER ASSIGN expression'
    p[0] = Assign(name=p[1], expr=p[3])

def p_statement_if(p):
    '''statement : IF expression LBRACE block RBRACE
                 | IF expression LBRACE block RBRACE ELSE LBRACE block RBRACE'''
    if len(p) == 6:
        p[0] = IfStmt(cond=p[2], then_body=p[4], else_body=None)
    else:
        p[0] = IfStmt(cond=p[2], then_body=p[4], else_body=p[8])

def p_statement_for(p):
    'statement : FOR expression LBRACE block RBRACE'
    p[0] = ForStmt(cond=p[2], body=p[4])

def p_statement_expr(p):
    'statement : expression'
    # Expresiones como llamadas: print(...)
    p[0] = p[1]  # Pero en AST, las llamadas ya son "statements" implícitos

# Permitimos bloques como sentencias
def p_statement_block(p):
    'statement : LBRACE block RBRACE'
    p[0] = p[2]

# --------------------
# Expresiones
# --------------------

def p_expression_binop(p):
    '''expression : expression PLUS expression
                  | expression MINUS expression
                  | expression TIMES expression
                  | expression DIVIDE expression
                  | expression MOD expression
                  | expression EQUALS expression
                  | expression LT expression
                  | expression LE expression
                  | expression GT expression
                  | expression GE expression
                  | expression AND expression
                  | expression OR expression'''
    p[0] = BinOp(left=p[1], op=p[2], right=p[3])

def p_expression_unary_not(p):
    'expression : NOT expression'
    p[0] = UnaryOp(op=p[1], expr=p[2])

def p_expression_uminus(p):
    'expression : MINUS expression %prec UMINUS'
    p[0] = UnaryOp(op='-', expr=p[2])

def p_expression_group(p):
    'expression : LPAREN expression RPAREN'
    p[0] = p[2]

def p_expression_number(p):
    'expression : NUMBER'
    p[0] = Literal(value=p[1], type_tag='int')

def p_expression_string(p):
    'expression : STRING'
    p[0] = Literal(value=p[1], type_tag='string')

def p_expression_true(p):
    'expression : TRUE'
    p[0] = Literal(value=True, type_tag='bool')

def p_expression_false(p):
    'expression : FALSE'
    p[0] = Literal(value=False, type_tag='bool')

def p_expression_identifier(p):
    'expression : IDENTIFIER'
    p[0] = Identifier(name=p[1])

# --------------------
# Llamadas a funciones: print / println
# --------------------

def p_expression_call(p):
    '''expression : PRINT LPAREN expression RPAREN
                  | PRINTLN LPAREN expression RPAREN'''
    p[0] = Call(func_name=p[1], args=[p[3]])

# --------------------
# Manejo de errores
# --------------------

def p_error(p):
    if p:
        raise SyntaxError(f"Error de sintaxis en token '{p.value}' (tipo={p.type}) en línea {p.lineno}")
    else:
        raise SyntaxError("Error de sintaxis: EOF inesperado")

# ====================
# Construcción del parser
# ====================

parser = yacc.yacc(debug=False, write_tables=False)