# -*- coding: utf-8 -*-
import json
import os
import urllib3
import requests
import csv
from bs4 import BeautifulSoup
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
try:
    import pdfkit
except ImportError:
    pdfkit = None

# --- Constantes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ARCHIVO_COTIZACIONES = 'cotizaciones_json/cotizaciones.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'
ALLOWED_EXTENSIONS = {'csv'}

# Asegurar que la carpeta de subidas existe
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
except Exception as e:
    print(f"Error creando carpeta de subidas: {e}")

# --- Funciones de Utilidad ---
def allowed_file(filename):
    """Verifica si la extensión del archivo está permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cargar_clientes_desde_csv(archivo_csv):
    """Carga clientes desde un archivo CSV."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                tipo_id = fila.get('tipo_id', 'V')
                numero_id = fila.get('numero_id', '').strip()
                if not numero_id.isdigit():
                    continue
                nuevo_id = f"{tipo_id}-{numero_id}"
                if nuevo_id not in clientes:
                    clientes[nuevo_id] = {
                        'id': nuevo_id,
                        'nombre': fila.get('nombre', '').strip(),
                        'email': fila.get('email', '').strip() if 'email' in fila else '',
                        'telefono': fila.get('telefono', '').strip() if 'telefono' in fila else '',
                        'direccion': fila.get('direccion', '').strip() if 'direccion' in fila else ''
                    }
        return guardar_datos(ARCHIVO_CLIENTES, clientes)
    except Exception as e:
        print(f"Error cargando clientes desde CSV: {e}")
        return False

def cargar_productos_desde_csv(archivo_csv):
    """Carga productos desde un archivo CSV."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    try:
        with open(archivo_csv, 'r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                nuevo_id = str(len(inventario) + 1)
                inventario[nuevo_id] = {
                    'nombre': fila.get('nombre', '').strip(),
                    'precio': float(fila.get('precio', 0)),
                    'cantidad': int(fila.get('cantidad', 0)),
                    'categoria': fila.get('categoria', '').strip(),
                    'ruta_imagen': "",
                    'ultima_entrada': None,
                    'ultima_salida': None
                }
        return guardar_datos(ARCHIVO_INVENTARIO, inventario)
    except Exception as e:
        print(f"Error cargando productos desde CSV: {e}")
        return False

def cargar_datos(nombre_archivo):
    """Carga datos desde un archivo JSON."""
    try:
        # Asegurar que el directorio existe
        directorio = os.path.dirname(nombre_archivo)
        if directorio:  # Si hay un directorio en la ruta
            os.makedirs(directorio, exist_ok=True)
            
        if not os.path.exists(nombre_archivo):
            print(f"Archivo {nombre_archivo} no existe. Creando nuevo archivo.")
            with open(nombre_archivo, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=False, indent=4)
            return {}
            
        with open(nombre_archivo, 'r', encoding='utf-8') as f:
            contenido = f.read()
            if not contenido.strip():
                print(f"Archivo {nombre_archivo} está vacío.")
                return {}
            try:
                return json.loads(contenido)
            except json.JSONDecodeError as e:
                print(f"Error decodificando JSON en {nombre_archivo}: {e}")
                return {}
    except Exception as e:
        print(f"Error leyendo {nombre_archivo}: {e}")
        return {}

def guardar_datos(nombre_archivo, datos):
    """Guarda datos en un archivo JSON."""
    try:
        # Asegurar que el directorio existe
        directorio = os.path.dirname(nombre_archivo)
        if directorio:  # Si hay un directorio en la ruta
            try:
                os.makedirs(directorio, exist_ok=True)
                print(f"Directorio {directorio} creado/verificado exitosamente")
            except Exception as e:
                print(f"Error creando directorio {directorio}: {e}")
                return False
        
        # Verificar que los datos son serializables
        try:
            json.dumps(datos)
        except Exception as e:
            print(f"Error serializando datos: {e}")
            return False
        
        # Intentar guardar con manejo de errores específico
        try:
            # Primero intentamos escribir en un archivo temporal
            temp_file = nombre_archivo + '.tmp'
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(datos, f, ensure_ascii=False, indent=4)
            
            # Si la escritura temporal fue exitosa, reemplazamos el archivo original
            if os.path.exists(nombre_archivo):
                os.remove(nombre_archivo)
            os.rename(temp_file, nombre_archivo)
            
            print(f"Datos guardados exitosamente en {nombre_archivo}")
            return True
        except Exception as e:
            print(f"Error escribiendo en archivo {nombre_archivo}: {e}")
            # Limpiar archivo temporal si existe
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass
            return False
    except Exception as e:
        print(f"Error general guardando {nombre_archivo}: {e}")
        return False

def obtener_estadisticas():
    """Obtiene estadísticas para el dashboard."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    # cuentas = cargar_datos(ARCHIVO_CUENTAS)  # Ya no se usa
    mes_actual = datetime.now().month
    total_clientes = len(clientes)
    total_productos = len(inventario)
    facturas_mes = sum(1 for f in facturas.values() if datetime.strptime(f['fecha'], '%Y-%m-%d').month == mes_actual)
    # Total cuentas por cobrar (sumar solo montos pendientes > 0 de facturas)
    total_cobrar_usd = 0
    for f in facturas.values():
        saldo = float(f.get('saldo_pendiente', 0))
        if saldo > 0:
            total_cobrar_usd += saldo
    tasa_bcv = obtener_tasa_bcv() or 1.0
    total_cobrar_bs = total_cobrar_usd * tasa_bcv
    ultimas_facturas = sorted(facturas.values(), key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'), reverse=True)[:5]
    productos_bajo_stock = [p for p in inventario.values() if int(p.get('cantidad', p.get('stock', 0))) < 10]
    # Calcular pagos recibidos del mes
    total_pagos_recibidos_usd = 0
    total_pagos_recibidos_bs = 0
    for f in facturas.values():
        if 'pagos' in f and f['pagos']:
            for pago in f['pagos']:
                fecha_factura = f.get('fecha', '')
                try:
                    if fecha_factura and datetime.strptime(fecha_factura, '%Y-%m-%d').month == mes_actual:
                        monto = float(pago.get('monto', 0))
                        total_pagos_recibidos_usd += monto
                        total_pagos_recibidos_bs += monto * float(f.get('tasa_bcv', tasa_bcv))
                except Exception:
                    continue
    return {
        'total_clientes': total_clientes,
        'total_productos': total_productos,
        'facturas_mes': facturas_mes,
        'total_cobrar': f"{total_cobrar_usd:,.2f}",
        'total_cobrar_usd': total_cobrar_usd,
        'total_cobrar_bs': total_cobrar_bs,
        'tasa_bcv': tasa_bcv,
        'ultimas_facturas': ultimas_facturas,
        'productos_bajo_stock': productos_bajo_stock,
        'total_pagos_recibidos_usd': total_pagos_recibidos_usd,
        'total_pagos_recibidos_bs': total_pagos_recibidos_bs
    }

def obtener_tasa_bcv():
    """Obtiene la tasa oficial USD/BS del BCV desde la web. Devuelve float o None si falla."""
    url = 'https://www.bcv.org.ve/glosario/cambio-oficial'
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, timeout=10, verify=False)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        # Buscar el valor de la tasa (puede cambiar el selector si la web cambia)
        # Normalmente está en un <strong> dentro de un div con id="dolar"
        tasa = None
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong = dolar_div.find('strong')
            if strong:
                tasa_txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    tasa = float(tasa_txt)
                except:
                    tasa = None
        # Fallback: buscar cualquier número grande en la página
        if not tasa:
            import re
            matches = re.findall(r'(\d{2,}\,\d{2})', resp.text)
            if matches:
                try:
                    tasa = float(matches[0].replace('.', '').replace(',', '.'))
                except:
                    tasa = None
        return tasa
    except Exception as e:
        print(f"Error obteniendo tasa BCV: {e}")
        return None

