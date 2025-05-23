import os
import shutil
import datetime
import subprocess
import json
from pathlib import Path

def crear_backup():
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
            else:
                shutil.copytree(item, backup_path / item, dirs_exist_ok=True)
    
    print(f"Backup creado en: {backup_path}")
    return backup_path

def subir_cambios():
    try:
        # Crear backup antes de subir cambios
        backup_path = crear_backup()
        
        # Asegurarse de estar en la rama maestro
        subprocess.run(["git", "checkout", "maestro"], check=True)
        
        # Agregar todos los cambios
        subprocess.run(["git", "add", "."], check=True)
        
        # Crear commit con fecha y hora
        fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = f"Actualización automática: {fecha}"
        subprocess.run(["git", "commit", "-m", mensaje], check=True)
        
        # Subir cambios a la rama maestro
        subprocess.run(["git", "push", "origin", "maestro"], check=True)
        
        print("Cambios subidos exitosamente a GitHub en la rama maestro")
        print(f"Backup local creado en: {backup_path}")
        
    except subprocess.CalledProcessError as e:
        print(f"Error al subir cambios: {e}")
    except Exception as e:
        print(f"Error inesperado: {e}")

if __name__ == "__main__":
    subir_cambios() 