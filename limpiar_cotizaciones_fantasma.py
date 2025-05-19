import os
import json

COTIZACIONES_DIR = 'cotizaciones_json'

eliminados = 0
if os.path.exists(COTIZACIONES_DIR):
    for filename in os.listdir(COTIZACIONES_DIR):
        if filename.endswith('.json'):
            filepath = os.path.join(COTIZACIONES_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cot = json.load(f)
                if not cot.get('numero_cotizacion') or not cot.get('fecha') or not cot.get('cliente', {}).get('nombre'):
                    os.remove(filepath)
                    print(f"Eliminado: {filename}")
                    eliminados += 1
            except Exception as e:
                os.remove(filepath)
                print(f"Eliminado (inválido): {filename}")
                eliminados += 1
print(f"Total de cotizaciones fantasma eliminadas: {eliminados}") 