def cargar_empresa():
    try:
        with open('empresa.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {
            "nombre": "Nombre de la Empresa",
            "rif": "J-000000000",
            "telefono": "0000-0000000",
            "direccion": "Dirección de la empresa"
        }

def limpiar_monto(monto):
    if not monto:
        return 0.0
    return float(str(monto).replace('$', '').replace('Bs', '').replace(',', '').strip())

# --- Inicializar la Aplicación Flask ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'  # Cambia esto por una clave secreta segura
csrf = CSRFProtect(app)

# --- Rutas ---
@app.route('/')
def index():
    """Página principal con dashboard."""
    stats = obtener_estadisticas()
    return render_template('index.html', **stats)

@app.route('/clientes')
def mostrar_clientes():
    """Muestra lista de clientes."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    return render_template('clientes.html', clientes=clientes)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
def nuevo_cliente():
    """Formulario para nuevo cliente."""
    if request.method == 'POST':
        try:
            print("Iniciando proceso de creación de cliente...")
            
            # Cargar clientes existentes
            clientes = cargar_datos(ARCHIVO_CLIENTES)
            if clientes is None:
                print("No se pudieron cargar los clientes existentes, creando nuevo diccionario")
                clientes = {}
            
            # Obtener y validar datos del formulario
            tipo_id = request.form.get('tipo_id', '').strip()
            numero_id = request.form.get('numero_id', '').strip()
            nombre = request.form.get('nombre', '').strip()
            email = request.form.get('email', '').strip()
            telefono_raw = request.form.get('telefono', '').replace(' ', '').replace('-', '')
            codigo_pais = request.form.get('codigo_pais', '+58')
            telefono = f"{codigo_pais}{telefono_raw}"
            direccion = request.form.get('direccion', '').strip()
            
            print(f"Datos recibidos - Tipo ID: {tipo_id}, Número ID: {numero_id}, Nombre: {nombre}")
            
            # Validaciones
            if not tipo_id or not numero_id or not nombre or not telefono or not direccion:
                print("Faltan campos obligatorios")
                flash('Todos los campos obligatorios deben estar completos', 'danger')
                return render_template('cliente_form.html')
            
            # Validar que el número de ID solo contenga dígitos
            if not numero_id.isdigit():
                print(f"Número de ID inválido: {numero_id}")
                flash('El número de identificación debe contener solo dígitos', 'danger')
                return render_template('cliente_form.html')
            
            # Crear ID del cliente
            nuevo_id = f"{tipo_id}-{numero_id}"
            print(f"ID generado para el cliente: {nuevo_id}")
            
            # Verificar si el cliente ya existe
            if nuevo_id in clientes:
                print(f"Cliente con ID {nuevo_id} ya existe")
                flash('Ya existe un cliente con este número de identificación', 'danger')
                return render_template('cliente_form.html')
            
            # Crear objeto cliente
            cliente = {
                'id': nuevo_id,
                'nombre': nombre,
                'email': email,
                'telefono': telefono,
                'direccion': direccion
            }
            
            print(f"Objeto cliente creado: {cliente}")
            
            # Agregar cliente al diccionario
            clientes[nuevo_id] = cliente
            print(f"Cliente agregado al diccionario. Total de clientes: {len(clientes)}")
            
            # Guardar datos
            if guardar_datos(ARCHIVO_CLIENTES, clientes):
                print("Cliente guardado exitosamente")
                flash('Cliente agregado exitosamente', 'success')
                return redirect(url_for('mostrar_clientes'))
            else:
                print("Error al guardar el cliente")
                flash('Error al guardar el cliente. Por favor, intente nuevamente.', 'danger')
                return render_template('cliente_form.html')
                
        except Exception as e:
            print(f"Error inesperado al crear cliente: {str(e)}")
            flash('Error al procesar los datos del cliente. Por favor, intente nuevamente.', 'danger')
            return render_template('cliente_form.html')
    
    return render_template('cliente_form.html')

@app.route('/inventario')
def mostrar_inventario():
    """Muestra lista de inventario."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('inventario.html', inventario=inventario)

@app.route('/inventario/nuevo', methods=['GET', 'POST'])
def nuevo_producto():
    """Formulario para nuevo producto."""
    if request.method == 'POST':
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        nuevo_id = str(len(inventario) + 1)
        
        producto = {
            'nombre': request.form['nombre'],
            'precio': float(request.form['precio']),
            'cantidad': int(request.form['stock']),
            'categoria': request.form['categoria'],
            'ruta_imagen': "",
            'ultima_entrada': None,
            'ultima_salida': None
        }
        
        inventario[nuevo_id] = producto
        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            flash('Producto agregado exitosamente', 'success')
            return redirect(url_for('mostrar_inventario'))
        else:
            flash('Error al guardar el producto', 'danger')
    
    return render_template('producto_form.html')

