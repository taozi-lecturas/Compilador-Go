# lexer.py
import ply.lex as lex

# === Lista de nombres de tokens ===
tokens = [
    'IDENTIFIER',
    'NUMBER',
    'STRING',

    # Operadores
    'PLUS', 'MINUS', 'TIMES', 'DIVIDE', 'MOD',

    # Asignación
    'EQUALS', 'ASSIGN',  # == y =

    # Comparaciones
    'LT', 'LE', 'GT', 'GE',

    # Lógicos
    'AND', 'OR', 'NOT',

    # Delimitadores
    'LPAREN', 'RPAREN',
    'LBRACE', 'RBRACE',
    'SEMICOLON', 'COMMA',
]

# === Palabras clave (reservadas) ===
reserved = {
    'var': 'VAR',
    'func': 'FUNC',
    'main': 'MAIN',
    'int': 'TYPE_INT',
    'bool': 'TYPE_BOOL',
    'true': 'TRUE',
    'false': 'FALSE',
    'if': 'IF',
    'else': 'ELSE',
    'for': 'FOR',
    'print': 'PRINT',
    'println': 'PRINTLN',
}

tokens += list(reserved.values())

# === Expresiones regulares para tokens simples ===
t_PLUS      = r'\+'
t_MINUS     = r'-'
t_TIMES     = r'\*'
t_DIVIDE    = r'/'
t_MOD       = r'%'

t_EQUALS    = r'=='
t_ASSIGN    = r'='
t_LT        = r'<'
t_LE        = r'<='
t_GT        = r'>'
t_GE        = r'>='

t_NOT       = r'!'
t_AND       = r'&&'
t_OR        = r'\|\|'

t_LPAREN    = r'\('
t_RPAREN    = r'\)'
t_LBRACE    = r'\{'
t_RBRACE    = r'\}'
t_SEMICOLON = r';'
t_COMMA     = r','

# Ignorar espacios y tabs
t_ignore = ' \t'

# Contador de líneas
def t_newline(t):
    r'\n+'
    t.lexer.lineno += len(t.value)

# Manejo de comentarios (opcionales, pero útiles)
def t_COMMENT(t):
    r'//.*'
    pass  # Ignorar

# Identificadores y palabras reservadas
def t_IDENTIFIER(t):
    r'[a-zA-Z_][a-zA-Z_0-9]*'
    t.type = reserved.get(t.value, 'IDENTIFIER')  # Chequear si es palabra clave
    return t

# Números enteros
def t_NUMBER(t):
    r'\d+'
    t.value = int(t.value)
    return t

# String literals (entre comillas dobles)
def t_STRING(t):
    r'"([^"\\]|\\.)*"'
    # Remover comillas y manejar escapes básicos si queremos (opcional)
    t.value = t.value[1:-1] \
        .replace('\\n', '\n') \
        .replace('\\t', '\t') \
        .replace('\\"', '"')
    return t

# Manejo de errores
def t_error(t):
    print(f"Carácter ilegal '{t.value[0]}' en línea {t.lexer.lineno}")
    t.lexer.skip(1)

# === Construcción del lexer ===
lexer = lex.lex()

# === Prueba opcional ===
""" if __name__ == "__main__":
    test_code = '''
    func main() {
        var a int = 10
        var b int = 1
        var c int = 0

        for b < a {
            b = b + 1
            if b % 2 == 0 {
                c = c + b
            }
        }

        print("Suma de pares: ")
        println(c)
    }
    '''

    lexer.input(test_code)
    while True:
        tok = lexer.token()
        if not tok:
            break
        print(tok) """