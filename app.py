# -*- coding: utf-8 -*-
import json
import os
import urllib3
import requests
import csv
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, make_response, send_file, session
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from auth import login_required, admin_required, verify_password
try:
    import pdfkit
except ImportError:
    pdfkit = None
from functools import wraps
import re
import uuid
from uuid import uuid4

# --- Inicializar la Aplicación Flask ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'tu_clave_secreta_aqui'  # Cambia esto por una clave secreta segura
csrf = CSRFProtect(app)

# --- Constantes ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ARCHIVO_CLIENTES = 'clientes.json'
ARCHIVO_INVENTARIO = 'inventario.json'
ARCHIVO_FACTURAS = 'facturas_json/facturas.json'
ARCHIVO_COTIZACIONES = 'cotizaciones_json/cotizaciones.json'
ARCHIVO_CUENTAS = 'cuentas_por_cobrar.json'
ULTIMA_TASA_BCV_FILE = 'ultima_tasa_bcv.json'
ALLOWED_EXTENSIONS = {'csv'}
BITACORA_FILE = 'bitacora.log'

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
    mes_actual = datetime.now().month
    total_clientes = len(clientes)
    total_productos = len(inventario)
    facturas_mes = sum(1 for f in facturas.values() if datetime.strptime(f['fecha'], '%Y-%m-%d').month == mes_actual)
    total_cobrar_usd = 0
    for f in facturas.values():
        saldo = float(f.get('saldo_pendiente', 0))
        if saldo > 0:
            total_cobrar_usd += saldo
    # Asegura que tasa_bcv sea float y no Response
    tasa_bcv = obtener_tasa_bcv()
    if hasattr(tasa_bcv, 'json'):
        # Si es un Response, extrae el valor
        try:
            tasa_bcv = tasa_bcv.json.get('tasa', 1.0)
        except Exception:
            tasa_bcv = 1.0
    try:
        tasa_bcv = float(tasa_bcv)
    except Exception:
        tasa_bcv = 1.0
    total_cobrar_bs = total_cobrar_usd * tasa_bcv
    ultimas_facturas = sorted(facturas.values(), key=lambda x: datetime.strptime(x['fecha'], '%Y-%m-%d'), reverse=True)[:5]
    productos_bajo_stock = [p for p in inventario.values() if int(p.get('cantidad', p.get('stock', 0))) < 10]
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

def limpiar_valor_monetario(valor):
    """Limpia y convierte un valor monetario a float."""
    if valor is None:
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)
    try:
        # Eliminar símbolos y espacios
        valor = str(valor).replace('$', '').replace(',', '').replace('Bs', '').strip()
        # Reemplazar coma decimal por punto si existe
        if ',' in valor:
            valor = valor.replace(',', '.')
        return float(valor)
    except (ValueError, TypeError):
        return 0.0

def guardar_ultima_tasa_bcv(tasa):
    try:
        with open(ULTIMA_TASA_BCV_FILE, 'w', encoding='utf-8') as f:
            json.dump({'tasa': tasa}, f)
        # Registrar en bitácora
        usuario = session['usuario'] if 'usuario' in session else 'sistema'
        registrar_bitacora(usuario, 'Actualizar tasa BCV', f'Tasa: {tasa}')
    except Exception as e:
        print(f"Error guardando última tasa BCV: {e}")

def cargar_ultima_tasa_bcv():
    try:
        with open(ULTIMA_TASA_BCV_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            tasa = float(data.get('tasa', 0))
            if tasa > 10:
                return tasa
            else:
                return None
    except Exception:
        return None

def obtener_tasa_bcv():
    try:
        with open('ultima_tasa_bcv.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            return float(data.get('tasa', 0))
    except Exception:
        return 0

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

def registrar_bitacora(usuario, accion, detalles=''):
    from datetime import datetime
    import requests
    from flask import has_request_context, request, session
    ip = ''
    ubicacion = ''
    lat = ''
    lon = ''
    if has_request_context():
        ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if ip == '127.0.0.1':
            ip = '190.202.123.123'  # IP pública de Venezuela para pruebas
    # Usar ubicación precisa si está en session
    if 'ubicacion_precisa' in session:
        lat = session['ubicacion_precisa'].get('lat', '')
        lon = session['ubicacion_precisa'].get('lon', '')
        ubicacion = session['ubicacion_precisa'].get('texto', '')
    elif has_request_context():
        try:
            resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                if data.get('status') == 'success':
                    lat = data.get('lat', '')
                    lon = data.get('lon', '')
                    ubicacion = ', '.join([v for v in [data.get('city', ''), data.get('regionName', ''), data.get('country', '')] if v])
                else:
                    ubicacion = f"API sin datos: {data}"
            else:
                ubicacion = f"API status: {resp.status_code}"
        except Exception as e:
            ubicacion = f"Error API: {e}"
    linea = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Usuario: {usuario} | Acción: {accion} | Detalles: {detalles} | IP: {ip} | Ubicación: {ubicacion} | Coordenadas: {lat},{lon}\n"
    with open(BITACORA_FILE, 'a', encoding='utf-8') as f:
        f.write(linea)

# Decorador para requerir login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Rutas protegidas ---
@app.route('/')
@login_required
def index():
    stats = obtener_estadisticas()
    try:
        tasa_bcv = float(stats.get('tasa_bcv', 0))
    except Exception:
        tasa_bcv = 0
    advertencia_tasa = None
    if not tasa_bcv or tasa_bcv < 1:
        advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
    stats['tasa_bcv'] = tasa_bcv
    return render_template('index.html', **stats, advertencia_tasa=advertencia_tasa)

@app.route('/clientes')
@login_required
def mostrar_clientes():
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    # Filtros
    q = request.args.get('q', '').strip().lower()
    filtro_orden = request.args.get('orden', 'nombre')
    if q:
        clientes = {k: v for k, v in clientes.items() if q in v.get('nombre', '').lower() or q in k.lower()}
    if filtro_orden == 'nombre':
        clientes = dict(sorted(clientes.items(), key=lambda item: item[1].get('nombre', '').lower()))
    elif filtro_orden == 'rif':
        clientes = dict(sorted(clientes.items(), key=lambda item: item[0].lower()))
    # Calcular totales por cliente
    clientes_totales = {}
    for id_cliente, cliente in clientes.items():
        # Total facturado
        facturas_cliente = [f for f in facturas.values() if f.get('cliente_id') == id_cliente]
        total_facturado = sum(float(f.get('total_usd', 0)) for f in facturas_cliente)
        total_abonado = sum(float(f.get('total_abonado', 0)) for f in facturas_cliente)
        # Total por cobrar (de cuentas por cobrar)
        cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id_cliente), None)
        total_por_cobrar = float(cuenta.get('saldo_pendiente', 0)) if cuenta else 0
        clientes_totales[id_cliente] = {
            'total_facturado': total_facturado,
            'total_abonado': total_abonado,
            'total_por_cobrar': total_por_cobrar
        }
    return render_template('clientes.html', clientes=clientes, q=q, filtro_orden=filtro_orden, clientes_totales=clientes_totales)

