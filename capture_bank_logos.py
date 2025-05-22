import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from PIL import Image

# Diccionario de bancos: url de la web principal y selector del logo
BANCOS = {
    'banco_venezuela': {
        'url': 'https://www.bancodevenezuela.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Venezuela"]'
    },
    'banesco': {
        'url': 'https://www.banesco.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Banesco"]'
    },
    'mercantil': {
        'url': 'https://www.mercantilbanco.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Mercantil"]'
    },
    'provincial': {
        'url': 'https://www.provincial.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Provincial"]'
    },
    'bancaribe': {
        'url': 'https://www.bancaribe.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Bancaribe"]'
    },
    'banplus': {
        'url': 'https://www.banplus.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Banplus"]'
    },
    'bicentenario': {
        'url': 'https://www.bicentenariobanco.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Bicentenario"]'
    },
    'bancamiga': {
        'url': 'https://www.bancamiga.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Bancamiga"]'
    },
    'sofitasa': {
        'url': 'https://www.sofitasa.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Sofitasa"]'
    },
    'plaza': {
        'url': 'https://www.bancoplaza.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Plaza"]'
    },
    'bge': {
        'url': 'https://www.bancobge.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="BGE"]'
    },
    'bfc': {
        'url': 'https://www.bfc.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="BFC"]'
    },
    '100banco': {
        'url': 'https://www.100banco.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="100"]'
    },
    'delsur': {
        'url': 'https://www.bancodelsur.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Sur"]'
    },
    'tesoro': {
        'url': 'https://www.bt.gob.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Tesoro"]'
    },
    'agricola': {
        'url': 'https://www.bav.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Agrícola"]'
    },
    'bancrecer': {
        'url': 'https://www.bancrecer.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Bancrecer"]'
    },
    'mibanco': {
        'url': 'https://www.mibanco.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Mibanco"]'
    },
    'activo': {
        'url': 'https://www.bancoactivo.com/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Activo"]'
    },
    'bid': {
        'url': 'https://www.bid.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="BID"]'
    },
    'novo': {
        'url': 'https://www.novobanco.com.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="Novo"]'
    },
    'banfanb': {
        'url': 'https://www.banfanb.gob.ve/',
        'selector': '.logo img, header img[src*="logo"], img[alt*="FANB"]'
    }
}

# Carpeta de destino
os.makedirs('static/bancos', exist_ok=True)

# Configuración de Selenium para Chrome en modo headless
chrome_options = Options()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--window-size=1920,1080')  # Resolución más alta
chrome_options.add_argument('--disable-gpu')
chrome_options.add_argument('--no-sandbox')
chrome_options.add_argument('--disable-dev-shm-usage')
chrome_options.add_argument('--disable-blink-features=AutomationControlled')
chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Cambia el path si tu chromedriver está en otro lugar
driver = webdriver.Chrome(options=chrome_options)
wait = WebDriverWait(driver, 10)  # Espera explícita de 10 segundos

def capture_logo(bank, info):
    try:
        print(f"Procesando {bank}...")
        driver.get(info['url'])
        
        # Esperar a que la página cargue completamente
        time.sleep(5)
        
        # Intentar diferentes selectores
        selectors = info['selector'].split(', ')
        logo = None
        
        for selector in selectors:
            try:
                logo = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                if logo:
                    break
            except:
                continue
        
        if not logo:
            raise Exception("No se encontró el logo con ningún selector")
            
        # Asegurarse de que el logo sea visible
        driver.execute_script("arguments[0].scrollIntoView(true);", logo)
        time.sleep(1)
        
        # Obtener ubicación y tamaño
        location = logo.location_once_scrolled_into_view
        size = logo.size
        
        # Tomar screenshot
        screenshot_path = f'static/bancos/{bank}_full.png'
        driver.save_screenshot(screenshot_path)
        
        # Recortar el logo
        image = Image.open(screenshot_path)
        left = int(location['x'])
        top = int(location['y'])
        right = left + int(size['width'])
        bottom = top + int(size['height'])
        
        # Añadir un pequeño margen
        margin = 5
        left = max(0, left - margin)
        top = max(0, top - margin)
        right = min(image.width, right + margin)
        bottom = min(image.height, bottom + margin)
        
        logo_image = image.crop((left, top, right, bottom))
        
        # Redimensionar manteniendo la proporción
        logo_image.thumbnail((100, 100), Image.LANCZOS)
        
        # Guardar el logo
        logo_image.save(f'static/bancos/{bank}.png', 'PNG', quality=95)
        os.remove(screenshot_path)
        print(f"✓ Logo guardado: static/bancos/{bank}.png")
        
    except Exception as e:
        print(f"✗ Error con {bank}: {str(e)}")
        # Guardar screenshot del error para debugging
        try:
            driver.save_screenshot(f'static/bancos/{bank}_error.png')
        except:
            pass

def main():
    print("Iniciando captura de logos...")
    success_count = 0
    total_bancos = len(BANCOS)
    
    for bank, info in BANCOS.items():
        capture_logo(bank, info)
        time.sleep(2)  # Espera entre bancos
    
    driver.quit()
    print("\nProceso terminado.")
    print(f"Total de bancos procesados: {total_bancos}")

if __name__ == '__main__':
    main() 