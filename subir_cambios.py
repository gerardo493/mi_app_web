import os
import subprocess
import sys
from datetime import datetime

def ejecutar_comando(comando):
    try:
        resultado = subprocess.run(comando, shell=True, check=True, capture_output=True, text=True)
        return resultado.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error al ejecutar el comando: {e}")
        print(f"Detalles del error: {e.stderr}")
        return None

def verificar_cambios():
    print("\n=== Verificando cambios en el repositorio ===")
    status = ejecutar_comando("git status")
    if status:
        print(status)
    return status

def agregar_cambios():
    print("\n=== Agregando cambios al staging ===")
    resultado = ejecutar_comando("git add .")
    if resultado:
        print("Cambios agregados exitosamente")

def hacer_commit(mensaje=None):
    if not mensaje:
        fecha = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        mensaje = f"Actualización automática - {fecha}"
    
    print(f"\n=== Realizando commit con mensaje: {mensaje} ===")
    resultado = ejecutar_comando(f'git commit -m "{mensaje}"')
    if resultado:
        print("Commit realizado exitosamente")

def subir_cambios():
    print("\n=== Subiendo cambios al repositorio remoto ===")
    resultado = ejecutar_comando("git push origin main")
    if resultado:
        print("Cambios subidos exitosamente")

def main():
    print("=== Herramienta para subir cambios a Git ===")
    
    # Verificar si hay cambios
    status = verificar_cambios()
    if "nothing to commit" in status:
        print("\nNo hay cambios para subir.")
        return

    # Preguntar si desea continuar
    respuesta = input("\n¿Desea continuar con el proceso? (s/n): ").lower()
    if respuesta != 's':
        print("Proceso cancelado.")
        return

    # Preguntar por el mensaje del commit
    mensaje = input("\nIngrese el mensaje para el commit (o presione Enter para usar el mensaje por defecto): ")
    
    # Ejecutar el proceso
    agregar_cambios()
    hacer_commit(mensaje if mensaje else None)
    subir_cambios()

if __name__ == "__main__":
    main() 