@app.route('/inventario/<id>/editar', methods=['GET', 'POST'])
def editar_producto(id):
    """Formulario para editar un producto."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    if id not in inventario:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('mostrar_inventario'))
    
    if request.method == 'POST':
        producto = {
            'id': id,  # Agregamos el ID al producto
            'nombre': request.form['nombre'],
            'precio': float(request.form['precio']),
            'cantidad': int(request.form['stock']),
            'categoria': request.form['categoria'],
            'ruta_imagen': inventario[id].get('ruta_imagen', ""),
            'ultima_entrada': inventario[id].get('ultima_entrada'),
            'ultima_salida': inventario[id].get('ultima_salida')
        }
        inventario[id] = producto
        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            flash('Producto actualizado exitosamente', 'success')
            return redirect(url_for('mostrar_inventario'))
        else:
            flash('Error al actualizar el producto', 'danger')
    
    producto = inventario[id]
    producto['id'] = id  # Agregamos el ID al producto antes de pasarlo a la plantilla
    return render_template('producto_form.html', producto=producto)

@app.route('/inventario/<id>/eliminar', methods=['POST'])
def eliminar_producto(id):
    """Elimina un producto."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    if id in inventario:
        del inventario[id]
        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            flash('Producto eliminado exitosamente', 'success')
        else:
            flash('Error al eliminar el producto', 'danger')
    else:
        flash('Producto no encontrado', 'danger')
    return redirect(url_for('mostrar_inventario'))

@app.route('/inventario/<id>')
def ver_producto(id):
    """Muestra los detalles de un producto del inventario."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    producto = inventario.get(id)
    if not producto:
        flash('Producto no encontrado', 'danger')
        return redirect(url_for('mostrar_inventario'))
    return render_template('producto_detalle.html', producto=producto, id=id)

@app.route('/facturas')
def mostrar_facturas():
    """Muestra lista de facturas."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    # Calcular estado automático para cada factura
    for factura in facturas.values():
        total_abonado = 0
        if 'pagos' in factura and factura['pagos']:
            for pago in factura['pagos']:
                try:
                    monto = float(str(pago.get('monto', 0)).replace('$', '').replace(',', ''))
                    total_abonado += monto
                except Exception:
                    continue
        total_factura = factura.get('total_usd') or factura.get('total') or 0
        if isinstance(total_factura, str):
            total_factura = float(total_factura.replace('$', '').replace(',', ''))
        if total_abonado >= total_factura and total_factura > 0:
            factura['estado'] = 'pagada'
        else:
            factura['estado'] = 'pendiente'
        factura['total_abonado'] = total_abonado
        factura['saldo_pendiente'] = max(total_factura - total_abonado, 0)
    return render_template('facturas.html', facturas=facturas, clientes=clientes)

@app.route('/facturas/<id>')
def ver_factura(id):
    """Muestra los detalles de una factura."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    factura = facturas.get(id)
    if not factura:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))
    
    # Calcular totales de pagos
    total_abonado = 0
    if 'pagos' in factura and factura['pagos']:
        for pago in factura['pagos']:
            try:
                monto = float(str(pago.get('monto', 0)).replace('$', '').replace(',', ''))
                total_abonado += monto
            except Exception:
                continue
    factura['total_abonado'] = total_abonado
    factura['saldo_pendiente'] = max(factura.get('total_usd', 0) - total_abonado, 0)
    
    empresa = cargar_empresa()
    return render_template('factura_detalle.html', factura=factura, clientes=clientes, inventario=inventario, empresa=empresa, zip=zip)

@app.route('/facturas/<id>/pdf')
def descargar_factura_pdf(id):
    if pdfkit is None:
        flash('PDFKit no está instalado. Instala con: pip install pdfkit', 'danger')
        return redirect(url_for('ver_factura', id=id))
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    factura = facturas.get(id)
    if not factura:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))
    empresa = cargar_empresa()
    rendered = render_template('factura_imprimir.html', 
                             factura=factura, 
                             clientes=clientes, 
                             inventario=inventario,
                             now=datetime.now,
                             empresa=empresa,
                             zip=zip)
    try:
        config = pdfkit.configuration(wkhtmltopdf='C:\\Program Files\\wkhtmltopdf\\bin\\wkhtmltopdf.exe')
        options = {
            'page-size': 'Letter',
            'margin-top': '0.75in',
            'margin-right': '0.75in',
            'margin-bottom': '0.75in',
            'margin-left': '0.75in',
            'encoding': 'UTF-8',
            'no-outline': None,
            'quiet': '',
            'print-media-type': '',
            'disable-smart-shrinking': '',
            'dpi': 300,
            'image-quality': 100,
            'enable-local-file-access': None,
            'footer-right': '[page] de [topage]',
            'footer-font-size': '8',
            'footer-spacing': '5'
        }
        pdf = pdfkit.from_string(rendered, False, configuration=config, options=options)
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename=factura_{factura["numero"]}.pdf'
        return response
    except Exception as e:
        print(f"Error generando PDF: {str(e)}")
        flash('Error al generar el PDF. Por favor, verifica que wkhtmltopdf esté instalado correctamente.', 'danger')
        return redirect(url_for('ver_factura', id=id))

@app.route('/facturas/<id>/imprimir')
def imprimir_factura(id):
    """Vista amigable para imprimir la factura."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    factura = facturas.get(id)
    if not factura:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))
    empresa = cargar_empresa()
    return render_template('factura_imprimir.html', factura=factura, clientes=clientes, inventario=inventario, now=datetime.now, empresa=empresa, zip=zip)

