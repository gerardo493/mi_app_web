import os
import json

COTIZACIONES_DIR = 'cotizaciones_json'
NUMEROS_A_ELIMINAR = {'0001', '0002', '0004', '0005'}

eliminados = 0
if os.path.exists(COTIZACIONES_DIR):
    for filename in os.listdir(COTIZACIONES_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(COTIZACIONES_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cot = json.load(f)
                numero = cot.get('numero_cotizacion')
                if numero in NUMEROS_A_ELIMINAR:
                    os.remove(filepath)
                    print(f"Eliminado: {filename} (numero_cotizacion={numero})")
                    eliminados += 1
            except Exception as e:
                print(f"Error leyendo {filename}: {e}")
print(f"Total de cotizaciones eliminadas: {eliminados}") 