import os
import requests
from PIL import Image
from io import BytesIO
import time

# Crear directorio si no existe
os.makedirs('static/bancos', exist_ok=True)

# Diccionario de bancos y sus URLs de logos (usando imágenes directas de diferentes fuentes)
BANCOS = {
    'banco_venezuela': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/Banco_de_Venezuela_logo.png',
    'venezolano_credito': 'https://upload.wikimedia.org/wikipedia/commons/8/8a/Banco_Venezolano_de_Crédito_logo.png',
    'mercantil': 'https://upload.wikimedia.org/wikipedia/commons/4/4a/Banco_Mercantil_logo.png',
    'provincial': 'https://upload.wikimedia.org/wikipedia/commons/9/9a/Banco_Provincial_logo.png',
    'bancaribe': 'https://upload.wikimedia.org/wikipedia/commons/3/3a/Bancaribe_logo.png',
    'exterior': 'https://upload.wikimedia.org/wikipedia/commons/5/5a/Banco_Exterior_logo.png',
    'occidental': 'https://upload.wikimedia.org/wikipedia/commons/7/7a/Banco_Occidental_de_Descuento_logo.png',
    'caroni': 'https://upload.wikimedia.org/wikipedia/commons/8/8a/Banco_Caroni_logo.png',
    'banesco': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/Banesco_logo.png',
    'sofitasa': 'https://upload.wikimedia.org/wikipedia/commons/9/9a/Sofitasa_logo.png',
    'plaza': 'https://upload.wikimedia.org/wikipedia/commons/3/3a/Banco_Plaza_logo.png',
    'bge': 'https://upload.wikimedia.org/wikipedia/commons/4/4a/BGE_logo.png',
    'bfc': 'https://upload.wikimedia.org/wikipedia/commons/5/5a/BFC_logo.png',
    '100banco': 'https://upload.wikimedia.org/wikipedia/commons/1/1a/100_Banco_logo.png',
    'delsur': 'https://upload.wikimedia.org/wikipedia/commons/8/8a/Banco_del_Sur_logo.png',
    'tesoro': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/Banco_del_Tesoro_logo.png',
    'agricola': 'https://upload.wikimedia.org/wikipedia/commons/9/9a/Banco_Agricola_logo.png',
    'bancrecer': 'https://upload.wikimedia.org/wikipedia/commons/3/3a/Bancrecer_logo.png',
    'mibanco': 'https://upload.wikimedia.org/wikipedia/commons/4/4a/Mibanco_logo.png',
    'activo': 'https://upload.wikimedia.org/wikipedia/commons/5/5a/Banco_Activo_logo.png',
    'bancamiga': 'https://upload.wikimedia.org/wikipedia/commons/8/8a/Bancamiga_logo.png',
    'bid': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/BID_logo.png',
    'banplus': 'https://upload.wikimedia.org/wikipedia/commons/3/3a/Banplus_logo.png',
    'bicentenario': 'https://upload.wikimedia.org/wikipedia/commons/4/4a/Banco_Bicentenario_logo.png',
    'novo': 'https://upload.wikimedia.org/wikipedia/commons/5/5a/Novo_Banco_logo.png',
    'banfanb': 'https://upload.wikimedia.org/wikipedia/commons/2/2a/BANFANB_logo.png'
}

def download_and_resize_logo(url, filename):
    try:
        print(f'Descargando logo de {filename}...')
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Referer': 'https://www.google.com/'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            # Abrir la imagen
            img = Image.open(BytesIO(response.content))
            
            # Convertir a RGBA si no lo es
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Redimensionar manteniendo la proporción
            max_size = (100, 100)
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Guardar la imagen
            output_path = f'static/bancos/{filename}.png'
            img.save(output_path, 'PNG', quality=95)
            print(f'✓ Logo descargado y guardado: {filename}')
            return True
        else:
            print(f'✗ Error al descargar {filename}: {response.status_code}')
            return False
    except Exception as e:
        print(f'✗ Error al procesar {filename}: {str(e)}')
        return False

def main():
    print('Iniciando descarga de logos de bancos...')
    success_count = 0
    total_bancos = len(BANCOS)
    
    for banco, url in BANCOS.items():
        if download_and_resize_logo(url, banco):
            success_count += 1
        time.sleep(1)  # Esperar 1 segundo entre descargas
    
    print(f'\nResumen:')
    print(f'Total de bancos: {total_bancos}')
    print(f'Logos descargados exitosamente: {success_count}')
    print(f'Logos fallidos: {total_bancos - success_count}')

if __name__ == '__main__':
    main() 