@app.route('/facturas/<id>/editar', methods=['GET', 'POST'])
def editar_factura(id):
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    if id not in facturas:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))
    if request.method == 'POST':
        factura = facturas[id]
        factura['cliente_id'] = request.form['cliente_id']
        factura['fecha'] = request.form['fecha']
        factura['numero'] = request.form['numero']
        factura['hora'] = request.form.get('hora', '')
        factura['condicion_pago'] = request.form.get('condicion_pago', 'contado')
        factura['fecha_vencimiento'] = request.form.get('fecha_vencimiento', '')
        factura['tasa_bcv'] = request.form.get('tasa_bcv', '')
        factura['productos'] = request.form.getlist('productos[]')
        factura['cantidades'] = request.form.getlist('cantidades[]')
        factura['descuento'] = request.form.get('descuento', '0')
        factura['tipo_descuento'] = request.form.get('tipo_descuento', 'bs')
        factura['iva'] = request.form.get('iva', '16')
        factura['subtotal_usd'] = limpiar_monto(request.form.get('subtotal_usd', ''))
        factura['subtotal_bs'] = limpiar_monto(request.form.get('subtotal_bs', ''))
        factura['descuento_total'] = limpiar_monto(request.form.get('descuento_total', ''))
        factura['iva_total'] = limpiar_monto(request.form.get('iva_total', ''))
        factura['total_usd'] = limpiar_monto(request.form.get('total_usd', ''))
        factura['total_bs'] = limpiar_monto(request.form.get('total_bs', ''))
        
        # Procesar pagos/abonos unificados
        import json
        pagos_json = request.form.get('pagos_json', '[]')
        try:
            pagos = json.loads(pagos_json)
            # Validar y limpiar montos
            for pago in pagos:
                if 'monto' in pago:
                    try:
                        pago['monto'] = float(str(pago['monto']).replace('$', '').replace(',', ''))
                    except Exception:
                        pago['monto'] = 0
            factura['pagos'] = pagos
        except Exception:
            factura['pagos'] = []
        
        # Calcular total abonado y saldo pendiente
        total_abonado = sum(float(p['monto']) for p in factura['pagos'])
        factura['total_abonado'] = total_abonado
        factura['saldo_pendiente'] = max(factura['total_usd'] - total_abonado, 0)
        
        facturas[id] = factura
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Factura actualizada exitosamente', 'success')
            return redirect(url_for('ver_factura', id=id))
        else:
            flash('Error al actualizar la factura', 'danger')
    
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0 or k in facturas[id].get('productos', [])}
    empresa = cargar_empresa()
    return render_template('factura_form.html', factura=facturas[id], clientes=clientes, inventario=inventario_disponible, editar=True, zip=zip, empresa=empresa)

@app.route('/facturas/nueva', methods=['GET', 'POST'])
def nueva_factura():
    if request.method == 'POST':
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        nuevo_id = str(len(facturas) + 1)
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        
        # Validar stock antes de guardar
        for prod_id, cantidad in zip(productos, cantidades):
            cantidad = int(cantidad)
            if prod_id not in inventario or inventario[prod_id]['cantidad'] < cantidad:
                flash(f'No hay suficiente stock para el producto {inventario[prod_id]["nombre"]}', 'danger')
                clientes = cargar_datos(ARCHIVO_CLIENTES)
                inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0}
                empresa = cargar_empresa()
                return render_template('factura_form.html', clientes=clientes, inventario=inventario_disponible, editar=False, empresa=empresa)
        
        # Descontar stock
        for prod_id, cantidad in zip(productos, cantidades):
            inventario[prod_id]['cantidad'] -= int(cantidad)
        guardar_datos(ARCHIVO_INVENTARIO, inventario)
        
        # Procesar pagos/abonos unificados
        import json
        pagos_json = request.form.get('pagos_json', '[]')
        try:
            pagos = json.loads(pagos_json)
            # Validar y limpiar montos
            for pago in pagos:
                if 'monto' in pago:
                    try:
                        pago['monto'] = float(str(pago['monto']).replace('$', '').replace(',', ''))
                    except Exception:
                        pago['monto'] = 0
        except Exception:
            pagos = []
        
        # Crear factura
        factura = {
            'id': nuevo_id,
            'numero': request.form['numero'],
            'fecha': request.form['fecha'],
            'hora': request.form.get('hora', ''),
            'condicion_pago': request.form.get('condicion_pago', 'contado'),
            'fecha_vencimiento': request.form.get('fecha_vencimiento', ''),
            'tasa_bcv': request.form.get('tasa_bcv', ''),
            'cliente_id': request.form['cliente_id'],
            'productos': productos,
            'cantidades': cantidades,
            'descuento': request.form.get('descuento', '0'),
            'tipo_descuento': request.form.get('tipo_descuento', 'bs'),
            'iva': request.form.get('iva', '5'),
            'subtotal_usd': limpiar_monto(request.form.get('subtotal_usd', '')),
            'subtotal_bs': limpiar_monto(request.form.get('subtotal_bs', '')),
            'descuento_total': limpiar_monto(request.form.get('descuento_total', '')),
            'iva_total': limpiar_monto(request.form.get('iva_total', '')),
            'total_usd': limpiar_monto(request.form.get('total_usd', '')),
            'total_bs': limpiar_monto(request.form.get('total_bs', '')),
            'pagos': pagos
        }
        
        # Calcular total abonado y saldo pendiente
        total_abonado = sum(float(p['monto']) for p in pagos)
        factura['total_abonado'] = total_abonado
        factura['saldo_pendiente'] = max(factura['total_usd'] - total_abonado, 0)
        
        facturas[nuevo_id] = factura
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Factura creada exitosamente', 'success')
            return redirect(url_for('mostrar_facturas'))
        else:
            flash('Error al guardar la factura', 'danger')
    
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0}
    empresa = cargar_empresa()
    return render_template('factura_form.html', clientes=clientes, inventario=inventario_disponible, editar=False, empresa=empresa)

