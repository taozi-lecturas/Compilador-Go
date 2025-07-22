# main.py
import subprocess
import os
import sys
from preprocessor import preprocess_source
from mg_lexer import lexer
from mg_parser import parser
from semant import SemanticAnalyzer
from codegen import CodeGen

OUTPUT_DIR = "output"

def parse_file(filepath, filename_base):
    print(f"\n📄 Analizando: {filepath}")
    print("=" * 60)

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            code = f.read()
    except Exception as e:
        print(f"❌ Error al leer el archivo: {e}")
        return

    try:
        processed_code = preprocess_source(code)
    except Exception as e:
        print(f"❌ Error en preprocesamiento: {e}")
        return

    try:
        lexer.input(processed_code)
        while lexer.token(): pass
    except Exception as e:
        print(f"❌ Error en tokenización: {e}")
        return

    try:
        ast = parser.parse(processed_code, lexer=lexer)
        if ast is None:
            print("❌ AST es None.")
            return
    except Exception as e:
        print(f"❌ Error en parsing: {e}")
        return

    try:
        analyzer = SemanticAnalyzer()
        if not analyzer.analyze(ast):
            print("❌ Errores semánticos:")
            for error in analyzer.errors:
                print(f"  • {error.message}")
            return
    except Exception as e:
        print(f"❌ Error en análisis semántico: {e}")
        return

    try:
        cg = CodeGen()
        cg.compile(ast)

        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ll_path = os.path.join(OUTPUT_DIR, f"{filename_base}.ll")
        o_path = os.path.join(OUTPUT_DIR, f"{filename_base}.o")
        bin_path = os.path.join(OUTPUT_DIR, f"{filename_base}.bin")

        with open(ll_path, "w") as f:
            f.write(str(cg.module))
        print(f"✅ Guardado IR en: {ll_path}")

        if emit_object_file(ll_path, o_path):
            link_binary(o_path, bin_path)

    except Exception as e:
        print(f"❌ Error en generación de código: {e}")
        return

def emit_object_file(input_ll, output_o):
    print(f"🔧 Generando objeto: {output_o}")
    try:
        subprocess.run([
            "llc", "-march=arm", "-mcpu=generic", "-mattr=+vfp2",
            "-float-abi=hard", "-filetype=obj", input_ll, "-o", output_o
        ], check=True, capture_output=True, text=True)
        print(f"✅ Objeto generado: {output_o}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en llc:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ 'llc' no encontrado. Instale LLVM.")
        return False

def link_binary(input_o, output_bin):
    print(f"🔗 Enlazando binario: {output_bin}")
    try:
        subprocess.run([
            "arm-linux-gnueabihf-gcc", input_o, "-o", output_bin
        ], check=True, capture_output=True, text=True)
        print(f"✅ Binario ARM generado: {output_bin}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en enlazado:\n{e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ 'arm-linux-gnueabihf-gcc' no encontrado.")
        return False

def main():
    tests_dir = "tests"
    if not os.path.isdir(tests_dir):
        print(f"❌ Carpeta '{tests_dir}' no encontrada.")
        return

    archivos = [f for f in os.listdir(tests_dir) if f.endswith(".go")]
    if not archivos:
        print("⚠️ No hay archivos .go en tests/")
        return

    print(f"🔍 Archivos detectados en tests/: {archivos}")
    for archivo in archivos:
        path = os.path.join(tests_dir, archivo)
        base = os.path.splitext(archivo)[0]
        parse_file(path, base)

    print("\n🎉 Proceso finalizado para todos los archivos.")

if __name__ == "__main__":
    main()
