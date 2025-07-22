# preprocessor.py
def preprocess_source(source_code: str) -> str:
    lines = source_code.splitlines()
    output = []

    for line in lines:
        stripped = line.strip()

        # Ignorar package e import
        if stripped.startswith("package ") or stripped.startswith("import "):
            continue

        # Reemplazar fmt.Print y fmt.Println
        line = line.replace("fmt.Print", "print")
        line = line.replace("fmt.Println", "println")

        output.append(line)

    return "\n".join(output)