@app.route('/facturas/<id>/eliminar', methods=['POST'])
def eliminar_factura(id):
    """Elimina una factura."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    if id in facturas:
        del facturas[id]
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Factura eliminada exitosamente', 'success')
        else:
            flash('Error al eliminar la factura', 'danger')
    else:
        flash('Factura no encontrada', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/cotizaciones')
def mostrar_cotizaciones():
    """Muestra lista de cotizaciones."""
    cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    now = datetime.now().strftime('%Y-%m-%d')
    return render_template('cotizaciones.html', cotizaciones=cotizaciones, clientes=clientes, now=now)

@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
def nueva_cotizacion():
    """Formulario para nueva cotización."""
    if request.method == 'POST':
        cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
        nuevo_id = str(len(cotizaciones) + 1)
        
        # Obtener los productos y cantidades
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        
        # Calcular el total
        total = 0
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        for prod_id, cantidad in zip(productos, cantidades):
            if prod_id in inventario:
                precio = float(inventario[prod_id]['precio'])
                total += precio * int(cantidad)
        
        cotizacion = {
            'id': nuevo_id,
            'numero': request.form['numero'],
            'fecha': request.form['fecha'],
            'cliente_id': request.form['cliente_id'],
            'productos': productos,
            'cantidades': cantidades,
            'total': f"${total:.2f}",
            'validez': request.form['validez']
        }
        
        cotizaciones[nuevo_id] = cotizacion
        if guardar_datos(ARCHIVO_COTIZACIONES, cotizaciones):
            flash('Cotización creada exitosamente', 'success')
            return redirect(url_for('mostrar_cotizaciones'))
        else:
            flash('Error al guardar la cotización', 'danger')
    
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('cotizacion_form.html', clientes=clientes, inventario=inventario)

@app.route('/cotizaciones/<id>/editar', methods=['GET', 'POST'])
def editar_cotizacion(id):
    """Formulario para editar una cotización."""
    cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
    if id not in cotizaciones:
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    
    if request.method == 'POST':
        # Obtener los productos y cantidades
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        
        # Calcular el total
        total = 0
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        for prod_id, cantidad in zip(productos, cantidades):
            if prod_id in inventario:
                precio = float(inventario[prod_id]['precio'])
                total += precio * int(cantidad)
        
        cotizacion = {
            'id': id,
            'numero': request.form['numero'],
            'fecha': request.form['fecha'],
            'cliente_id': request.form['cliente_id'],
            'productos': productos,
            'cantidades': cantidades,
            'total': f"${total:.2f}",
            'validez': request.form['validez']
        }
        
        cotizaciones[id] = cotizacion
        if guardar_datos(ARCHIVO_COTIZACIONES, cotizaciones):
            flash('Cotización actualizada exitosamente', 'success')
            return redirect(url_for('mostrar_cotizaciones'))
        else:
            flash('Error al actualizar la cotización', 'danger')
    
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('cotizacion_form.html', cotizacion=cotizaciones[id], clientes=clientes, inventario=inventario)

@app.route('/cotizaciones/<id>/eliminar', methods=['POST'])
def eliminar_cotizacion(id):
    """Elimina una cotización."""
    cotizaciones = cargar_datos(ARCHIVO_COTIZACIONES)
    if id in cotizaciones:
        del cotizaciones[id]
        if guardar_datos(ARCHIVO_COTIZACIONES, cotizaciones):
            flash('Cotización eliminada exitosamente', 'success')
        else:
            flash('Error al eliminar la cotización', 'danger')
    else:
        flash('Cotización no encontrada', 'danger')
    return redirect(url_for('mostrar_cotizaciones'))

@app.route('/clientes/<path:id>')
def ver_cliente(id):
    """Muestra los detalles de un cliente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    if id in clientes:
        return render_template('cliente_detalle.html', cliente=clientes[id])
    flash('Cliente no encontrado', 'danger')
    return redirect(url_for('mostrar_clientes'))

@app.route('/clientes/<path:id>/editar', methods=['GET', 'POST'])
def editar_cliente(id):
    """Formulario para editar un cliente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    if id not in clientes:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('mostrar_clientes'))
    if request.method == 'POST':
        telefono_raw = request.form.get('telefono', '').replace(' ', '').replace('-', '')
        codigo_pais = request.form.get('codigo_pais', '+58')
        telefono = f"{codigo_pais}{telefono_raw}"
        cliente = {
            'id': id,  # Usar siempre el id de la URL
            'nombre': request.form['nombre'],
            'email': request.form.get('email', ''),
            'telefono': telefono,
            'direccion': request.form['direccion']
        }
        clientes[id] = cliente
        if guardar_datos(ARCHIVO_CLIENTES, clientes):
            flash('Cliente actualizado exitosamente', 'success')
            return redirect(url_for('mostrar_clientes'))
        else:
            flash('Error al actualizar el cliente', 'danger')
    return render_template('cliente_form.html', cliente=clientes[id])

@app.route('/clientes/<path:id>/eliminar', methods=['POST'])
def eliminar_cliente(id):
    """Elimina un cliente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    if id in clientes:
        del clientes[id]
        if guardar_datos(ARCHIVO_CLIENTES, clientes):
            flash('Cliente eliminado exitosamente', 'success')
        else:
            flash('Error al eliminar el cliente', 'danger')
    else:
        flash('Cliente no encontrado', 'danger')
    return redirect(url_for('mostrar_clientes'))

@app.route('/inventario/ajustar-stock', methods=['GET', 'POST'])
def ajustar_stock():
    if request.method == 'POST':
        productos = request.form.getlist('productos[]')
        tipo_ajuste = request.form.get('tipo_ajuste')
        cantidad = int(request.form.get('cantidad'))
        motivo = request.form.get('motivo')
        
        if not productos:
            flash('Debe seleccionar al menos un producto', 'danger')
            return redirect(url_for('ajustar_stock'))
            
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for id_producto in productos:
            if id_producto in inventario:
                producto = inventario[id_producto]
                if tipo_ajuste == 'entrada':
                    producto['cantidad'] += cantidad
                    producto['ultima_entrada'] = fecha_actual
                else:  # salida
                    if producto['cantidad'] >= cantidad:
                        producto['cantidad'] -= cantidad
                        producto['ultima_salida'] = fecha_actual
                    else:
                        flash(f'No hay suficiente stock para {producto["nombre"]}', 'warning')
                        continue

                # Registrar el ajuste en el historial
                if 'historial_ajustes' not in producto:
                    producto['historial_ajustes'] = []

                producto['historial_ajustes'].append({
                    'fecha': fecha_actual,
                    'tipo': tipo_ajuste,
                    'cantidad': cantidad,
                    'motivo': motivo
                })
        guardar_datos(ARCHIVO_INVENTARIO, inventario)
        flash(f'Ajuste de stock realizado para {len(productos)} producto(s)', 'success')
        return redirect(url_for('mostrar_inventario'))
    
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('ajustar_stock.html', inventario=inventario)

