import os
import subprocess
import sys
from datetime import datetime

def ejecutar_comando(comando):
    """Ejecuta un comando y muestra su salida"""
    try:
        resultado = subprocess.run(comando, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {comando}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error al ejecutar: {comando}")
        print(f"Error: {e.stderr}")
        return False

def main():
    print("\n=== Iniciando proceso de despliegue ===\n")
    
    # Obtener la fecha y hora actual
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Verificar estado de git
    print("1. Verificando estado del repositorio...")
    if not ejecutar_comando("git status"):
        return
    
    # Agregar todos los cambios
    print("\n2. Agregando cambios...")
    if not ejecutar_comando("git add ."):
        return
    
    # Crear commit
    print("\n3. Creando commit...")
    mensaje_commit = f"Actualización automática - {fecha_actual}"
    if not ejecutar_comando(f'git commit -m "{mensaje_commit}"'):
        return
    
    # Subir cambios
    print("\n4. Subiendo cambios a Render...")
    if not ejecutar_comando("git push origin maestro"):
        return
    
    print("\n=== ¡Despliegue completado con éxito! ===")
    print("\nLa aplicación se está actualizando en Render.")
    print("Puedes verificar el estado del despliegue en tu panel de control de Render.")
    print("\nNota: El proceso de despliegue puede tomar unos minutos.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProceso cancelado por el usuario.")
        sys.exit(1)
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        sys.exit(1) 