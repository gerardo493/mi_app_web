import os
import shutil
import datetime
import subprocess
import json
from pathlib import Path
import time

def crear_backup():
    print("Iniciando proceso de backup...")
    # Crear directorio de backups si no existe
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)
    
    # Crear nombre del backup con fecha y hora
    fecha = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"backup_{fecha}"
    backup_path = backup_dir / backup_name
    
    # Archivos y directorios a respaldar
    archivos_a_respaldar = [
        "clientes.json",
        "inventario.json",
        "cuentas_por_cobrar.json",
        "facturas_json",
        "cotizaciones_json",
        "reportes_clientes",
        "reportes_cuentas",
        "reportes_facturas",
        "reportes_generales",
        "reportes_pagos",
        "historial_clientes"
    ]
    
    # Crear directorio del backup
    backup_path.mkdir(exist_ok=True)
    
    # Copiar archivos y directorios
    for item in archivos_a_respaldar:
        if os.path.exists(item):
            if os.path.isfile(item):
                shutil.copy2(item, backup_path)
                print(f"✓ Backup de archivo: {item}")
            else:
                shutil.copytree(item, backup_path / item, dirs_exist_ok=True)
                print(f"✓ Backup de directorio: {item}")
    
    print(f"✅ Backup completado en: {backup_path}")
    return backup_path

def subir_cambios():
    try:
        print("\n=== Iniciando proceso de subida de cambios ===")
        
        # Crear backup antes de subir cambios
        backup_path = crear_backup()
        
        print("\nVerificando estado de Git...")
        # Asegurarse de estar en la rama maestro
        subprocess.run(["git", "checkout", "maestro"], check=True)
        
        print("\nAgregando cambios a Git...")
        # Agregar todos los cambios
        subprocess.run(["git", "add", "."], check=True)
        
        # Crear commit con fecha y hora
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = f"Actualización automática: {fecha}"
        print(f"\nCreando commit: {mensaje}")
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        
        print("\nSubiendo cambios a GitHub...")
        # Subir cambios a la rama maestro
        subprocess.run(["git", "push", "origin", "maestro"], check=True)
        
        print("\n✅ Cambios subidos exitosamente a GitHub en la rama maestro")
        print(f"✅ Backup local creado en: {backup_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al subir cambios: {e}")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")

def verificar_rutas_imagenes():
    print("\nVerificando rutas de imágenes en el inventario...")
    try:
        # Cargar inventario
        with open('inventario.json', 'r', encoding='utf-8') as f:
            inventario = json.load(f)

        cambios = 0
        total_productos = len(inventario)
        productos_con_imagen = 0
        productos_sin_imagen = 0

        for prod_id, prod in inventario.items():
            if 'ruta_imagen' in prod:
                if prod['ruta_imagen']:
                    productos_con_imagen += 1
                    if isinstance(prod['ruta_imagen'], str) and '\\' in prod['ruta_imagen']:
                        prod['ruta_imagen'] = prod['ruta_imagen'].replace('\\', '/')
                        cambios += 1
                else:
                    productos_sin_imagen += 1

        if cambios > 0:
            with open('inventario.json', 'w', encoding='utf-8') as f:
                json.dump(inventario, f, ensure_ascii=False, indent=4)
            print(f"✅ Rutas corregidas en {cambios} productos.")
        else:
            print("ℹ️ No se encontraron rutas que necesiten corrección.")
        
        print(f"\nResumen del inventario:")
        print(f"- Total de productos: {total_productos}")
        print(f"- Productos con imagen: {productos_con_imagen}")
        print(f"- Productos sin imagen: {productos_sin_imagen}")
        
    except Exception as e:
        print(f"❌ Error al verificar rutas: {e}")

if __name__ == "__main__":
    verificar_rutas_imagenes()
    subir_cambios()
    print("\nProceso completado. Presione Enter para salir...")
    input() 