@app.route('/inventario/reporte')
def reporte_inventario():
    try:
        inventario = cargar_datos('inventario.json')
        empresa = cargar_datos('empresa.json')
        # Obtener la tasa BCV actual
        tasa_bcv = obtener_tasa_bcv()
        # Obtener la fecha actual
        fecha_actual = datetime.now()
        # Calcular estadísticas
        total_productos = len(inventario)
        total_stock = sum(producto['cantidad'] for producto in inventario.values())
        valor_total = sum(producto['cantidad'] * producto['precio'] for producto in inventario.values())
        # Productos por categoría
        productos_por_categoria = {}
        for producto in inventario.values():
            categoria = producto['categoria']
            if categoria not in productos_por_categoria:
                productos_por_categoria[categoria] = {
                    'productos': [],
                    'cantidad': 0,
                    'valor': 0
                }
            productos_por_categoria[categoria]['productos'].append(producto)
            productos_por_categoria[categoria]['cantidad'] += producto['cantidad']
            productos_por_categoria[categoria]['valor'] += producto['cantidad'] * producto['precio']
        # Productos con bajo stock (menos de 10 unidades)
        productos_bajo_stock = {
            id: producto for id, producto in inventario.items() 
            if producto['cantidad'] < 10
        }
        return render_template('reporte_inventario.html',
                             inventario=inventario,
                             total_productos=total_productos,
                             total_stock=total_stock,
                             valor_total=valor_total,
                             productos_por_categoria=productos_por_categoria,
                             productos_bajo_stock=productos_bajo_stock,
                             empresa=empresa,
                             tasa_bcv=tasa_bcv,
                             fecha_actual=fecha_actual)
    except Exception as e:
        flash(f'Error al generar el reporte: {str(e)}', 'danger')
        return redirect(url_for('mostrar_inventario'))

# --- API Endpoints ---
@app.route('/api/productos')
def api_productos():
    """API endpoint para obtener productos."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return jsonify(inventario)

@app.route('/api/clientes')
def api_clientes():
    """API endpoint para obtener clientes."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    return jsonify(clientes)

@app.route('/api/tasa-bcv')
def api_tasa_bcv():
    """API endpoint para obtener la tasa BCV."""
    tasa = obtener_tasa_bcv()
    if tasa is not None:
        return jsonify({'tasa': tasa})
    return jsonify({'error': 'No se pudo obtener la tasa BCV'}), 500

# --- Manejo de Errores ---
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(e):
    return render_template('500.html'), 500

@app.route('/clientes/reporte')
def reporte_clientes():
    """Genera un reporte general de clientes y sus estadísticas."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    
    # Estadísticas generales
    total_clientes = len(clientes)
    total_facturas = len(facturas)
    total_cobrar = sum(float(cuenta.get('monto', 0)) for cuenta in cuentas.values())
    
    # Productos más comprados
    productos_comprados = {}
    for factura in facturas.values():
        for prod_id, cantidad in zip(factura.get('productos', []), factura.get('cantidades', [])):
            if prod_id in inventario:
                if prod_id not in productos_comprados:
                    productos_comprados[prod_id] = {
                        'nombre': inventario[prod_id]['nombre'],
                        'cantidad': 0,
                        'valor': 0
                    }
                productos_comprados[prod_id]['cantidad'] += int(cantidad)
                productos_comprados[prod_id]['valor'] += int(cantidad) * float(inventario[prod_id]['precio'])
    
    top_productos = sorted(productos_comprados.items(), 
                          key=lambda x: x[1]['cantidad'], 
                          reverse=True)[:10]
    
    # Estadísticas por cliente
    clientes_stats = {}
    for id_cliente, cliente in clientes.items():
        facturas_cliente = [f for f in facturas.values() if f.get('cliente_id') == id_cliente]
        total_compras = sum(
            float(f.get('total', 0).replace('$', '').replace(',', '')) if isinstance(f.get('total', 0), str) else float(f.get('total', 0))
            for f in facturas_cliente
        )
        cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id_cliente), None)
        
        clientes_stats[id_cliente] = {
            'nombre': cliente['nombre'],
            'total_facturas': len(facturas_cliente),
            'total_compras': total_compras,
            'cuenta_por_cobrar': float(cuenta.get('monto', 0)) if cuenta else 0,
            'ultima_compra': max((f.get('fecha') for f in facturas_cliente), default='N/A'),
            'email': cliente.get('email', ''),
            'telefono': cliente.get('telefono', '')
        }
    
    # Top 10 mejores clientes
    top_clientes = sorted(clientes_stats.items(), 
                         key=lambda x: x[1]['total_compras'], 
                         reverse=True)[:10]
    
    # Top 5 peores clientes (con cuentas por cobrar)
    peores_clientes = sorted(
        [(id, stats) for id, stats in clientes_stats.items() if stats['cuenta_por_cobrar'] > 0],
        key=lambda x: x[1]['cuenta_por_cobrar'],
        reverse=True
    )[:5]
    
    return render_template('reporte_clientes.html',
                         total_clientes=total_clientes,
                         total_facturas=total_facturas,
                         total_cobrar=total_cobrar,
                         top_productos=top_productos,
                         top_clientes=top_clientes,
                         peores_clientes=peores_clientes,
                         clientes_stats=clientes_stats)

@app.route('/clientes/<path:id>/historial')
def historial_cliente(id):
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if id not in clientes:
        flash('Cliente no encontrado', 'danger')
        return redirect(url_for('mostrar_clientes'))
    
    cliente = clientes[id]
    now = datetime.now()
    filtro_anio = int(request.args.get('anio', now.year))
    filtro_mes = request.args.get('mes', '')

    # Filtrar facturas por cliente, año y mes
    facturas_cliente = [f for f in facturas.values() if f.get('cliente_id') == id]
    facturas_filtradas = []
    for f in facturas_cliente:
        fecha = f.get('fecha', '')
        try:
            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
        except Exception:
            continue
        if fecha_dt.year == filtro_anio and (not filtro_mes or fecha_dt.month == int(filtro_mes)):
            facturas_filtradas.append(f)
    cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id), None)
    
    # Totales filtrados
    total_compras = sum(
        float(f.get('total_usd', f.get('total', 0)).replace('$', '').replace(',', '')) if isinstance(f.get('total_usd', f.get('total', 0)), str) else float(f.get('total_usd', f.get('total', 0)))
        for f in facturas_filtradas
    )
    total_bs = sum(
        float(f.get('total_bs', 0)) if f.get('total_bs', 0) else (
            float(f.get('total_usd', f.get('total', 0))) * float(f.get('tasa_bcv', 0) or 0)
        )
        for f in facturas_filtradas
    )
    # Productos comprados filtrados
    productos_comprados = {}
    for factura in facturas_filtradas:
        for prod_id, cantidad in zip(factura.get('productos', []), factura.get('cantidades', [])):
            if prod_id in inventario:
                if prod_id not in productos_comprados:
                    productos_comprados[prod_id] = {
                        'nombre': inventario[prod_id]['nombre'],
                        'cantidad': 0,
                        'valor': 0
                    }
                productos_comprados[prod_id]['cantidad'] += int(cantidad)
                productos_comprados[prod_id]['valor'] += int(cantidad) * float(inventario[prod_id]['precio'])
    # Para el formulario de filtro
    anios_disponibles = sorted({datetime.strptime(f.get('fecha', ''), '%Y-%m-%d').year for f in facturas_cliente if f.get('fecha', '')})
    return render_template(
        'historial_cliente.html',
                         cliente=cliente,
        facturas=facturas_filtradas,
                         cuenta=cuenta,
                         total_compras=total_compras,
        total_bs=total_bs,
        productos_comprados=productos_comprados,
        filtro_anio=filtro_anio,
        filtro_mes=filtro_mes,
        anios_disponibles=anios_disponibles,
        now=now
    )

def actualizar_facturas_antiguas():
    """Agrega campos nuevos por defecto a todas las facturas antiguas."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    campos_nuevos = {
        'hora': '',
        'condicion_pago': 'contado',
        'fecha_vencimiento': '',
        'tasa_bcv': '',
        'descuento': '0',
        'tipo_descuento': 'bs',
        'iva': '5',
        'pagos': {},
        'subtotal_usd': '0.00',
        'subtotal_bs': '0.00',
        'descuento_total': '0.00',
        'iva_total': '0.00',
        'total_usd': '0.00',
        'total_bs': '0.00'
    }
    actualizadas = 0
    for id, factura in facturas.items():
        cambiado = False
        for campo, valor in campos_nuevos.items():
            if campo not in factura:
                factura[campo] = valor
                cambiado = True
        if cambiado:
            actualizadas += 1
    if actualizadas > 0:
        guardar_datos(ARCHIVO_FACTURAS, facturas)
    return actualizadas