@app.route('/clientes/nuevo', methods=['GET', 'POST'])
@login_required
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
                registrar_bitacora(session['usuario'], 'Nuevo cliente', f"Nombre: {request.form.get('nombre','')}")
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
@login_required
def mostrar_inventario():
    """Muestra lista de inventario con filtros y orden."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    # Filtros y orden
    q = request.args.get('q', '').strip().lower()
    filtro_categoria = request.args.get('categoria', '').strip().lower()
    filtro_orden = request.args.get('orden', 'nombre')
    # Filtrar por búsqueda
    if q:
        inventario = {k: v for k, v in inventario.items() if q in v.get('nombre', '').lower()}
    # Filtrar por categoría
    if filtro_categoria:
        inventario = {k: v for k, v in inventario.items() if filtro_categoria in v.get('categoria', '').lower()}
    # Ordenar
    if filtro_orden == 'nombre':
        inventario = dict(sorted(inventario.items(), key=lambda item: item[1].get('nombre', '').lower()))
    elif filtro_orden == 'stock':
        inventario = dict(sorted(inventario.items(), key=lambda item: int(item[1].get('cantidad', 0)), reverse=True))
    # Lista de categorías únicas para el select
    categorias = sorted(set(v.get('categoria', '') for v in cargar_datos(ARCHIVO_INVENTARIO).values() if v.get('categoria', '')))
    return render_template('inventario.html', inventario=inventario, q=q, filtro_categoria=filtro_categoria, filtro_orden=filtro_orden, categorias=categorias)

@app.route('/inventario/nuevo', methods=['GET', 'POST'])
@login_required
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
            registrar_bitacora(session['usuario'], 'Nuevo producto', f"Nombre: {request.form.get('nombre','')}")
            return redirect(url_for('mostrar_inventario'))
        else:
            flash('Error al guardar el producto', 'danger')
    
    return render_template('producto_form.html')

@app.route('/inventario/<id>/editar', methods=['GET', 'POST'])
@login_required
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
            registrar_bitacora(session['usuario'], 'Editar producto', f"ID: {id}, Nombre: {request.form.get('nombre','')}")
            return redirect(url_for('mostrar_inventario'))
        else:
            flash('Error al actualizar el producto', 'danger')
    
    producto = inventario[id]
    producto['id'] = id  # Agregamos el ID al producto antes de pasarlo a la plantilla
    return render_template('producto_form.html', producto=producto)

@app.route('/inventario/<id>/eliminar', methods=['POST'])
@login_required
def eliminar_producto(id):
    """Elimina un producto."""
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    if id in inventario:
        del inventario[id]
        if guardar_datos(ARCHIVO_INVENTARIO, inventario):
            flash('Producto eliminado exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Eliminar producto', f"ID: {id}")
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
@login_required
def mostrar_facturas():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    actualizadas = 0
    for id, factura in facturas.items():
        try:
            precios = factura.get('precios', [])
            cantidades = factura.get('cantidades', [])
            subtotal_usd = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios))) if precios and cantidades else 0
            tasa_bcv = float(factura.get('tasa_bcv', 1))
            descuento_total = float(factura.get('descuento_total', 0))
            iva_total = float(factura.get('iva_total', 0))
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            pagos = factura.get('pagos', [])
            total_abonado = sum(float(p.get('monto', 0)) for p in pagos)
            saldo_pendiente = max(total_usd - total_abonado, 0)
            factura['subtotal_usd'] = subtotal_usd
            factura['subtotal_bs'] = subtotal_bs
            factura['total_usd'] = total_usd
            factura['total_bs'] = total_bs
            factura['total_abonado'] = total_abonado
            factura['saldo_pendiente'] = saldo_pendiente
            facturas[id] = factura
            actualizadas += 1
        except Exception as e:
            print(f"Error actualizando factura {id}: {e}")
    guardar_datos(ARCHIVO_FACTURAS, facturas)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    tasa_bcv = obtener_tasa_bcv()
    return render_template('facturas.html', facturas=facturas, clientes=clientes, tasa_bcv=tasa_bcv)

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
@login_required
def editar_factura(id):
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    
    if id not in facturas:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))
    
    if request.method == 'POST':
        try:
            factura = facturas[id]
            # Obtener y validar datos básicos
            factura['cliente_id'] = request.form['cliente_id']
            factura['fecha'] = request.form['fecha']
            factura['numero'] = request.form['numero']
            factura['hora'] = request.form.get('hora', '')
            factura['condicion_pago'] = request.form.get('condicion_pago', 'contado')
            factura['dias_credito'] = request.form.get('dias_credito', '30')
            factura['fecha_vencimiento'] = request.form.get('fecha_vencimiento', '') if request.form.get('condicion_pago') == 'credito' else ''
            # Obtener productos, cantidades y precios
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            precios = [float(p) for p in precios]
            factura['productos'] = productos
            factura['cantidades'] = cantidades
            factura['precios'] = precios
            # Obtener y validar tasa BCV
            tasa_bcv = limpiar_valor_monetario(request.form.get('tasa_bcv', '36.00'))
            if tasa_bcv <= 0:
                tasa_bcv = 36.00
            factura['tasa_bcv'] = tasa_bcv
            # Calcular subtotales y totales
            subtotal_usd = sum(precios[i] * int(cantidades[i]) for i in range(len(precios)))
            subtotal_bs = subtotal_usd * tasa_bcv
            descuento = limpiar_valor_monetario(request.form.get('descuento', '0'))
            tipo_descuento = request.form.get('tipo_descuento', 'bs')
            if tipo_descuento == 'porc':
                descuento_total = subtotal_usd * (descuento / 100)
            else:
                descuento_total = descuento / tasa_bcv
            iva = limpiar_valor_monetario(request.form.get('iva', '0'))
            iva_total = (subtotal_usd - descuento_total) * (iva / 100)
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            factura['descuento'] = descuento
            factura['tipo_descuento'] = tipo_descuento
            factura['iva'] = iva
            factura['subtotal_usd'] = subtotal_usd
            factura['subtotal_bs'] = subtotal_bs
            factura['descuento_total'] = descuento_total
            factura['iva_total'] = iva_total
            factura['total_usd'] = total_usd
            factura['total_bs'] = total_bs
            # Procesar pagos
            pagos_json = request.form.get('pagos_json', '[]')
            try:
                pagos = json.loads(pagos_json)
                for pago in pagos:
                    if 'monto' in pago:
                        pago['monto'] = limpiar_valor_monetario(pago['monto'])
                factura['pagos'] = pagos
            except Exception:
                factura['pagos'] = []
            # Calcular total abonado y saldo pendiente
            total_abonado = sum(float(p['monto']) for p in factura['pagos'])
            factura['total_abonado'] = total_abonado
            factura['saldo_pendiente'] = max(total_usd - total_abonado, 0)
            # Actualizar estado
            if total_abonado >= total_usd and total_usd > 0:
                factura['estado'] = 'pagada'
            else:
                factura['estado'] = 'pendiente'
            facturas[id] = factura
            if guardar_datos(ARCHIVO_FACTURAS, facturas):
                flash('Factura actualizada exitosamente', 'success')
                registrar_bitacora(session['usuario'], 'Editar factura', f"ID: {id}")
                return redirect(url_for('ver_factura', id=id))
            else:
                flash('Error al actualizar la factura', 'danger')
        except Exception as e:
            flash(f'Error al actualizar la factura: {str(e)}', 'danger')
    
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0 or k in facturas[id].get('productos', [])}
    empresa = cargar_empresa()
    return render_template('factura_form.html', factura=facturas[id], clientes=clientes, inventario=inventario_disponible, editar=True, zip=zip, empresa=empresa)

@app.route('/facturas/nueva', methods=['GET', 'POST'])
@login_required
def nueva_factura():
    if request.method == 'POST':
        try:
            # Obtener y validar datos básicos
            cliente_id = request.form['cliente_id']
            fecha = request.form['fecha']
            numero = request.form['numero']
            hora = request.form.get('hora', '')
            condicion_pago = request.form.get('condicion_pago', 'contado')
            dias_credito = request.form.get('dias_credito', '30')
            fecha_vencimiento = request.form.get('fecha_vencimiento', '')
            
            # Obtener productos, cantidades y precios
            productos = request.form.getlist('productos[]')
            cantidades = request.form.getlist('cantidades[]')
            precios = request.form.getlist('precios[]')
            precios = [float(p) for p in precios]
            
            # Obtener y validar tasa BCV
            tasa_bcv = limpiar_valor_monetario(request.form.get('tasa_bcv', '36.00'))
            if tasa_bcv <= 0:
                tasa_bcv = 36.00
            
            # Calcular subtotales y totales
            subtotal_usd = sum(precios[i] * int(cantidades[i]) for i in range(len(precios)))
            subtotal_bs = subtotal_usd * tasa_bcv
            descuento = limpiar_valor_monetario(request.form.get('descuento', '0'))
            tipo_descuento = request.form.get('tipo_descuento', 'bs')
            if tipo_descuento == 'porc':
                descuento_total = subtotal_usd * (descuento / 100)
            else:
                descuento_total = descuento / tasa_bcv
            iva = limpiar_valor_monetario(request.form.get('iva', '0'))
            iva_total = (subtotal_usd - descuento_total) * (iva / 100)
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            
            # Procesar pagos
            pagos_json = request.form.get('pagos_json', '[]')
            try:
                pagos = json.loads(pagos_json)
                for pago in pagos:
                    if 'monto' in pago:
                        pago['monto'] = limpiar_valor_monetario(pago['monto'])
            except Exception:
                pagos = []
            
            # Crear nueva factura
            factura = {
                'id': str(uuid.uuid4()),
                'numero': numero,
                'fecha': fecha,
                'hora': hora,
                'cliente_id': cliente_id,
                'condicion_pago': condicion_pago,
                'dias_credito': dias_credito,
                'fecha_vencimiento': fecha_vencimiento if condicion_pago == 'credito' else '',
                'tasa_bcv': tasa_bcv,
                'estado': 'pendiente',
                'productos': productos,
                'cantidades': cantidades,
                'precios': precios,
                'descuento': descuento,
                'tipo_descuento': tipo_descuento,
                'iva': iva,
                'subtotal_usd': subtotal_usd,
                'subtotal_bs': subtotal_bs,
                'descuento_total': descuento_total,
                'iva_total': iva_total,
                'total_usd': total_usd,
                'total_bs': total_bs,
                'pagos': pagos
            }
            # Calcular total abonado y saldo pendiente
            total_abonado = sum(float(p['monto']) for p in pagos)
            factura['total_abonado'] = total_abonado
            factura['saldo_pendiente'] = max(total_usd - total_abonado, 0)
            
            facturas = cargar_datos(ARCHIVO_FACTURAS)
            inventario = cargar_datos(ARCHIVO_INVENTARIO)
            # Validar stock
            for prod_id, cantidad in zip(productos, cantidades):
                if prod_id in inventario:
                    if int(cantidad) > int(inventario[prod_id]['cantidad']):
                        flash(f'No hay suficiente stock para {inventario[prod_id]["nombre"]}', 'danger')
                        return redirect(url_for('nueva_factura'))
            # Descontar stock
            for prod_id, cantidad in zip(productos, cantidades):
                inventario[prod_id]['cantidad'] -= int(cantidad)
            if not guardar_datos(ARCHIVO_INVENTARIO, inventario):
                flash('Error al actualizar el inventario', 'danger')
                return redirect(url_for('nueva_factura'))
            # Guardar factura
            facturas[factura['id']] = factura
            if guardar_datos(ARCHIVO_FACTURAS, facturas):
                flash('Factura creada exitosamente', 'success')
                registrar_bitacora(session['usuario'], 'Nueva factura', f"Número: {numero}, Cliente: {cliente_id}")
                return redirect(url_for('mostrar_facturas'))
            else:
                flash('Error al guardar la factura', 'danger')
                return redirect(url_for('nueva_factura'))
        except Exception as e:
            flash(f'Error al crear la factura: {str(e)}', 'danger')
            return redirect(url_for('nueva_factura'))
    
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0}
    empresa = cargar_empresa()
    return render_template('factura_form.html', clientes=clientes, inventario=inventario_disponible, editar=False, empresa=empresa, factura=None)

@app.route('/facturas/<id>/eliminar', methods=['POST'])
@login_required
def eliminar_factura(id):
    """Elimina una factura."""
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    if id in facturas:
        del facturas[id]
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Factura eliminada exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Eliminar factura', f"ID: {id}")
        else:
            flash('Error al eliminar la factura', 'danger')
    else:
        flash('Factura no encontrada', 'danger')
    return redirect(url_for('mostrar_facturas'))

@app.route('/cotizaciones')
@login_required
def mostrar_cotizaciones():
    """Muestra lista de cotizaciones válidas."""
    try:
        cotizaciones = {}
        cotizaciones_dir = 'cotizaciones_json'
        
        # Asegurar que el directorio existe
        if not os.path.exists(cotizaciones_dir):
            os.makedirs(cotizaciones_dir)
            return render_template('cotizaciones.html', cotizaciones={}, clientes={}, now=datetime.now().strftime('%Y-%m-%d'))
        
        # Leer todos los archivos JSON de cotizaciones
        for filename in os.listdir(cotizaciones_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(cotizaciones_dir, filename), 'r', encoding='utf-8') as f:
                        cot_data = json.load(f)
                        
                        # Extraer el ID del nombre del archivo
                        cot_id = filename.split('_')[1].split('.')[0]
                        
                        # Procesar la fecha y hora
                        fecha = cot_data.get('fecha', '')
                        hora = cot_data.get('hora', '--:--')  # Usar '--:--' si no existe
                        
                        # Calcular validez
                        validez_dias = int(cot_data.get('validez_dias', 30))
                        try:
                            fecha_dt = datetime.strptime(fecha, '%Y-%m-%d')
                            validez = (fecha_dt + timedelta(days=validez_dias)).strftime('%Y-%m-%d')
                        except:
                            fecha_dt = datetime.now()
                            validez = (fecha_dt + timedelta(days=validez_dias)).strftime('%Y-%m-%d')
                        
                        # Procesar el cliente
                        cliente = cot_data.get('cliente', {})
                        cliente_nombre = cliente.get('nombre', 'Cliente no especificado')
                        
                        # Procesar el total
                        total = f"${float(cot_data.get('total_usd', 0)):.2f}" if isinstance(cot_data.get('total_usd', 0), (int, float)) else cot_data.get('total_usd', '$0.00')
                        
                        # Crear el diccionario de la cotización
                        cotizaciones[cot_id] = {
                            'numero': cot_data.get('numero_cotizacion', cot_id),
                            'fecha': fecha,
                            'hora': hora,
                            'cliente_id': cliente_nombre,
                            'total': total,
                            'validez': validez
                        }
                except Exception as e:
                    print(f"Error procesando archivo {filename}: {str(e)}")
                    continue
        
        # Cargar clientes para el template
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        now = datetime.now().strftime('%Y-%m-%d')
        
        return render_template('cotizaciones.html', 
                             cotizaciones=cotizaciones, 
                             clientes=clientes, 
                             now=now)
                              
    except Exception as e:
        print(f"Error al cargar las cotizaciones: {str(e)}")
        flash('Error al cargar las cotizaciones. Por favor, intente nuevamente.', 'danger')
        return redirect(url_for('index'))

@app.route('/cotizaciones/nueva', methods=['GET', 'POST'])
@login_required
def nueva_cotizacion():
    """Formulario para nueva cotización."""
    if request.method == 'POST':
        cotizaciones_dir = 'cotizaciones_json'
        os.makedirs(cotizaciones_dir, exist_ok=True)
        # Obtener el número de cotización del formulario (obligatorio)
        numero_cotizacion = request.form.get('numero_cotizacion', '').strip()
        if not numero_cotizacion:
            flash('Debe ingresar el número de cotización.', 'danger')
            return redirect(url_for('nueva_cotizacion'))
        # Obtener datos del formulario
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        precios = request.form.getlist('precios[]')
        subtotal_usd = request.form.get('subtotal_usd', '0')
        subtotal_bs = request.form.get('subtotal_bs', '0')
        descuento = request.form.get('descuento', '0')
        tipo_descuento = request.form.get('tipo_descuento', 'bs')
        descuento_total = request.form.get('descuento_total', '0')
        iva = request.form.get('iva', '0')
        iva_total = request.form.get('iva_total', '0')
        total_usd = request.form.get('total_usd', '0')
        total_bs = request.form.get('total_bs', '0')
        tasa_bcv = request.form.get('tasa_bcv', '0')
        validez = request.form.get('validez', '3')
        cliente_id = request.form.get('cliente_id')
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        cliente = clientes.get(cliente_id, {})
        fecha = request.form['fecha']
        hora = request.form.get('hora')
        if not hora:
            hora = datetime.now().strftime('%H:%M')
        # Calcular subtotal_usd
        subtotal_usd = 0
        for precio, cantidad in zip(precios, cantidades):
            try:
                p = float(precio)
                c = int(cantidad)
                subtotal_usd += p * c
            except Exception:
                continue
        # Calcular descuento_total
        tasa_bcv = float(tasa_bcv) if tasa_bcv else 1.0
        descuento = float(descuento) if descuento else 0.0
        if tipo_descuento == 'porc':
            descuento_total = subtotal_usd * (descuento / 100)
        else:
            descuento_total = descuento / tasa_bcv
        # Calcular IVA
        iva = float(iva) if iva else 0.0
        iva_total = (subtotal_usd - descuento_total) * (iva / 100)
        # Calcular total_usd
        total_usd = subtotal_usd - descuento_total + iva_total
        # Guardar en el JSON
        cotizacion = {
            'numero_cotizacion': numero_cotizacion,
            'fecha': fecha,
            'hora': hora,
            'cliente': cliente,
            'productos': productos,
            'cantidades': cantidades,
            'precios': precios,
            'subtotal_usd': subtotal_usd,
            'subtotal_bs': subtotal_usd * tasa_bcv,
            'descuento': descuento,
            'tipo_descuento': tipo_descuento,
            'descuento_total': descuento_total,
            'iva': iva,
            'iva_total': iva_total,
            'total_usd': total_usd,
            'total_bs': total_usd * tasa_bcv,
            'tasa_bcv': tasa_bcv,
            'validez_dias': int(validez)
        }
        filename = os.path.join(cotizaciones_dir, f"cotizacion_{numero_cotizacion}.json")
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cotizacion, f, ensure_ascii=False, indent=4)
        flash('Cotización creada exitosamente', 'success')
        registrar_bitacora(session['usuario'], 'Nueva cotización', f"Cliente: {request.form.get('cliente_id','')}")
        return redirect(url_for('mostrar_cotizaciones'))
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    return render_template('cotizacion_form.html', clientes=clientes, inventario=inventario)

@app.route('/cotizaciones/<id>/editar', methods=['GET', 'POST'])
@login_required
def editar_cotizacion(id):
    """Formulario para editar una cotización."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if not os.path.exists(filename):
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    if request.method == 'POST':
        productos = request.form.getlist('productos[]')
        cantidades = request.form.getlist('cantidades[]')
        precios = request.form.getlist('precios[]')
        subtotal_usd = request.form.get('subtotal_usd', '0')
        subtotal_bs = request.form.get('subtotal_bs', '0')
        descuento = request.form.get('descuento', '0')
        tipo_descuento = request.form.get('tipo_descuento', 'bs')
        descuento_total = request.form.get('descuento_total', '0')
        iva = request.form.get('iva', '0')
        iva_total = request.form.get('iva_total', '0')
        total_usd = request.form.get('total_usd', '0')
        total_bs = request.form.get('total_bs', '0')
        tasa_bcv = request.form.get('tasa_bcv', '0')
        validez = request.form.get('validez', '3')
        cliente_id = request.form.get('cliente_id')
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        cliente = clientes.get(cliente_id, {})
        cotizacion = {
            'numero_cotizacion': id,
            'fecha': request.form['fecha'],
            'cliente': cliente,
            'productos': productos,
            'cantidades': cantidades,
            'precios': precios,
            'subtotal_usd': subtotal_usd,
            'subtotal_bs': subtotal_bs,
            'descuento': descuento,
            'tipo_descuento': tipo_descuento,
            'descuento_total': descuento_total,
            'iva': iva,
            'iva_total': iva_total,
            'total_usd': total_usd,
            'total_bs': total_bs,
            'tasa_bcv': tasa_bcv,
            'validez_dias': int(validez)
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(cotizacion, f, ensure_ascii=False, indent=4)
        flash('Cotización actualizada exitosamente', 'success')
        registrar_bitacora(session['usuario'], 'Editar cotización', f"ID: {id}")
        return redirect(url_for('mostrar_cotizaciones'))
    with open(filename, 'r', encoding='utf-8') as f:
        cotizacion = json.load(f)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    # --- Fix para edición: cliente_id y validez ---
    if 'cliente' in cotizacion and 'id' in cotizacion['cliente']:
        cotizacion['cliente_id'] = cotizacion['cliente']['id']
    else:
        cotizacion['cliente_id'] = ''
    cotizacion['validez'] = cotizacion.get('validez_dias', 3)
    if 'precios' in cotizacion:
        cotizacion['precios'] = [float(p) for p in cotizacion['precios']]
    # Fix para mostrar el número de cotización en el formulario
    cotizacion['numero'] = cotizacion.get('numero_cotizacion', id)
    return render_template('cotizacion_form.html', cotizacion=cotizacion, clientes=clientes, inventario=inventario, zip=zip)

@app.route('/cotizaciones/<id>/eliminar', methods=['POST'])
@login_required
def eliminar_cotizacion(id):
    """Elimina una cotización (elimina el archivo individual)."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if os.path.exists(filename):
        try:
            os.remove(filename)
            flash('Cotización eliminada exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Eliminar cotización', f"ID: {id}")
        except Exception as e:
            flash(f'Error al eliminar la cotización: {e}', 'danger')
    else:
        flash('Cotización no encontrada', 'danger')
    return redirect(url_for('mostrar_cotizaciones'))

@app.route('/clientes/<path:id>')
def ver_cliente(id):
    """Muestra los detalles de un cliente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    cuentas = cargar_datos(ARCHIVO_CUENTAS)
    tasa_bcv = obtener_tasa_bcv() or 1.0
    if id in clientes:
        cliente = clientes[id]
        # Calcular totales financieros
        facturas_cliente = [f for f in facturas.values() if f.get('cliente_id') == id]
        total_facturado = sum(float(f.get('total_usd', 0)) for f in facturas_cliente)
        total_abonado = sum(float(f.get('total_abonado', 0)) for f in facturas_cliente)
        cuenta = next((c for c in cuentas.values() if c.get('cliente_id') == id), None)
        total_por_cobrar = float(cuenta.get('saldo_pendiente', 0)) if cuenta else 0
        total_por_cobrar_bs = total_por_cobrar * tasa_bcv
        return render_template('cliente_detalle.html', cliente=cliente, total_facturado=total_facturado, total_abonado=total_abonado, total_por_cobrar=total_por_cobrar, total_por_cobrar_bs=total_por_cobrar_bs, tasa_bcv=tasa_bcv)
    flash('Cliente no encontrado', 'danger')
    return redirect(url_for('mostrar_clientes'))

@app.route('/clientes/<path:id>/editar', methods=['GET', 'POST'])
@login_required
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
            registrar_bitacora(session['usuario'], 'Editar cliente', f"ID: {id}, Nombre: {request.form.get('nombre','')}")
            return redirect(url_for('mostrar_clientes'))
        else:
            flash('Error al actualizar el cliente', 'danger')
    return render_template('cliente_form.html', cliente=clientes[id])

@app.route('/clientes/<path:id>/eliminar', methods=['POST'])
@login_required
def eliminar_cliente(id):
    """Elimina un cliente."""
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    if id in clientes:
        del clientes[id]
        if guardar_datos(ARCHIVO_CLIENTES, clientes):
            flash('Cliente eliminado exitosamente', 'success')
            registrar_bitacora(session['usuario'], 'Eliminar cliente', f"ID: {id}")
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
    # Filtros y orden
    q = request.args.get('q', '').strip().lower()
    filtro_categoria = request.args.get('categoria', '').strip().lower()
    filtro_orden = request.args.get('orden', 'nombre')
    # Filtrar por búsqueda
    if q:
        inventario = {k: v for k, v in inventario.items() if q in v.get('nombre', '').lower()}
    # Filtrar por categoría
    if filtro_categoria:
        inventario = {k: v for k, v in inventario.items() if filtro_categoria in v.get('categoria', '').lower()}
    # Ordenar
    if filtro_orden == 'nombre':
        inventario = dict(sorted(inventario.items(), key=lambda item: item[1].get('nombre', '').lower()))
    elif filtro_orden == 'stock':
        inventario = dict(sorted(inventario.items(), key=lambda item: int(item[1].get('cantidad', 0)), reverse=True))
    # Lista de categorías únicas para el select
    categorias = sorted(set(v.get('categoria', '') for v in cargar_datos(ARCHIVO_INVENTARIO).values() if v.get('categoria', '')))
    return render_template('ajustar_stock.html', inventario=inventario, q=q, filtro_categoria=filtro_categoria, filtro_orden=filtro_orden, categorias=categorias)

@app.route('/inventario/reporte')
def reporte_inventario():
    try:
        inventario = cargar_datos('inventario.json')
        empresa = cargar_datos('empresa.json')
        # Obtener la tasa BCV actual
        tasa_bcv = obtener_tasa_bcv()
        advertencia_tasa = None
        try:
            tasa_bcv = float(tasa_bcv)
        except Exception:
            tasa_bcv = 0
        if not tasa_bcv or tasa_bcv < 1:
            advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
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
                             fecha_actual=fecha_actual,
                             advertencia_tasa=advertencia_tasa)
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
    try:
        # Intentar obtener la tasa del día
        tasa = obtener_tasa_bcv_dia()
        if tasa:
            return jsonify({'tasa': tasa, 'advertencia': False})
        
        # Si no hay tasa del día, intentar obtener la última tasa guardada
        ultima_tasa = cargar_ultima_tasa_bcv()
        if ultima_tasa:
            return jsonify({'tasa': ultima_tasa, 'advertencia': True})
        
        # Si no hay tasa guardada, devolver error
        return jsonify({'error': 'No se pudo obtener la tasa BCV'}), 500
        
    except Exception as e:
        print(f"Error en /api/tasa-bcv: {e}")
        return jsonify({'error': str(e)}), 500

