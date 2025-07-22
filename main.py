# main.py
import subprocess
import os
import sys
from preprocessor import preprocess_source
from mg_lexer import lexer
from mg_parser import parser
from semant import SemanticAnalyzer
from codegen import CodeGen  # Asegúrate de tener este archivo


def parse_file(filepath, output_dir="output"):
    # Crear directorio de salida si no existe
    os.makedirs(output_dir, exist_ok=True)
    
    # Obtener el nombre base del archivo sin extensión
    base_name = os.path.splitext(os.path.basename(filepath))[0]
    
    print(f"\n📄 Analizando: {filepath}")
    print("=" * 60)
    
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
        print(cg.module)

        # Guardar .ll con nombre basado en el archivo de entrada
        ll_filename = os.path.join(output_dir, f"{base_name}.ll")
        with open(ll_filename, "w") as f:
            f.write(str(cg.module))
        print(f"📄 IR guardado en '{ll_filename}'")

        # Emitir objeto ARMv6
        o_filename = os.path.join(output_dir, f"{base_name}.o")
        if emit_object_file(cg, output_ll=ll_filename, output_o=o_filename):
            # Enlazar binario
            bin_filename = os.path.join(output_dir, f"{base_name}_armv7")
            link_binary(output_o=o_filename, output_bin=bin_filename)

    except Exception as e:
        print(f"❌ Error en generación de código: {e}")
        return None

    return ast  # Opcional: si quieres usarlo después


def emit_object_file(cg, output_ll="output.ll", output_o="output.o"):
    """Genera archivo .o para ARMv7 + hard-float usando llc"""
    print(f"\n🔧 Emitiendo código objeto: {output_o} (ARMv7 + hard-float)")

    # Guardar LLVM IR
    with open(output_ll, "w") as f:
        f.write(str(cg.module))

    try:
        result = subprocess.run([
            "llc",
            "-march=arm",                       # Arquitectura ARM
            "-mtriple=armv7l-linux-gnueabihf",  # Triple clave: little-endian ARMv7 + hf
            "-mcpu=cortex-a7",                  # CPU común de ARMv7
            "-float-abi=hard",                  # ABI con FPU
            "-filetype=obj",
            output_ll,
            "-o", output_o
        ], check=True, capture_output=True, text=True)

        print(f"✅ Archivo objeto generado: {output_o}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en llc: {e.stderr}")
        print(f"📝 Salida: {e.stdout}")
        return False
    except FileNotFoundError:
        print("❌ 'llc' no encontrado. Instala LLVM: sudo apt install llvm")
        return False

def link_binary(output_o="output.o", output_bin="programa_armv7"):
    """Enlaza el objeto en un binario estático ARMv7"""
    print(f"\n🔗 Enlazando binario: {output_bin}")

    try:
        result = subprocess.run([
            "arm-linux-gnueabihf-gcc",
            "-static",              # Sin dependencias dinámicas
            "-march=armv7-a",       # Objetivo: ARMv7-A
            "-mfpu=vfpv3-d16",      # FPU requerido
            "-mfloat-abi=hard",     # Hard-float ABI
            output_o,
            "-o", output_bin
        ], check=True, capture_output=True, text=True)

        print(f"✅ Binario generado: {output_bin}")

        # Mostrar info básica del binario
        try:
            objdump = subprocess.run(
                ["arm-linux-gnueabihf-readelf", "-A", output_bin],
                capture_output=True, text=True, check=True
            )
            attrs = objdump.stdout.strip()
            for line in attrs.splitlines():
                if "Tag_CPU_arch" in line or "Tag_FP_arch" in line or "Tag_ABI_VFP_args" in line:
                    print(f"   {line.strip()}")
        except:
            pass

        return True

    except subprocess.CalledProcessError as e:
        print(f"❌ Error en enlazado: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ 'arm-linux-gnueabihf-gcc' no encontrado. Instala: sudo apt install gcc-arm-linux-gnueabihf")
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
    
    # Crear directorio de salida
    os.makedirs(output_dir, exist_ok=True)
    
    # Procesar cada archivo
    for filename in go_files:
        filepath = os.path.join(tests_dir, filename)
        parse_file(filepath, output_dir)
    
    print("\n🎉 Análisis y generación de código completados.")


if __name__ == "__main__":
    main()  # ← Todo está dentro de main(), sin código adicional suelto