@app.route('/facturas/actualizar-campos')
def actualizar_campos_facturas():
    n = actualizar_facturas_antiguas()
    flash(f'Se actualizaron {n} facturas antiguas con los campos nuevos.', 'success' if n else 'info')
    return redirect(url_for('mostrar_facturas'))

@app.route('/inventario/cargar-csv', methods=['GET', 'POST'])
def cargar_productos_csv():
    """Formulario para cargar productos desde CSV."""
    if request.method == 'POST':
        if 'archivo' not in request.files:
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        archivo = request.files['archivo']
        if archivo.filename == '':
            flash('No se seleccionó ningún archivo', 'danger')
            return redirect(request.url)
        
        if archivo and allowed_file(archivo.filename):
            try:
                filename = secure_filename(archivo.filename)
                ruta_archivo = os.path.join(UPLOAD_FOLDER, filename)
                archivo.save(ruta_archivo)
                
                if cargar_productos_desde_csv(ruta_archivo):
                    flash('Productos cargados exitosamente', 'success')
                else:
                    flash('Error al cargar los productos', 'danger')
                
                # Limpiar archivo después de procesarlo
                try:
                    os.remove(ruta_archivo)
                except:
                    pass
                    
                return redirect(url_for('mostrar_inventario'))
            except Exception as e:
                flash(f'Error al procesar el archivo: {str(e)}', 'danger')
                return redirect(request.url)
        
        flash('Tipo de archivo no permitido', 'danger')
        return redirect(request.url)
    
    return render_template('cargar_csv.html', tipo='productos')

@app.route('/inventario/eliminar-multiples', methods=['POST'])
def eliminar_productos_multiples():
    try:
        productos = json.loads(request.form.get('productos', '[]'))
        if not productos:
            flash('No se seleccionaron productos para eliminar', 'warning')
            return redirect(url_for('mostrar_inventario'))
        
        inventario = cargar_datos('inventario.json')
        eliminados = 0
        
        for id in productos:
            if id in inventario:
                del inventario[id]
                eliminados += 1
        
        if guardar_datos('inventario.json', inventario):
            flash(f'Se eliminaron {eliminados} productos exitosamente', 'success')
        else:
            flash('Error al guardar los cambios', 'danger')
            
    except Exception as e:
        flash(f'Error al eliminar los productos: {str(e)}', 'danger')
    
    return redirect(url_for('mostrar_inventario'))

# --- Filtro personalizado para fechas legibles ---
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d/%m/%Y %H:%M:%S'):
    """Convierte una cadena de fecha a formato legible."""
    if not value:
        return ''
    try:
        # Intentar parsear formato ISO
        if 'T' in value:
            value = value.split('.')[0].replace('T', ' ')
        dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
        return dt.strftime(format)
    except Exception:
        return value  # Si falla, mostrar la cadena original

# --- Filtro personalizado para números en formato español ---
@app.template_filter('es_number')
def es_number(value, decimales=2):
    """Convierte un número a formato español (punto para miles, coma para decimales)."""
    try:
        # Si es None o string vacío, retornar 0
        if value is None or value == '':
            return f"0,{decimales * '0'}"
            
        # Convertir a float
        value = float(value)
        
        # Si es 0, retornar formato con decimales
        if value == 0:
            return f"0,{decimales * '0'}"
            
        # Formatear con separadores de miles y decimales
        formatted = f"{abs(value):,.{decimales}f}"
        
        # Reemplazar comas y puntos para formato español
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Agregar signo negativo si corresponde
        if value < 0:
            formatted = f"-{formatted}"
            
        return formatted
    except Exception:
        return str(value) if value is not None else "0"