def obtener_tasa_bcv_dia():
    """Obtiene la tasa oficial USD/BS del BCV desde la web. Devuelve float o None si falla."""
    url = 'https://www.bcv.org.ve/glosario/cambio-oficial'
    try:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        resp = requests.get(url, timeout=10, verify=False)
        if resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        tasa = None
        
        # Buscar por id='dolar'
        dolar_div = soup.find('div', id='dolar')
        if dolar_div:
            strong = dolar_div.find('strong')
            if strong:
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                except:
                    pass
        
        # Buscar por strong con texto que parezca una tasa
        if not tasa:
            for strong in soup.find_all('strong'):
                txt = strong.text.strip().replace('.', '').replace(',', '.')
                try:
                    posible = float(txt)
                    if posible > 10:
                        tasa = posible
                        break
                except:
                    continue
        
        # Buscar cualquier número grande en el texto plano
        if not tasa:
            import re
            matches = re.findall(r'(\d{2,}[.,]\d{2})', resp.text)
            for m in matches:
                try:
                    posible = float(m.replace('.', '').replace(',', '.'))
                    if posible > 10:
                        tasa = posible
                        break
                except:
                    continue
        
        if tasa and tasa > 10:
            # Guardar la tasa en el archivo
            guardar_ultima_tasa_bcv(tasa)
            return tasa
        else:
            return None
            
    except Exception as e:
        print(f"Error obteniendo tasa BCV: {e}")
        return None

