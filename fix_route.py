import re

# Leer el archivo
with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar la posición de la segunda definición
pattern = r'@app\.route\(\'/inventario/\<id\>/editar\'\)\n@login_required\ndef editar_producto\(id\):'
matches = list(re.finditer(pattern, content))

if len(matches) > 1:
    # Obtener la posición de inicio de la segunda definición
    start_pos = matches[1].start()
    
    # Encontrar el inicio del bloque de ejecución
    end_pattern = '# --- Bloque para Ejecutar la Aplicación ---'
    end_pos = content.find(end_pattern, start_pos)
    
    if end_pos != -1:
        # Eliminar la segunda definición
        new_content = content[:start_pos] + content[end_pos:]
        
        # Guardar el archivo
        with open('app.py', 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Cambio realizado exitosamente")
    else:
        print("No se encontró el final del bloque")
else:
    print("No se encontraron definiciones duplicadas") 