@app.route('/cuentas-por-cobrar')
def reporte_cuentas_por_cobrar():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    filtro = request.args.get('estado', 'por_cobrar')
    cuentas_filtradas = {}
    total_por_cobrar_usd = 0
    total_por_cobrar_bs = 0
    tasa_bcv = obtener_tasa_bcv() or 1.0
    clientes_deudores = set()
    for id, factura in facturas.items():
        saldo_pendiente = float(factura.get('saldo_pendiente', 0))
        estado = 'por_cobrar'
        if factura.get('estado', '').lower() == 'pagada' or saldo_pendiente <= 0:
            estado = 'cobrado'
        elif factura.get('condicion_pago', '') == 'credito' or saldo_pendiente > 0:
            estado = 'por_cobrar'
        if filtro == 'todas' or \
           (filtro == 'por_cobrar' and estado == 'por_cobrar') or \
           (filtro == 'cobrado' and estado == 'cobrado'):
            cuentas_filtradas[id] = {
                'factura_id': id,
                'numero': factura.get('numero', id),
                'cliente_id': factura.get('cliente_id'),
                'cliente_nombre': clientes.get(factura.get('cliente_id'), {}).get('nombre', factura.get('cliente_id')),
                'total_usd': float(factura.get('total_usd', 0)),
                'abonado_usd': float(factura.get('total_abonado', 0)),
                'saldo_pendiente': saldo_pendiente,
                'estado': estado,
                'fecha': factura.get('fecha'),
                'condicion_pago': factura.get('condicion_pago', ''),
            }
            if estado == 'por_cobrar' and saldo_pendiente > 0:
                total_por_cobrar_usd += saldo_pendiente
                clientes_deudores.add(factura.get('cliente_id'))
    total_por_cobrar_bs = total_por_cobrar_usd * tasa_bcv
    cantidad_facturas = len([c for c in cuentas_filtradas.values() if c['estado'] == 'por_cobrar'])
    cantidad_clientes = len(clientes_deudores)
    promedio_por_factura = total_por_cobrar_usd / cantidad_facturas if cantidad_facturas > 0 else 0
    # Top 5 deudores
    deudores = {}
    for c in cuentas_filtradas.values():
        if c['estado'] == 'por_cobrar' and c['saldo_pendiente'] > 0:
            cid = c['cliente_id']
            deudores[cid] = deudores.get(cid, 0) + c['saldo_pendiente']
    top_deudores = sorted(deudores.items(), key=lambda x: x[1], reverse=True)[:5]
    top_deudores = [
        {'cliente': clientes.get(cid, {}).get('nombre', cid), 'monto': monto}
        for cid, monto in top_deudores
    ]
    return render_template('reporte_cuentas_por_cobrar.html',
        cuentas=cuentas_filtradas,
        clientes=clientes,
        filtro=filtro,
        total_por_cobrar_usd=total_por_cobrar_usd,
        total_por_cobrar_bs=total_por_cobrar_bs,
        tasa_bcv=tasa_bcv,
        cantidad_facturas=cantidad_facturas,
        cantidad_clientes=cantidad_clientes,
        promedio_por_factura=promedio_por_factura,
        top_deudores=top_deudores
    )

@app.route('/pagos-recibidos')
def pagos_recibidos():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    pagos = []
    total_usd = 0
    total_bs = 0
    tasa_bcv = obtener_tasa_bcv() or 1.0
    for f in facturas.values():
        if 'pagos' in f and f['pagos']:
            for pago in f['pagos']:
                pagos.append({
                    'factura_id': f.get('id'),
                    'fecha': f.get('fecha'),
                    'cliente_id': f.get('cliente_id'),
                    'monto': pago.get('monto', 0),
                    'metodo': pago.get('metodo', ''),
                    'tasa_bcv': float(f.get('tasa_bcv', tasa_bcv)),
                })
                total_usd += float(pago.get('monto', 0))
                total_bs += float(pago.get('monto', 0)) * float(f.get('tasa_bcv', tasa_bcv))
    return render_template('pagos_recibidos.html', pagos=pagos, clientes=clientes, total_usd=total_usd, total_bs=total_bs, tasa_bcv=tasa_bcv)

@app.template_filter('split')
def split_filter(value, delimiter=' '):
    """Filtro personalizado para dividir strings"""
    return value.split(delimiter)

@app.route('/reporte/facturas')
def reporte_facturas():
    """Muestra un reporte general de facturas con filtros y estadísticas"""
    # Cargar datos necesarios
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    # Obtener parámetros de filtro
    filtro_anio = request.args.get('anio', '')
    filtro_mes = request.args.get('mes', '')
    filtro_cliente = request.args.get('cliente', '')
    
    # Filtrar facturas
    facturas_filtradas = []
    for factura in facturas.values():
        fecha = factura['fecha'].split('-')
        anio_factura = fecha[0]
        mes_factura = fecha[1]
        
        # Aplicar filtros
        if filtro_anio and anio_factura != filtro_anio:
            continue
        if filtro_mes and mes_factura != filtro_mes.zfill(2):
            continue
        if filtro_cliente and str(factura['cliente_id']) != filtro_cliente:
            continue
        facturas_filtradas.append(factura)
    
    # Calcular totales
    total_usd = sum(float(f.get('total_usd', 0)) for f in facturas_filtradas)
    total_bs = sum(float(f.get('total_bs', 0)) for f in facturas_filtradas)
    
    # Calcular top clientes
    clientes_totales = {}
    for factura in facturas_filtradas:
        cliente_id = factura['cliente_id']
        if cliente_id not in clientes_totales:
            clientes_totales[cliente_id] = 0
        clientes_totales[cliente_id] += float(factura.get('total_usd', 0))
    
    top_clientes = [
        {'nombre': clientes[cid]['nombre'], 'total': total}
        for cid, total in sorted(clientes_totales.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    # Calcular top productos
    productos_totales = {}
    productos_cantidades = {}
    for factura in facturas_filtradas:
        # Compatibilidad: puede ser 'items' o ('productos' y 'cantidades')
        if 'items' in factura:
            for item in factura['items']:
                pid = item['producto_id']
                if pid not in productos_totales:
                    productos_totales[pid] = 0
                    productos_cantidades[pid] = 0
                productos_totales[pid] += float(item.get('subtotal', 0))
                productos_cantidades[pid] += int(item.get('cantidad', 0))
        else:
            for prod_id, cantidad in zip(factura.get('productos', []), factura.get('cantidades', [])):
                if prod_id not in productos_totales:
                    productos_totales[prod_id] = 0
                    productos_cantidades[prod_id] = 0
                precio = float(inventario.get(prod_id, {}).get('precio', 0))
                productos_totales[prod_id] += precio * int(cantidad)
                productos_cantidades[prod_id] += int(cantidad)
    
    top_productos = [
        {
            'nombre': inventario[pid]['nombre'] if pid in inventario else pid,
            'cantidad': productos_cantidades[pid],
            'total': total
        }
        for pid, total in sorted(productos_totales.items(), key=lambda x: x[1], reverse=True)[:5]
    ]
    
    return render_template('reporte_facturas.html',
                         facturas=facturas_filtradas,
                         clientes=clientes,
                         total_usd=total_usd,
                         total_bs=total_bs,
                         top_clientes=top_clientes,
                         top_productos=top_productos,
                         filtro_anio=filtro_anio,
                         filtro_mes=filtro_mes,
                         filtro_cliente=filtro_cliente)

@app.route('/inventario/')
def inventario_slash_redirect():
    return redirect(url_for('mostrar_inventario'))

# --- Bloque para Ejecutar la Aplicación ---
if __name__ == '__main__':
    app.run(debug=True)