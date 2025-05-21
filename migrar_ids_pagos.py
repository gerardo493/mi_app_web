import json
import os
from uuid import uuid4

ARCHIVO_FACTURAS = 'facturas_json/facturas.json'

def migrar_ids_pagos():
    if not os.path.exists(ARCHIVO_FACTURAS):
        print('No existe el archivo de facturas.')
        return
    with open(ARCHIVO_FACTURAS, 'r', encoding='utf-8') as f:
        facturas = json.load(f)
    cambios = 0
    for fid, factura in facturas.items():
        pagos = factura.get('pagos', [])
        for pago in pagos:
            if 'id' not in pago or not pago['id']:
                pago['id'] = str(uuid4())
                cambios += 1
        factura['pagos'] = pagos
        facturas[fid] = factura
    if cambios > 0:
        with open(ARCHIVO_FACTURAS, 'w', encoding='utf-8') as f:
            json.dump(facturas, f, ensure_ascii=False, indent=4)
        print(f'Se asignaron {cambios} ids a pagos sin identificador.')
    else:
        print('Todos los pagos ya tenían id.')

if __name__ == '__main__':
    migrar_ids_pagos() 