# --- Manejo de Errores ---
@app.errorhandler(404)
def pagina_no_encontrada(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def error_servidor(e):
    return render_template('500.html'), 500

@app.route('/clientes/reporte')
def reporte_clientes():
    try:
        clientes = cargar_datos(ARCHIVO_CLIENTES)
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        inventario = cargar_datos(ARCHIVO_INVENTARIO)
        empresa = cargar_empresa()
        
        # Obtener la tasa BCV actual
        tasa_bcv = obtener_tasa_bcv()
        advertencia_tasa = None
        try:
            tasa_bcv = float(tasa_bcv)
        except Exception:
            tasa_bcv = 0
        if not tasa_bcv or tasa_bcv < 1:
            advertencia_tasa = '¡Advertencia! No se ha podido obtener la tasa BCV actual.'
        
        # Calcular estadísticas generales
        total_clientes = len(clientes)
        total_facturas = len(facturas)
        total_facturado_general = 0
        total_abonado_general = 0
        total_cobrar = 0
        
        # Estadísticas por cliente
        stats_clientes = {}
        for id_cliente, cliente in clientes.items():
            stats_clientes[id_cliente] = {
                'id': id_cliente,
                'nombre': cliente['nombre'],
                'email': cliente.get('email', ''),
                'telefono': cliente.get('telefono', ''),
                'total_facturas': 0,
                'total_compras': 0,
                'ultima_compra': None,
                'total_facturado': 0,
                'total_abonado': 0,
                'total_por_cobrar': 0
            }
        
        # Procesar facturas
        for factura in facturas.values():
            id_cliente = factura['cliente_id']
            if id_cliente in stats_clientes:
                stats = stats_clientes[id_cliente]
                stats['total_facturas'] += 1
                total_facturado = float(factura.get('total', 0))
                total_abonado = float(factura.get('total_abonado', 0))
                total_por_cobrar = total_facturado - total_abonado
                
                stats['total_facturado'] += total_facturado
                stats['total_abonado'] += total_abonado
                stats['total_por_cobrar'] += total_por_cobrar
                stats['total_compras'] += total_facturado
                
                fecha_factura = datetime.strptime(factura['fecha'], '%Y-%m-%d')
                if not stats['ultima_compra'] or fecha_factura > datetime.strptime(stats['ultima_compra'], '%Y-%m-%d'):
                    stats['ultima_compra'] = factura['fecha']
                
                total_facturado_general += total_facturado
                total_abonado_general += total_abonado
                total_cobrar += total_por_cobrar
        
        # Ordenar clientes por total de compras
        top_clientes = sorted(
            [stats for stats in stats_clientes.values() if stats['total_compras'] > 0],
            key=lambda x: x['total_compras'],
            reverse=True
        )[:10]
        
        # Ordenar clientes por total por cobrar
        peores_clientes = sorted(
            [stats for stats in stats_clientes.values() if stats['total_por_cobrar'] > 0],
            key=lambda x: x['total_por_cobrar'],
            reverse=True
        )[:5]
        
        # Estadísticas de productos más comprados
        productos_stats = {}
        for factura in facturas.values():
            for item in factura.get('items', []):
                id_producto = item.get('id')
                if id_producto in inventario:
                    if id_producto not in productos_stats:
                        productos_stats[id_producto] = {
                            'nombre': inventario[id_producto]['nombre'],
                            'cantidad': 0,
                            'valor': 0
                        }
                    cantidad = int(item.get('cantidad', 0))
                    precio = float(item.get('precio', 0))
                    productos_stats[id_producto]['cantidad'] += cantidad
                    productos_stats[id_producto]['valor'] += cantidad * precio
        
        # Ordenar productos por cantidad
        top_productos = sorted(
            productos_stats.values(),
            key=lambda x: x['cantidad'],
            reverse=True
        )[:10]
        
        return render_template('reporte_clientes.html',
            clientes=clientes,
            facturas=facturas,
            inventario=inventario,
            empresa=empresa,
            tasa_bcv=tasa_bcv,
            advertencia_tasa=advertencia_tasa,
            total_clientes=total_clientes,
            total_facturas=total_facturas,
            total_facturado_general=total_facturado_general,
            total_abonado_general=total_abonado_general,
            total_cobrar=total_cobrar,
            top_clientes=top_clientes,
            peores_clientes=peores_clientes,
            top_productos=top_productos
        )
    except Exception as e:
        print(f"Error en reporte_clientes: {e}")
        return str(e), 500

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
@login_required
def mostrar_cuentas_por_cobrar():
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
@login_required
def mostrar_pagos_recibidos():
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
        # Calcular estado actualizado
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
        facturas_filtradas.append(factura)
    
    # Calcular totales
    total_facturas = len(facturas_filtradas)
    total_usd = sum(float(f.get('total_usd', 0)) for f in facturas_filtradas)
    total_bs = sum(float(f.get('total_bs', 0)) for f in facturas_filtradas)
    promedio_usd = total_usd / total_facturas if total_facturas > 0 else 0
    
    # Calcular top clientes
    clientes_totales = {}
    for factura in facturas_filtradas:
        cliente_id = factura['cliente_id']
        if cliente_id not in clientes_totales:
            clientes_totales[cliente_id] = {
                'total_usd': 0,
                'total_bs': 0,
                'total_facturas': 0
            }
        clientes_totales[cliente_id]['total_usd'] += float(factura.get('total_usd', 0))
        clientes_totales[cliente_id]['total_bs'] += float(factura.get('total_bs', 0))
        clientes_totales[cliente_id]['total_facturas'] += 1
    
    # Preparar lista de top clientes con todos los campos necesarios
    top_clientes = []
    for cid, stats in sorted(clientes_totales.items(), key=lambda x: x[1]['total_usd'], reverse=True)[:10]:
        cliente = clientes.get(cid, {})
        total_facturas = stats['total_facturas']
        promedio_usd = stats['total_usd'] / total_facturas if total_facturas > 0 else 0
        top_clientes.append({
            'nombre': cliente.get('nombre', 'Cliente no encontrado'),
            'total_facturas': total_facturas,
            'total_usd': stats['total_usd'],
            'total_bs': stats['total_bs'],
            'promedio_usd': promedio_usd
        })
    
    return render_template('reporte_facturas.html',
                         facturas=facturas_filtradas,
                         clientes=clientes,
                         total_facturas=total_facturas,
                         total_usd=total_usd,
                         total_bs=total_bs,
                         promedio_usd=promedio_usd,
                         top_clientes=top_clientes,
                         filtro_anio=filtro_anio,
                         filtro_mes=filtro_mes,
                         filtro_cliente=filtro_cliente)

@app.route('/inventario/')
def inventario_slash_redirect():
    return redirect(url_for('mostrar_inventario'))

@app.route('/facturas/reparar-totales')
def reparar_totales_facturas():
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    actualizadas = 0
    for id, factura in facturas.items():
        # Recalcular totales y pagos
        try:
            precios = factura.get('precios', [])
            cantidades = factura.get('cantidades', [])
            subtotal_usd = sum(float(precios[i]) * int(cantidades[i]) for i in range(len(precios))) if precios and cantidades else 0
            tasa_bcv = float(factura.get('tasa_bcv', 1))
            descuento_total = float(factura.get('descuento_total', 0))
            iva_total = float(factura.get('iva_total', 0))
            total_usd = subtotal_usd - descuento_total + iva_total
            total_bs = total_usd * tasa_bcv
            pagos = factura.get('pagos', [])
            total_abonado = sum(float(p.get('monto', 0)) for p in pagos)
            saldo_pendiente = max(total_usd - total_abonado, 0)
            # Actualizar campos
            factura['subtotal_usd'] = subtotal_usd
            factura['subtotal_bs'] = subtotal_bs
            factura['total_usd'] = total_usd
            factura['total_bs'] = total_bs
            factura['total_abonado'] = total_abonado
            factura['saldo_pendiente'] = saldo_pendiente
            facturas[id] = factura
            actualizadas += 1
        except Exception as e:
            print(f"Error actualizando factura {id}: {e}")
    guardar_datos(ARCHIVO_FACTURAS, facturas)
    flash(f'Se actualizaron {actualizadas} facturas con los totales y pagos recalculados.', 'success')
    return redirect(url_for('mostrar_facturas'))

@app.route('/reporte/cotizaciones')
def reporte_cotizaciones():
    """Reporte básico de cotizaciones."""
    cotizaciones = []
    cotizaciones_dir = 'cotizaciones_json'
    if os.path.exists(cotizaciones_dir):
        for filename in os.listdir(cotizaciones_dir):
            if filename.endswith('.json'):
                try:
                    with open(os.path.join(cotizaciones_dir, filename), 'r', encoding='utf-8') as f:
                        cot_data = json.load(f)
                        if not cot_data.get('numero_cotizacion') or not cot_data.get('fecha') or not cot_data.get('cliente', {}).get('nombre'):
                            continue
                        cotizaciones.append(cot_data)
                except Exception:
                    continue
    total_cotizaciones = len(cotizaciones)
    total_monto = sum(float(str(c.get('total_usd', 0)).replace('$', '').replace(',', '').strip()) for c in cotizaciones)
    return render_template('reporte_cotizaciones.html', cotizaciones=cotizaciones, total_cotizaciones=total_cotizaciones, total_monto=total_monto, now=datetime.now())

@app.route('/cotizaciones/<id>/convertir-a-factura')
def convertir_cotizacion_a_factura(id):
    """Convierte una cotización en factura y abre el formulario de factura para editar antes de guardar."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if not os.path.exists(filename):
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    with open(filename, 'r', encoding='utf-8') as f:
        cotizacion = json.load(f)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    empresa = cargar_empresa()
    # Preparar datos para el formulario de factura
    factura = {
        'numero': '',
        'fecha': datetime.now().strftime('%Y-%m-%d'),
        'hora': datetime.now().strftime('%H:%M'),
        'condicion_pago': 'contado',
        'fecha_vencimiento': '',
        'tasa_bcv': cotizacion.get('tasa_bcv', ''),
        'cliente_id': cotizacion['cliente'].get('id', ''),
        'productos': cotizacion.get('productos', []),
        'cantidades': cotizacion.get('cantidades', []),
        'precios': [float(p) for p in cotizacion.get('precios', [])],
        'descuento': cotizacion.get('descuento', '0'),
        'tipo_descuento': cotizacion.get('tipo_descuento', 'bs'),
        'iva': cotizacion.get('iva', '16'),
        'subtotal_usd': cotizacion.get('subtotal_usd', '0'),
        'subtotal_bs': cotizacion.get('subtotal_bs', '0'),
        'descuento_total': cotizacion.get('descuento_total', '0'),
        'iva_total': cotizacion.get('iva_total', '0'),
        'total_usd': cotizacion.get('total_usd', '0'),
        'total_bs': cotizacion.get('total_bs', '0'),
        'pagos': [],
        'estado': 'pendiente',
        'total_abonado': 0,
        'saldo_pendiente': cotizacion.get('total_usd', '0'),
    }
    inventario_disponible = {k: v for k, v in inventario.items() if int(v.get('cantidad', 0)) > 0 or k in factura.get('productos', [])}
    return render_template('factura_form.html', factura=factura, clientes=clientes, inventario=inventario_disponible, editar=False, empresa=empresa)

@app.route('/cotizaciones/<id>/imprimir')
def imprimir_cotizacion(id):
    """Vista amigable para imprimir la cotización."""
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if not os.path.exists(filename):
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    with open(filename, 'r', encoding='utf-8') as f:
        cotizacion = json.load(f)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    empresa = cargar_empresa()
    # Calcular totales en el backend
    total_usd = 0
    total_bs = 0
    tasa = float(cotizacion.get('tasa_bcv', 0) or 0)
    for precio, cantidad in zip(cotizacion.get('precios', []), cotizacion.get('cantidades', [])):
        try:
            p = float(precio)
            c = int(cantidad)
            subtotal_usd = p * c
            subtotal_bs = subtotal_usd * tasa
            total_usd += subtotal_usd
            total_bs += subtotal_bs
        except Exception:
            continue
    return render_template('cotizacion_imprimir.html', cotizacion=cotizacion, clientes=clientes, inventario=inventario, empresa=empresa, zip=zip, total_usd=total_usd, total_bs=total_bs)

@app.route('/cotizaciones/<id>/pdf')
def descargar_cotizacion_pdf(id):
    """Descargar la cotización como PDF."""
    try:
        import pdfkit
    except ImportError:
        flash('PDFKit no está instalado. Instala con: pip install pdfkit', 'danger')
        return redirect(url_for('imprimir_cotizacion', id=id))
    cotizaciones_dir = 'cotizaciones_json'
    filename = os.path.join(cotizaciones_dir, f"cotizacion_{id}.json")
    if not os.path.exists(filename):
        flash('Cotización no encontrada', 'danger')
        return redirect(url_for('mostrar_cotizaciones'))
    with open(filename, 'r', encoding='utf-8') as f:
        cotizacion = json.load(f)
    clientes = cargar_datos(ARCHIVO_CLIENTES)
    inventario = cargar_datos(ARCHIVO_INVENTARIO)
    empresa = cargar_empresa()
    rendered = render_template('cotizacion_imprimir.html', cotizacion=cotizacion, clientes=clientes, inventario=inventario, empresa=empresa, zip=zip)
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
        response.headers['Content-Disposition'] = f'attachment; filename=cotizacion_{cotizacion["numero_cotizacion"]}.pdf'
        return response
    except Exception as e:
        print(f"Error generando PDF: {str(e)}")
        flash('Error al generar el PDF. Por favor, verifica que wkhtmltopdf esté instalado correctamente.', 'danger')
        return redirect(url_for('imprimir_cotizacion', id=id))

@app.route('/cotizacion/<numero>')
def ver_cotizacion(numero):
    try:
        # Cargar la cotización
        cotizacion_path = os.path.join('cotizaciones_json', f'cotizacion_{numero}.json')
        if not os.path.exists(cotizacion_path):
            flash('Cotización no encontrada', 'error')
            return redirect(url_for('cotizaciones'))
        
        with open(cotizacion_path, 'r', encoding='utf-8') as f:
            cotizacion = json.load(f)
        
        # Cargar datos adicionales necesarios
        with open('inventario.json', 'r', encoding='utf-8') as f:
            inventario = json.load(f)
        with open('empresa.json', 'r', encoding='utf-8') as f:
            empresa = json.load(f)
        
        return render_template('cotizacion_imprimir.html', cotizacion=cotizacion, inventario=inventario, empresa=empresa, zip=zip)
    except Exception as e:
        flash(f'Error al cargar la cotización: {str(e)}', 'error')
        return redirect(url_for('cotizaciones'))

@app.route('/login', methods=['GET', 'POST'])
@csrf.exempt
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            flash('Por favor ingrese usuario y contraseña', 'warning')
            return render_template('login.html')
        
        if verify_password(username, password):
            session['usuario'] = username
            registrar_bitacora(username, 'Inicio de sesión', 'Inicio de sesión exitoso')
            flash('Bienvenido al sistema', 'success')
            return redirect(url_for('index'))
        else:
            registrar_bitacora(username, 'Intento fallido', 'Intento fallido de inicio de sesión')
            flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    usuario = session.get('usuario', 'desconocido')
    registrar_bitacora(usuario, 'Cierre de sesión', 'Sesión finalizada')
    session.pop('usuario', None)
    flash('Sesión cerrada exitosamente', 'info')
    return redirect(url_for('login'))

@app.route('/bitacora')
@login_required
def ver_bitacora():
    try:
        with open('bitacora.log', 'r', encoding='utf-8') as f:
            lineas = f.readlines()
    except Exception:
        lineas = []
    return render_template('bitacora.html', lineas=lineas)

@app.route('/bitacora/limpiar', methods=['POST'])
@login_required
@csrf.exempt
def limpiar_bitacora():
    try:
        # Registrar la acción antes de limpiar
        usuario = session.get('usuario', 'desconocido')
        registrar_bitacora(usuario, 'Limpiar bitácora', 'Se limpió toda la bitácora del sistema')
        
        # Limpiar el archivo
        open('bitacora.log', 'w').close()
        
        flash('Bitácora limpiada exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al limpiar la bitácora: {str(e)}', 'danger')
    
    return redirect(url_for('ver_bitacora'))

@app.route('/facturas/<id>/registrar_pago', methods=['POST'])
@login_required
def registrar_pago(id):
    facturas = cargar_datos(ARCHIVO_FACTURAS)
    factura = facturas.get(id)
    if not factura:
        flash('Factura no encontrada', 'danger')
        return redirect(url_for('mostrar_facturas'))

    try:
        monto = float(request.form.get('monto_pago', 0))
        moneda = request.form.get('moneda_pago', 'USD')
        metodo = request.form.get('metodo_pago', '')
        referencia = request.form.get('referencia_pago', '')
        banco = request.form.get('banco', '')
        tasa_bcv = float(factura.get('tasa_bcv', 1.0))
        
        # Convertir a USD si el pago es en Bs
        monto_usd = monto if moneda == 'USD' else monto / tasa_bcv
        
        # Manejar la captura de transacción si se subió una
        captura_path = None
        if 'captura_transaccion' in request.files:
            captura = request.files['captura_transaccion']
            if captura and captura.filename:
                # Crear directorio si no existe
                upload_dir = os.path.join(app.static_folder, 'capturas_transacciones')
                os.makedirs(upload_dir, exist_ok=True)
                
                # Generar nombre único para el archivo
                filename = secure_filename(f"{id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{captura.filename}")
                captura_path = os.path.join('capturas_transacciones', filename)
                captura.save(os.path.join(app.static_folder, captura_path))
        
        nuevo_pago = {
            'id': str(uuid4()),
            'monto': monto_usd,
            'moneda': moneda,
            'metodo': metodo,
            'referencia': referencia,
            'banco': banco,
            'captura_path': captura_path,
            'fecha': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        if 'pagos' not in factura or not isinstance(factura['pagos'], list):
            factura['pagos'] = []
        factura['pagos'].append(nuevo_pago)
        
        # Recalcular total abonado y saldo pendiente
        total_abonado = sum(float(p['monto']) for p in factura['pagos'])
        factura['total_abonado'] = total_abonado
        factura['saldo_pendiente'] = max(factura.get('total_usd', 0) - total_abonado, 0)
        
        # Actualizar estado
        if total_abonado >= factura.get('total_usd', 0) and factura.get('total_usd', 0) > 0:
            factura['estado'] = 'pagada'
        else:
            factura['estado'] = 'pendiente'
            
        facturas[id] = factura
        guardar_datos(ARCHIVO_FACTURAS, facturas)
        flash('Pago registrado exitosamente.', 'success')
    except Exception as e:
        flash(f'Error al registrar el pago: {e}', 'danger')
    return redirect(url_for('ver_factura', id=id))

@app.route('/facturas/<id>/eliminar_pago/<pago_id>', methods=['POST'])
@login_required
def eliminar_pago(id, pago_id):
    try:
        # Cargar datos
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        if id not in facturas:
            flash('Factura no encontrada', 'error')
            return redirect(url_for('mostrar_facturas'))
        
        factura = facturas[id]
        pagos = factura.get('pagos', [])
        
        # Encontrar y eliminar el pago
        pago_encontrado = False
        for i, pago in enumerate(pagos):
            if str(pago.get('id', '')) == str(pago_id):
                # Restar el monto del pago del total abonado
                monto_pago = float(pago.get('monto', 0))
                if pago.get('moneda') == 'Bs':
                    monto_pago = monto_pago / float(factura.get('tasa_bcv', 1))
                
                factura['total_abonado'] = float(factura.get('total_abonado', 0)) - monto_pago
                factura['saldo_pendiente'] = float(factura.get('total_usd', 0)) - float(factura.get('total_abonado', 0))
                
                # Eliminar el pago
                pagos.pop(i)
                pago_encontrado = True
                break
        
        if not pago_encontrado:
            flash('Pago no encontrado', 'error')
            return redirect(url_for('editar_factura', id=id))
        
        # Actualizar estado de la factura
        if factura['total_abonado'] >= factura.get('total_usd', 0) and factura.get('total_usd', 0) > 0:
            factura['estado'] = 'pagada'
        else:
            factura['estado'] = 'pendiente'
        
        # Guardar cambios
        facturas[id] = factura
        if guardar_datos(ARCHIVO_FACTURAS, facturas):
            flash('Pago eliminado exitosamente', 'success')
        else:
            flash('Error al guardar los cambios', 'error')
            
    except Exception as e:
        flash(f'Error al eliminar el pago: {str(e)}', 'error')
    
    return redirect(url_for('editar_factura', id=id))

@app.route('/facturas/<id>/saldo')
@login_required
def obtener_saldo_factura(id):
    try:
        facturas = cargar_datos(ARCHIVO_FACTURAS)
        if id not in facturas:
            return jsonify({'error': 'Factura no encontrada'}), 404
        
        factura = facturas[id]
        saldo_pendiente = float(factura.get('saldo_pendiente', 0))
        tasa_bcv = float(factura.get('tasa_bcv', 0))
        
        return jsonify({
            'saldo_pendiente': saldo_pendiente,
            'tasa_bcv': tasa_bcv
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/guardar_ubicacion_precisa', methods=['POST'])
def guardar_ubicacion_precisa():
    data = request.get_json()
    if data and 'lat' in data and 'lon' in data:
        lat = data['lat']
        lon = data['lon']
        # Reverse geocoding con Nominatim
        try:
            url = f'https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=10&addressdetails=1'
            headers = {'User-Agent': 'mi-app-web/1.0'}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                info = resp.json().get('address', {})
                ciudad = info.get('city') or info.get('town') or info.get('village') or info.get('hamlet') or ''
                estado = info.get('state', '')
                pais = info.get('country', '')
                texto = ', '.join([v for v in [ciudad, estado, pais] if v])
                session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': texto}
            else:
                session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': ''}
        except Exception:
            session['ubicacion_precisa'] = {'lat': lat, 'lon': lon, 'texto': ''}
        return jsonify({'status': 'ok'})
    return jsonify({'status': 'error'}), 400

# --- Bloque para Ejecutar la Aplicación ---
if __name__ == '__main__':
    app.run(debug=True)