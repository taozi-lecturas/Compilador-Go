# main.py
import subprocess
import os
import sys
from preprocessor import preprocess_source
from mg_lexer import lexer
from mg_parser import parser
from semant import SemanticAnalyzer
from codegen import CodeGen


def parse_file(filepath):
    # Nombre base sin extensión
    basename = os.path.splitext(os.path.basename(filepath))[0]
    print(f"\n📄 Analizando: {filepath}")
    print("=" * 60)

    # Directorio de salida
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # Rutas de salida
    ll_path = os.path.join(output_dir, f"{basename}.ll")
    o_path = os.path.join(output_dir, f"{basename}.o")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return None

    # Preprocesar
    try:
        processed_code = preprocess_source(code)
        print("✅ Código preprocesado:")
        print("---")
        print(processed_code)
        print("---")
    except Exception as e:
        print(f"❌ Error en preprocesamiento: {e}")
        return None

    # Tokenización
    try:
        print("📝 Tokens generados:")
        lexer.input(processed_code)
        has_tokens = False
        while True:
            tok = lexer.token()
            if not tok:
                break
            print(tok)
            has_tokens = True
        if not has_tokens:
            print("  (ningún token generado)")
    except Exception as e:
        print(f"❌ Error en tokenización: {e}")
        return None

    # Parseo
    ast = None
    try:
        print("\n🧩 Generando AST...")
        ast = parser.parse(processed_code, lexer=lexer)
        if ast is not None:
            print(ast)
            print("✅ AST generado exitosamente.")
        else:
            print("❌ AST es None.")
            return None
    except SyntaxError as e:
        print(f"❌ Error de sintaxis: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado en parsing: {e}")
        return None

    # === Análisis semántico ===
    try:
        print("\n🔍 Análisis semántico...")
        analyzer = SemanticAnalyzer()
        if analyzer.analyze(ast):
            print("✅ Sin errores semánticos.")
        else:
            print("❌ Errores semánticos encontrados:")
            for error in analyzer.errors:
                print(f"  • {error.message}")
            return None
    except Exception as e:
        print(f"❌ Error en análisis semántico: {e}")
        return None

    # === Generación de código LLVM IR ===
    print("\n💻 Generando código LLVM IR...")
    try:
        cg = CodeGen()
        cg.compile(ast)
        print("✅ Código LLVM generado:")

        # Guardar .ll
        with open(ll_path, "w") as f:
            f.write(str(cg.module))
        print(f"📄 IR guardado en '{ll_path}'")

        # Emitir objeto ARMv6
        if emit_object_file(ll_path, o_path):
            print(f"✅ Objeto ARMv6 generado: {o_path}")
        else:
            print(f"❌ Fallo al generar objeto: {o_path}")
            return None

    except Exception as e:
        print(f"❌ Error en generación de código: {e}")
        return None

    return ast


def emit_object_file(input_ll, output_o):
    """Genera el archivo .o usando llc, compatible con arm-linux-gnueabihf"""
    print(f"🔧 Generando objeto desde {input_ll} → {output_o}")

    try:
        result = subprocess.run([
            "llc",
            "-march=arm",
            "-mcpu=generic",
            "-mattr=+vfp2",
            "-float-abi=hard",
            "-filetype=obj",
            input_ll,
            "-o", output_o
        ], check=True, capture_output=True, text=True)

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en llc ({input_ll}): {e.stderr.strip()}")
        return False
    except FileNotFoundError:
        print("❌ 'llc' no encontrado. Instala LLVM: sudo apt install llvm")
        return False


def main():
    tests_dir = "tests"
    output_dir = "output"

    if not os.path.exists(tests_dir):
        print(f"❌ Carpeta '{tests_dir}' no encontrada.")
        sys.exit(1)

    go_files = [f for f in os.listdir(tests_dir) if f.endswith(".go")]

    if not go_files:
        print(f"⚠️ No se encontraron archivos '.go' en '{tests_dir}/'")
        sys.exit(0)

    print(f"🔍 Encontrados {len(go_files)} archivo(s) para analizar en '{tests_dir}/':")
    for f in go_files:
        print(f"  - {f}")

    # Crear carpeta de salida
    os.makedirs(output_dir, exist_ok=True)
    print(f"\n📁 Carpeta de salida creada o verificada: ./{output_dir}/")

    # Procesar cada archivo
    success_count = 0
    for filename in go_files:
        filepath = os.path.join(tests_dir, filename)
        print("\n" + "─" * 50)
        if parse_file(filepath) is not None:
            success_count += 1

    print(f"\n🎉 Proceso completado.")
    print(f"📦 Archivos procesados: {len(go_files)}")
    print(f"✅ Éxitos: {success_count}, ❌ Fallos: {len(go_files) - success_count}")
    print(f"📂 Todos los archivos .ll y .o están en './{output_dir}/'")


if __name__ == "__main__":
    main()