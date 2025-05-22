# -*- coding: utf-8 -*-
import json
import os
import datetime
import traceback
import csv
from collections import Counter
import shutil
import copy # Necesario para copiar datos de factura al regenerar PDF
import glob
import requests
from bs4 import BeautifulSoup
import urllib3

try:
    import tkinter as tk
    from tkinter import messagebox
except ImportError:
    print("Error: Tkinter no está instalado. Por favor, instala Tkinter para ejecutar esta aplicación.")
    exit(1)

# Importar qrcode y Image si no están ya
try:
    import qrcode
    from PIL import Image
except ImportError:
    print("¡ADVERTENCIA! Faltan bibliotecas para QR. Ejecuta: pip install qrcode[pil]")
    qrcode = None

from fpdf import FPDF
from fpdf.enums import XPos, YPos
import colorama
from colorama import Fore, Back, Style, init
# Inicializar colorama
init(autoreset=True)

# --- Constantes ---
ARCHIVO_CLIENTES = 'clientes.json'; ARCHIVO_INVENTARIO = 'inventario.json'; ARCHIVO_CONFIG = 'config.json'
ARCHIVO_CUENTAS_COBRAR = 'cuentas_por_cobrar.json'; CARPETA_FACTURAS_JSON = 'facturas_json'
CARPETA_FACTURAS_PDF = 'facturas_pdf'; CARPETA_IMAGENES = 'imagenes_productos'; CARPETA_LISTAS_INVENTARIO = 'listas_inventario'
CARPETA_HISTORIAL_CLIENTES = 'historial_clientes'; CARPETA_REPORTES_GENERALES = 'reportes_generales'
CARPETA_REPORTES_FACTURAS = 'reportes_facturas'; ARCHIVO_TEMP_QR = 'temp_qr_code.png'; TASA_IVA_POR_DEFECTO = 0.16
NOMBRE_EMPRESA = "PRODUCTOS NATURALES KISVIC 1045, C.A."; RIF_EMPRESA = "J-406373818"
TELEFONO_EMPRESA = "0424-728-6225"; ARCHIVO_LOGO = "logo.png"

# --- Constantes de Carpetas ---
CARPETA_FACTURAS_JSON = 'facturas_json'
CARPETA_FACTURAS_PDF = 'facturas_pdf'
CARPETA_IMAGENES = 'imagenes'
CARPETA_LISTAS_INVENTARIO = 'listas_inventario'
CARPETA_HISTORIAL_CLIENTES = 'historial_clientes'
CARPETA_REPORTES_GENERALES = 'reportes_generales'
CARPETA_REPORTES_FACTURAS = 'reportes_facturas'
CARPETA_REPORTES_CUENTAS = 'reportes_cuentas'
CARPETA_REPORTES_PAGOS = 'reportes_pagos'
CARPETA_REPORTES_CLIENTES = 'reportes_clientes'

# Constantes para carpetas de reportes
CARPETA_REPORTES_PAGOS = 'reportes_pagos'
CARPETA_REPORTES_GENERALES = os.path.join(CARPETA_REPORTES_PAGOS, 'generales')
CARPETA_REPORTES_INDIVIDUALES = os.path.join(CARPETA_REPORTES_PAGOS, 'individuales')
CARPETA_REPORTES_CUENTAS = 'reportes_cuentas'
CARPETA_REPORTES_PENDIENTES = os.path.join(CARPETA_REPORTES_CUENTAS, 'pendientes')
CARPETA_REPORTES_CONTADO = os.path.join(CARPETA_REPORTES_CUENTAS, 'contado')
CARPETA_REPORTES_TODAS = os.path.join(CARPETA_REPORTES_CUENTAS, 'todas')

# --- Constantes de Cotizaciones ---
CARPETA_COTIZACIONES_JSON = 'cotizaciones_json'
CARPETA_COTIZACIONES_PDF = 'cotizaciones_pdf'
ARCHIVO_CONFIG_COT = 'config_cot.json'

# --- Funciones de Cotizaciones ---
def cargar_config_cot():
    config = cargar_datos(ARCHIVO_CONFIG_COT)
    config.setdefault('proxima_cotizacion', 1)
    return config

def guardar_config_cot(config):
    guardar_datos(config, ARCHIVO_CONFIG_COT)

def obtener_siguiente_numero_cotizacion(config):
    numero = config.get('proxima_cotizacion', 1)
    config['proxima_cotizacion'] = numero + 1
    guardar_config_cot(config)
    return f"{numero:04d}"

def generar_pdf_cotizacion(cot_data, nombre_archivo_pdf):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        # --- Logo centrado en la parte superior ---
        logo_w = 32
        logo_h = 32
        logo_x = (210 - logo_w) / 2
        logo_y = 10
        try:
            if os.path.exists(ARCHIVO_LOGO):
                pdf.image(ARCHIVO_LOGO, x=logo_x, y=logo_y, w=logo_w, h=logo_h)
        except Exception as e_logo:
            print(f"Adv: Error al cargar el logo: {e_logo}")
        pdf.set_y(logo_y + logo_h + 2)
        def to_latin1(t):
            txt = str(t) if t is not None else ''
            return txt.encode('latin-1','replace').decode('latin-1')
        pdf.set_font('Arial','B',14)
        pdf.set_text_color(0,0,128)
        pdf.cell(0,8,to_latin1(NOMBRE_EMPRESA),0,1,'C')
        pdf.set_font('Arial','',10)
        pdf.set_text_color(0,0,0)
        pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C')
        pdf.cell(0,5,f"Teléfono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C')
        pdf.cell(0,5,"Centro Comercial Caña de Azucar (Antiguo Merbumar), Nave A, Locales 154-156-Maracay-Edo.Aragua",0,1,'C')
        pdf.ln(2)
        pdf.set_font('Arial','B',16)
        pdf.set_text_color(0,0,128)
        pdf.cell(0,10,'COTIZACIÓN',0,1,'C')
        pdf.set_text_color(0,0,0)
        pdf.ln(2)
        # --- Datos Cotización (esquina superior derecha) ---
        pdf.set_font('Arial','B',10)
        num_c = cot_data.get('numero_cotizacion','N/A')
        fecha_iso = cot_data.get('fecha','N/A')
        try:
            fecha_dt = datetime.datetime.fromisoformat(fecha_iso)
            fecha_legible = fecha_dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            fecha_legible = fecha_iso
        validez = cot_data.get('validez_dias', 7)
        # Guardar posición actual para datos cliente
        y_datos = pdf.get_y()
        pdf.set_xy(130, 18)
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Nro. Cotización:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,num_c,0,1,'L')
        pdf.set_x(130)
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Fecha Emisión:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,fecha_legible,0,1,'L')
        # Alinear perfectamente Validez con Fecha Emisión
        pdf.set_x(130)
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Validez:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,f"{validez} días",0,1,'L')
        # --- Datos Cliente ---
        cli = cot_data.get('cliente',{})
        rif_cliente = cli.get('rif') or 'N/A'
        pdf.set_xy(10, y_datos + 2)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Cliente RIF:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(rif_cliente),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Nombre:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('nombre','N/A')),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Dirección:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('direccion','N/A')),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Teléfono:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('telefono','N/A')),0,1,'L')
        pdf.ln(5)
        # --- Tabla de Productos ---
        pdf.set_font('Arial','B',9)
        pdf.set_fill_color(240,240,240)
        pdf.set_draw_color(100,100,100)
        c_w = [20, 60, 15, 25, 25, 25, 25]
        headers = ['Código', 'Descripción', 'Cantidad', 'P. Unit USD', 'P. Unit Bs', 'Subtotal USD', 'Subtotal Bs']
        for i, h in enumerate(headers):
            pdf.cell(c_w[i], 7, h, 1, 0, 'C', fill=True)
        pdf.ln()
        pdf.set_font('Arial','',8)
        items = cot_data.get('items',[])
        tasa = cot_data.get('tasa_cambio', 0)
        for item in items:
            codigo = to_latin1(item.get('id',''))
            desc = to_latin1(item.get('nombre',''))
            cant = item.get('cantidad',0)
            pu_usd = item.get('precio_unitario_usd',0)
            pu_bs = pu_usd * tasa
            subtotal_usd = cant * pu_usd
            subtotal_bs = cant * pu_bs
            pdf.set_fill_color(255,255,255)
            pdf.cell(c_w[0], 6, str(codigo), 1, 0, 'C')
            pdf.cell(c_w[1], 6, desc, 1, 0, 'L')
            pdf.cell(c_w[2], 6, str(cant), 1, 0, 'C')
            pdf.cell(c_w[3], 6, f"${pu_usd:,.2f}", 1, 0, 'R')
            pdf.cell(c_w[4], 6, f"{pu_bs:,.2f} Bs", 1, 0, 'R')
            pdf.cell(c_w[5], 6, f"${subtotal_usd:,.2f}", 1, 0, 'R')
            pdf.cell(c_w[6], 6, f"{subtotal_bs:,.2f} Bs", 1, 1, 'R')
        pdf.ln(5)
        # --- Totales ---
        sub_bs = cot_data.get('subtotal_bs',0)
        iva_bs = cot_data.get('iva_bs',0)
        desc_bs = cot_data.get('descuento_bs',0)
        tot_bs = cot_data.get('total_bs',0)
        sub_usd = cot_data.get('subtotal_usd',0)
        iva_usd = cot_data.get('iva_usd',0)
        desc_usd = cot_data.get('descuento_usd',0)
        tot_usd = cot_data.get('total_usd',0)
        def fmt(val):
            return f"{abs(val):,.2f}"
        w_label = 50
        w_val = 40
        x_totales = pdf.w - pdf.r_margin - (w_label + w_val)
        pdf.set_font('Arial','',10)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'SUBTOTAL BS:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(sub_bs)} Bs",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'IVA:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(iva_bs)} Bs",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'DESCUENTO:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(desc_bs)} Bs",0,1,'R')
        pdf.set_font('Arial','B',11)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'TOTAL BS:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(tot_bs)} Bs",0,1,'R')
        pdf.ln(2)
        pdf.set_font('Arial','',10)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'SUBTOTAL USD:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(sub_usd)} $",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'IVA:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(iva_usd)} $",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'DESCUENTO:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(desc_usd)} $",0,1,'R')
        pdf.set_font('Arial','B',11)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'TOTAL USD:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(tot_usd)} $",0,1,'R')
        pdf.ln(10)
        # --- Pie de Página ---
        pdf.set_font('Arial','B',9)
        pdf.set_text_color(0,0,0)
        pie_1 = "Este documento es una cotización y no constituye un documento fiscal ni compromiso de venta. Precios sujetos a cambio sin previo aviso. Vigencia según validez indicada."
        pie_2 = f"Tasa de cambio utilizada: {tasa:.2f} Bs/USD"
        pdf.set_x(10)
        pdf.set_y(pdf.get_y()+5)
        pdf.set_font('Arial','',9)
        pdf.multi_cell(0,6,pie_1,0,'J')
        pdf.set_x(10)
        pdf.cell(0,6,pie_2,0,1,'C')
        os.makedirs(os.path.dirname(nombre_archivo_pdf), exist_ok=True)
        pdf.output(nombre_archivo_pdf)
        print(Fore.GREEN + f"Cotización PDF: '{nombre_archivo_pdf}'")
        return True
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF COTIZACIÓN ---")
        print(Fore.RED + f"Error: {type(e).__name__} - {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")
        if os.path.exists(nombre_archivo_pdf):
            try:
                os.remove(nombre_archivo_pdf)
                print("Eliminado PDF fallido.")
            except Exception as err:
                print(Fore.YELLOW + f"Adv: No se pudo eliminar PDF: {err}")
        return False

# --- Crear Cotización ---
def crear_cotizacion(clientes, inventario):
    try:
        print(Fore.CYAN + "\n--- Crear Cotización ---")
        config_cot = cargar_config_cot()
        fecha_hora_actual = datetime.datetime.now()
        print(Fore.WHITE + f"\nFecha y hora actual: {fecha_hora_actual.strftime('%d/%m/%Y %H:%M')}")
        modificar_fecha = input(Fore.YELLOW + "¿Desea modificar la fecha y hora? (S/N): ").upper()
        if modificar_fecha == 'S':
            while True:
                try:
                    fecha_str = input(Fore.WHITE + "Ingrese la fecha (DD/MM/YYYY): ")
                    hora_str = input(Fore.WHITE + "Ingrese la hora (HH:MM): ")
                    fecha_hora_str = f"{fecha_str} {hora_str}"
                    fecha_hora_actual = datetime.datetime.strptime(fecha_hora_str, '%d/%m/%Y %H:%M')
                    break
                except ValueError:
                    print(Fore.RED + "Formato inválido. Use DD/MM/YYYY para la fecha y HH:MM para la hora.")
        # Tasa
        tasa = 0; tasa_valida = False
        while not tasa_valida:
            try:
                t_s = input(Fore.YELLOW+f"TASA Bs./USD: ").strip().replace(',','.')
                tasa_temp = float(t_s)
                if tasa_temp <= 0:
                    print(Fore.YELLOW+"Positiva.")
                else:
                    tasa = tasa_temp
                    tasa_valida = True
            except ValueError:
                print(Fore.YELLOW+"Inválida.")
        # IVA
        print(Fore.WHITE + "\nTasa IVA predeterminada: 0%")
        while True:
            try:
                iva_str = input(Fore.YELLOW + "Ingrese tasa IVA (0-100%) o Enter para 0%: ").strip().replace(',','.')
                if not iva_str:
                    t_iva = 0.0
                    print(Fore.GREEN + "Usando tasa IVA: 0%")
                    break
                t_iva = float(iva_str) / 100
                if 0 <= t_iva <= 1:
                    print(Fore.GREEN + f"Usando tasa IVA: {t_iva*100:.0f}%")
                    break
                else:
                    print(Fore.RED + "La tasa debe estar entre 0% y 100%")
            except ValueError:
                print(Fore.RED + "Valor inválido. Ingrese un número entre 0 y 100")
        # Descuento
        while True:
            try:
                desc_str = input(Fore.YELLOW + "Ingrese porcentaje de DESCUENTO (0-100%) o Enter para 0%: ").strip().replace(',','.')
                if not desc_str:
                    descuento_porcentaje = 0.0
                    print(Fore.GREEN + "Sin descuento.")
                    break
                descuento_porcentaje = float(desc_str)
                if 0 <= descuento_porcentaje <= 100:
                    print(Fore.GREEN + f"Descuento aplicado: {descuento_porcentaje:.2f}%")
                    break
                else:
                    print(Fore.RED + "El descuento debe estar entre 0% y 100%")
            except ValueError:
                print(Fore.RED + "Valor inválido. Ingrese un número entre 0 y 100")
        # Validez
        while True:
            try:
                validez_str = input(Fore.YELLOW + "Validez de la cotización en días (ej: 7): ").strip()
                if not validez_str:
                    validez = 7
                    break
                validez = int(validez_str)
                if validez > 0:
                    break
                else:
                    print(Fore.RED + "Debe ser mayor a 0.")
            except ValueError:
                print(Fore.RED + "Valor inválido.")
        # Número de cotización
        num_cot = obtener_siguiente_numero_cotizacion(config_cot)
        # Buscar cliente
        cli = None
        while not cli:
            print("\n--- Buscar Cliente ---")
            print("1. Buscar por RIF")
            print("2. Buscar por Nombre")
            op_cli = input(Fore.YELLOW + "Seleccione: ")
            if op_cli == '1':
                rif = input(Fore.WHITE + "RIF del Cliente: ").strip().upper()
                cli = clientes.get(rif)
                if cli:
                    cli = dict(cli)
                    cli['rif'] = rif
                    print(f"Cliente: {cli['nombre']}")
                    break
            elif op_cli == '2':
                resultados = buscar_cliente_por_nombre(clientes)
                if resultados:
                    rif = input("\nIngrese el RIF del cliente deseado: ").strip().upper()
                    cli = clientes.get(rif)
                    if cli:
                        cli = dict(cli)
                        cli['rif'] = rif
                        print(f"Cliente: {cli['nombre']}")
                        break
            else:
                print(Fore.YELLOW + "Opción inválida.")
                continue
            if not cli:
                print(Fore.YELLOW + f"Cliente no encontrado.")
                if input("¿Desea crear un nuevo cliente? (s/n): ").lower() == 's':
                    agregar_o_modificar_cliente(clientes)
                    clientes = cargar_clientes()
                    cli = clientes.get(rif)
                    if cli:
                        print(f"Cliente creado: {cli['nombre']}")
                        break
                    else:
                        print(Fore.RED + "Error al crear el cliente.")
                        return False
                else:
                    print("Operación cancelada.")
                    return False
        items_cot=[]
        while True:
            print(Style.BRIGHT+"\n--- Agregar Ítem ---")
            if items_cot:
                print(Fore.BLUE+"--- Ítems en Cotización Actual ---")
                temp_sub_usd = sum(it['cantidad']*it.get('precio_unitario_usd',0) for it in items_cot)
                print(f"{'ID':<10} {'Nombre':<25} {'Cant':>5} {'P.U USD':>10} {'SubT USD':>10}")
                print("-" * 65)
                for item in items_cot: subt_usd = item['cantidad'] * item['precio_unitario_usd']; print(f"{item['id']:<10} {item['nombre'][:25]:<25} {item['cantidad']:>5} {item['precio_unitario_usd']:>10.2f} {subt_usd:>10.2f}")
                print("-" * 65); print(f"{'Subtotal actual:':>54} ${temp_sub_usd:,.2f}"); print("-" * 65)
            op_prod = input("¿Cómo desea buscar el producto? (1: ID, 2: Nombre, 'fin' terminar): ").strip()
            if op_prod.upper() == 'FIN': break
            pid, prod = None, None
            if op_prod == '1':
                pid = input("ID del producto: ").strip().upper()
                prod = get_producto(inventario, pid)
            elif op_prod == '2':
                resultados = buscar_producto_por_nombre(inventario)
                if resultados:
                    pid = input("\nIngrese el ID del producto deseado: ").strip().upper()
                    prod = get_producto(inventario, pid)
            else:
                print(Fore.YELLOW + "Opción inválida.")
                continue
            if not prod:
                print(Fore.RED + "Producto no existe.")
                continue
            while True:
                try:
                    cant=int(input(f"Cant: ").strip());
                    if cant>0:
                        pu_u=prod.get('precio',0); pu_b=pu_u*tasa;
                        it={"id":pid,"nombre":prod['nombre'],"cantidad":cant,"precio_unitario_usd":pu_u,"precio_unitario_bs":pu_b,"categoria":prod.get('categoria',''),"ruta_imagen":prod.get('ruta_imagen','')}
                        items_cot.append(it); print(Fore.GREEN+"-> Ítem agregado."); break
                    else: print(Fore.YELLOW+"Cant > 0.")
                except ValueError: print(Fore.YELLOW+"Inválida.")
        if not items_cot: print("Cancelada (sin ítems)."); return False
        # Cálculos Finales
        sub_bs = sum(it['cantidad']*it.get('precio_unitario_bs',0) for it in items_cot)
        iva_bs = sub_bs * t_iva
        tot_bs = sub_bs + iva_bs
        monto_descuento_bs = (sub_bs + iva_bs) * (descuento_porcentaje/100)
        tot_bs -= monto_descuento_bs
        sub_usd = sum(it['cantidad']*it.get('precio_unitario_usd',0) for it in items_cot)
        iva_usd = sub_usd * t_iva
        tot_usd = sub_usd + iva_usd
        monto_descuento_usd = (sub_usd + iva_usd) * (descuento_porcentaje/100)
        tot_usd -= monto_descuento_usd
        print(Fore.CYAN+Style.BRIGHT+"\n--- Resumen Final Cotización ---")
        f_a=datetime.datetime.now()
        print(f"Nro:{num_cot}|Fecha:{f_a.strftime('%d/%m/%Y %H:%M')}")
        print(f"Cli:{cli['nombre']}({cli.get('rif','')})")
        print(f"Tasa:{tasa:.2f}Bs/USD")
        print("-" * 70)
        print(f"{'Cant':<4}{'Producto':<25}{'P.U USD':>10}{'P.U Bs':>12}{'SubT Bs':>12}")
        print("-" * 70)
        for i in items_cot:
            s_it_b=i['cantidad']*i.get('precio_unitario_bs',0)
            n_m=i.get('nombre','N/A')[:25]
            pu_u_m=i.get('precio_unitario_usd',0)
            pu_b_m=i.get('precio_unitario_bs',0)
            print(f"{i['cantidad']:<4}{n_m:<25}{pu_u_m:>10.2f}{pu_b_m:>12.2f}{s_it_b:>12,.2f}")
        print("-" * 70)
        print(f"{'Subtotal (Bs):':>53} Bs. {sub_bs:>12,.2f}")
        print(f"{'Subtotal USD:':>53} USD {sub_usd:>10,.2f}")
        print(f"{'IVA:':>53} Bs. {iva_bs:>12,.2f}")
        print(Style.BRIGHT+f"{'Total a Pagar (Bs):':>53} Bs. {tot_bs:>12,.2f}")
        print(Style.BRIGHT+f"{'Total a Pagar (USD):':>53} USD {tot_usd:>10,.2f}")
        print("-" * 70)
        while True:
            confirmar = input(Fore.YELLOW + "¿Generar/Guardar cotización? (s/n): ").lower()
            if confirmar == 's':
                cot_d = {
                    "numero_cotizacion": num_cot,
                    "fecha": fecha_hora_actual.isoformat(),
                    "tasa_cambio": tasa,
                    "cliente": {"rif": cli.get('rif',''), **cli},
                    "items": items_cot,
                    "subtotal_bs": sub_bs,
                    "iva_bs": iva_bs,
                    "total_bs": tot_bs,
                    "subtotal_usd": sub_usd,
                    "iva_usd": iva_usd,
                    "total_usd": tot_usd,
                    "tasa_iva_aplicada": t_iva,
                    "descuento_porcentaje": descuento_porcentaje,
                    "descuento_bs": monto_descuento_bs,
                    "descuento_usd": monto_descuento_usd,
                    "validez_dias": validez
                }
                n_json = os.path.join(CARPETA_COTIZACIONES_JSON, f"cotizacion_{num_cot}.json")
                os.makedirs(CARPETA_COTIZACIONES_JSON, exist_ok=True)
                if guardar_datos(cot_d, n_json):
                    print(Fore.GREEN+f"Cotización JSON: '{n_json}'")
                    n_pdf = os.path.join(CARPETA_COTIZACIONES_PDF, f"cotizacion_{num_cot}.pdf")
                    os.makedirs(CARPETA_COTIZACIONES_PDF, exist_ok=True)
                    if generar_pdf_cotizacion(cot_d, n_pdf):
                        print(Fore.GREEN + f"Cotización PDF generada: '{n_pdf}'")
                    else:
                        print(Fore.RED+f"Error PDF {num_cot}.")
                    return True
            elif confirmar == 'n':
                print("Operación cancelada.")
                return False
            else:
                print(Fore.YELLOW + "Opción inválida. Ingrese 's' o 'n'.")
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR CREAR COTIZACIÓN ---")
        print(Fore.RED + f"Error CRITICO: {type(e).__name__} - {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")
        return False

# --- Funciones de Utilidad ---
def cargar_datos(nombre_archivo):
    """Carga datos desde un archivo JSON, intentando UTF-8 y luego Latin-1."""
    encodings_to_try = ['utf-8', 'latin-1']
    if os.path.exists(nombre_archivo):
        for encoding in encodings_to_try:
            try:
                with open(nombre_archivo, 'r', encoding=encoding, newline='') as f:
                    content = f.read(); return json.loads(content) if content.strip() else {}
            except (json.JSONDecodeError, IOError) as e:
                if isinstance(e, UnicodeDecodeError) and encoding != encodings_to_try[-1]: continue
                else: print(Fore.YELLOW + f"Adv {nombre_archivo} (encoding {encoding}): {e}"); return {}
            except Exception as e_gen: print(Fore.RED + f"Error inesperado leyendo {nombre_archivo}: {e_gen}"); return {}
        print(Fore.RED + f"Error: No se pudo decodificar {nombre_archivo} con {', '.join(encodings_to_try)}."); return {}
    else: return {}

def guardar_datos(datos, nombre_archivo):
    """Guarda datos en un archivo JSON (siempre en UTF-8)."""
    try:
        carpeta_destino = os.path.dirname(nombre_archivo)
        if carpeta_destino and not os.path.exists(carpeta_destino): os.makedirs(carpeta_destino, exist_ok=True)
        with open(nombre_archivo, 'w', encoding='utf-8') as f: json.dump(datos, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e: print(Fore.RED + f"Error guardando {nombre_archivo}: {e}"); return False

def forzar_saltos_linea(texto, max_largo=40):
    """Divide un texto en líneas de longitud máxima (aproximada)."""
    if not texto: return ""
    proc=[]; parts=texto.split(' ')
    for p in parts:
        if len(p) > max_largo: pp=" ".join([p[i:i+max_largo] for i in range(0, len(p), max_largo)]); proc.append(pp)
        else: proc.append(p)
    return " ".join(proc)

# --- Gestión de Clientes ---
def cargar_clientes(): return cargar_datos(ARCHIVO_CLIENTES)
def guardar_clientes(clientes): return guardar_datos(clientes, ARCHIVO_CLIENTES)
def agregar_o_modificar_cliente(clientes):
    print(Fore.CYAN + "\n--- Agregar/Modificar Cliente ---")
    rif = input("RIF: ").strip().upper()
    if not rif:
        print(Fore.RED + "RIF vacío."); return
    c = clientes.get(rif, {})
    n_p = c.get('nombre', '')
    d_p = c.get('direccion', '')
    t_p = c.get('telefono', '')
    n = input(f"Nombre [{n_p}]: ").strip() or n_p
    d = input(f"Dirección [{d_p}]: ").strip() or d_p
    t = input(f"Teléfono [{t_p}]: ").strip() or t_p
    if not n or not d:
        print(Fore.RED + "Nombre/Dirección obligatorios."); return
    nuevo_rif = rif
    if rif in clientes:
        cambiar_rif = input("¿Desea modificar el RIF de este cliente? (s/n): ").strip().lower()
        if cambiar_rif == 's':
            nuevo_rif = input("Nuevo RIF: ").strip().upper()
            if not nuevo_rif:
                print(Fore.RED + "Nuevo RIF vacío. No se modifica el RIF.")
                nuevo_rif = rif
            elif nuevo_rif in clientes:
                print(Fore.RED + f"El RIF {nuevo_rif} ya existe. No se modifica el RIF.")
                nuevo_rif = rif
            else:
                clientes[nuevo_rif] = {'nombre': n, 'direccion': d, 'telefono': t}
                del clientes[rif]
                if guardar_clientes(clientes):
                    print(Fore.GREEN + f"Cliente '{n}' (RIF cambiado a {nuevo_rif}) guardado/actualizado.")
                else:
                    print(Fore.RED + "Error guardando clientes.")
                return
    clientes[nuevo_rif] = {'nombre': n, 'direccion': d, 'telefono': t}
    if guardar_clientes(clientes):
        print(Fore.GREEN + f"Cliente '{n}' ({nuevo_rif}) guardado/actualizado.")
def buscar_cliente_por_rif(clientes):
    print(Fore.CYAN + "\n--- Buscar Cliente por RIF ---")
    rif = input("RIF: ").strip().upper()
    if rif in clientes:
        print(Style.BRIGHT + f"\nCliente encontrado:")
        print(f"RIF: {rif}")
        print(f"Nombre: {clientes[rif]['nombre']}")
        print(f"Teléfono: {clientes[rif].get('telefono', 'No disponible')}")
        return rif
    else:
        print(Fore.YELLOW + "Cliente no encontrado.")
        return None

def buscar_cliente_por_nombre(clientes):
    print(Fore.CYAN + "\n--- Buscar Cliente por Nombre ---")
    nombre = input("Nombre (o parte): ").strip().lower()
    encontrados = []
    for rif, datos in clientes.items():
        if nombre in datos.get('nombre', '').lower():
            encontrados.append((rif, datos))
    if encontrados:
        print(Style.BRIGHT + f"\nResultados:")
        print(f"{'RIF':<15} {'Nombre':<30} {'Teléfono':<15}")
        print("-" * 62)
        for rif, datos in encontrados:
            print(f"{rif:<15} {datos['nombre'][:30]:<30} {datos.get('telefono','')[:15]:<15}")
        print("-" * 62)
        return encontrados
    else:
        print(Fore.YELLOW + "No se encontraron clientes con ese nombre.")
        return None

def listar_clientes(clientes):
    print(Fore.CYAN + Style.BRIGHT + "\n--- Listado de Clientes Registrados ---");
    if not clientes: print(Fore.YELLOW + "No hay clientes registrados."); return
    print(Style.BRIGHT + f"{'RIF':<15} {'Nombre':<30} {'Teléfono':<15}"); print("-" * 62)
    for rif, datos in sorted(clientes.items()): n_m=datos.get('nombre','')[:30]; t_m=datos.get('telefono','')[:15]; print(f"{rif:<15} {n_m:<30} {t_m:<15}")
    print("-" * 62); print(f"Total: {len(clientes)} clientes.")
def eliminar_cliente(clientes):
    print(Fore.CYAN + "\n--- Eliminar Cliente ---"); rif=input("RIF a ELIMINAR: ").strip().upper()
    if not rif: print(Fore.YELLOW+"RIF vacío."); return
    cli=clientes.get(rif)
    if cli:
        print("\nEncontrado:"); print(Style.BRIGHT+f" RIF: {rif}"); print(f" Nom: {cli.get('nombre','N/A')}")
        print(f" Dir: {cli.get('direccion','N/A')}"); print(f" Tel: {cli.get('telefono','N/A')}")
        print(Fore.RED+Style.BRIGHT+"\n¡ADVERTENCIA! Permanente."); conf=input(f"¿SEGURO eliminar '{cli.get('nombre',rif)}'? (s/n): ").lower()
        if conf=='s':
            del clientes[rif]
            if guardar_clientes(clientes): print(Fore.GREEN+f"Cliente {rif} eliminado.")
            else: print(Fore.RED+"Error guardando clientes después de eliminar."); clientes = cargar_clientes()
        else: print("Eliminación cancelada.")
    else: print(Fore.YELLOW+f"RIF {rif} no encontrado.")
def cargar_clientes_desde_csv(clientes_actuales):
    """Carga clientes desde CSV, con mapeo flexible de columnas y fallback encoding."""
    print(Fore.CYAN + "\n--- Cargar Clientes CSV ---"); n_csv=input("Archivo CSV: ").strip()
    if not n_csv: print(Fore.YELLOW+"Cancelado."); return clientes_actuales
    if not os.path.exists(n_csv): print(Fore.RED+f"Error: '{n_csv}' no encontrado."); return clientes_actuales
    delim=input("Separador (, o ;) [;]: ").strip() or ';';
    if delim not in [',',';']: print(Fore.YELLOW+"Inválido. Usando ';'."); delim=';'
    print("\nNombres (o aprox.) de columnas en CSV:");
    col_r_usr=input("   Col RIF [RIF]: ").strip() or "RIF"
    col_n_usr=input("   Col Nombre [Nombre]: ").strip() or "Nombre"
    col_d_usr=input("   Col Dirección [Direccion]: ").strip() or "Direccion"
    col_t_usr=input("   Col Teléfono [Telefono]: ").strip() or "Telefono"
    n_cli={}; errores=[]; ln=1; file_content=None; encoding_usado=None
    try:
        try:
            with open(n_csv, mode='r', encoding='utf-8-sig', newline='') as f: file_content = f.readlines(); encoding_usado = 'utf-8-sig'
        except UnicodeDecodeError:
            print(Fore.YELLOW + "Falló UTF-8-SIG, intentando Latin-1...");
            with open(n_csv, mode='r', encoding='latin-1', newline='') as f: file_content = f.readlines(); encoding_usado = 'latin-1'
    except Exception as e_open: print(Fore.RED+f"Error abriendo CSV: {e_open}"); return clientes_actuales
    if not file_content: print(Fore.RED+"CSV vacío."); return clientes_actuales
    try:
        header_line = file_content[0].strip(); n_cols_orig = [h.strip() for h in header_line.split(delim)]
        if not n_cols_orig: print(Fore.RED+"CSV sin cabeceras?"); return clientes_actuales
        header_lookup = {h.replace(" ","").lower().lstrip('\ufeff'): h for h in n_cols_orig}
        col_map = {}; faltan = []; user_cols = { "RIF": col_r_usr, "Nombre": col_n_usr, "Direccion": col_d_usr, "Telefono": col_t_usr }
        for nl, nu in user_cols.items():
            kb = nu.replace(" ","").lower(); no = header_lookup.get(kb)
            if no: col_map[nl] = no
            else: faltan.append(nu)
        if faltan: print(Fore.RED+f"Error: No se encontraron cols: {','.join(faltan)}"); print(f"Encontradas:{n_cols_orig}"); return clientes_actuales
        print(f"Leyendo CSV (encoding: {encoding_usado})...");
        reader_data = csv.DictReader(file_content[1:], fieldnames=n_cols_orig, delimiter=delim);
        for row in reader_data:
            ln+=1; row_l = {k: str(v).strip() if v is not None else '' for k, v in row.items()}
            try:
                rif=row_l.get(col_map["RIF"],'').strip().upper();
                if not rif: errores.append(f"L:{ln}: RIF vacío."); continue
                nom=row_l.get(col_map["Nombre"],'').strip(); dire=row_l.get(col_map["Direccion"],'').strip(); tel=row_l.get(col_map["Telefono"],'').strip()
                if not nom or not dire: errores.append(f"L:{ln}({rif}): Nom/Dir vacíos."); continue
                n_cli[rif]={'nombre':nom,'direccion':dire,'telefono':tel}
            except KeyError as e: errores.append(f"L:{ln}: Error interno, col '{e}' no."); continue
            except Exception as er: errores.append(f"L:{ln}: Error procesando fila - {er}")
    except Exception as ef: print(Fore.RED+f"Error procesando CSV: {ef}"); return clientes_actuales
    if errores:
        print(Fore.YELLOW+"\nProblemas:"); [print(Fore.YELLOW+f" - {e}") for e in errores[:10]];
        if len(errores)>10: print(Fore.YELLOW+f" ... {len(errores)-10} más.")
        if input("¿Continuar? (s/n): ").lower()!='s': print("Cancelado."); return clientes_actuales
    if n_cli:
        print(f"\n{len(n_cli)} clientes leídos. Actualizando..."); clientes_actuales.update(n_cli)
        if guardar_clientes(clientes_actuales): print(Fore.GREEN+"Clientes actualizados."); return clientes_actuales
        else: print(Fore.RED+"Error guardando."); return cargar_clientes()
    else: print(Fore.YELLOW+"No se cargaron clientes."); return clientes_actuales

# --- Gestión de Inventario ---
def cargar_inventario(): return cargar_datos(ARCHIVO_INVENTARIO)
def guardar_inventario(inv): return guardar_datos(inv, ARCHIVO_INVENTARIO)
def get_producto(inv, pid): return inv.get(pid.strip().upper())
def ajustar_stock(inv, pid, cant_adj, tipo_mov):
    pid=pid.strip().upper(); prod=inv.get(pid)
    if not prod: print(Fore.RED+f"Error: ID {pid} no."); return False
    cant_act=prod.get('cantidad',0); nva_cant=cant_act+cant_adj
    if nva_cant<0 and tipo_mov != 'devolucion_eliminar': print(Fore.RED+f"Error: Stock '{prod.get('nombre',pid)}' neg ({nva_cant})."); return False
    prod['cantidad']=nva_cant; f_iso=datetime.datetime.now().isoformat()
    msg_t=""
    if tipo_mov=='entrada': prod['ultima_entrada']=f_iso; msg_t="Últ. ENTRADA."
    elif tipo_mov=='salida': prod['ultima_salida']=f_iso; msg_t="Últ. SALIDA."
    elif tipo_mov=='devolucion_eliminar': msg_t="Devolución (Elim Fac.)"
    else: msg_t="(Ajuste)."
    print(Fore.GREEN+f"Stock '{prod.get('nombre',pid)}' -> {nva_cant}. {msg_t}")
    return guardar_inventario(inv)
def agregar_o_modificar_producto(inv, pid_pre=None):
    print(Fore.CYAN+"\n--- Add/Mod Producto (USD) ---")
    if pid_pre: pid=pid_pre.strip().upper(); print(f"ID: {pid}")
    else: pid=input("ID producto: ").strip().upper()
    if not pid: print(Fore.RED+"ID vacío."); return None
    p_ex=inv.get(pid,{}); n_p=p_ex.get('nombre',''); pr_p=p_ex.get('precio',''); ca_p=p_ex.get('cantidad','')
    cat_p=p_ex.get('categoria',''); img_p=p_ex.get('ruta_imagen',''); ent_p=p_ex.get('ultima_entrada',None); sal_p=p_ex.get('ultima_salida',None)
    n=input(f"Nombre [{n_p}]: ").strip() or n_p; cat=input(f"Cat [{cat_p}]: ").strip() or cat_p; img=input(f"Imagen [{img_p}]: ").strip() or img_p
    p_usd=None
    while p_usd is None:
        p_str=input(f"Precio USD [{pr_p}]: ").strip()
        if not p_str and p_ex: p_usd=pr_p; break
        if p_str:
            p_val=None;
            try: p_val=float(p_str.replace(',','.'))
            except ValueError: print(Fore.YELLOW+"Inválido."); continue
            if p_val is not None:
                if p_val<0: print(Fore.YELLOW+"Negativo.")
                else: p_usd=p_val
        elif not p_ex: print(Fore.YELLOW+"Obligatorio.")
        else: print(Fore.RED+"Error precio."); return None
    cant_act=ca_p if p_ex else 0; cant_nva=None; f_ent_upd=ent_p; f_sal_upd=sal_p
    while cant_nva is None:
        cant_str=input(f"Cant stock [{cant_act}]: ").strip()
        if not cant_str: cant_nva=cant_act; break
        try:
            cant_val=int(cant_str);
            if cant_val<0: print(Fore.YELLOW+"Negativa."); continue
            cant_nva=cant_val
            if cant_nva>cant_act: f_ent_upd=datetime.datetime.now().isoformat(); print("(Entrada)")
            elif cant_nva<cant_act: f_sal_upd=datetime.datetime.now().isoformat(); print("(Salida)")
            break
        except ValueError: print(Fore.YELLOW+"Inválida.")
    if not n: print(Fore.RED+"Nombre obligatorio."); return None
    inv[pid]={'nombre': n,'precio': p_usd,'cantidad': cant_nva,'categoria': cat,'ruta_imagen': img,'ultima_entrada': f_ent_upd,'ultima_salida': f_sal_upd}
    if guardar_inventario(inv): print(Fore.GREEN+f"Producto '{n}' guardado."); return inv[pid]
    else: print(Fore.RED+"Error guardando."); return None
def listar_productos(inv):
    print(Fore.CYAN+"\n--- Listado Productos ---");
    if not inv: print(Fore.YELLOW+"Inv vacío."); return False
    print(Style.BRIGHT+f"{'ID':<10} {'Nombre':<20} {'Cat':<12} {'P.USD':>10} {'Cant':>5} {'Entr':>10} {'Sal':>10}"); print("-" * 85)
    for pid,p in sorted(inv.items()):
        pf=f"{p.get('precio',0):.2f}"; cat=p.get('categoria','N/A')[:12]; nom=p.get('nombre','N/A')[:20]
        try: ue=datetime.datetime.fromisoformat(p.get('ultima_entrada','')).strftime('%d/%m/%y') if p.get('ultima_entrada') else '-'
        except: ue='??/??/??'
        try: us=datetime.datetime.fromisoformat(p.get('ultima_salida','')).strftime('%d/%m/%y') if p.get('ultima_salida') else '-'
        except: us='??/??/??'
        print(f"{pid:<10} {nom:<20} {cat:<12} {pf:>10} {p.get('cantidad',0):>5} {ue:>10} {us:>10}")
    print("-" * 85); return True
def calcular_valor_inventario(inv):
    print(Fore.CYAN+"\n--- Valor Total Inventario ---");
    if not inv: print(Fore.YELLOW+"Inv vacío."); return
    v_usd=0; t_items=0
    for pid,p in inv.items():
        cant=p.get('cantidad',0);
        if cant>0: v_usd+=p.get('precio',0)*cant; t_items+=cant
    print(f"Items: {t_items}, Valor (USD): "+ Fore.GREEN+Style.BRIGHT+f"${v_usd:,.2f}")
    tasa=0
    while True:
        try:
            t_str=input(Fore.YELLOW+"Tasa Bs./USD (o vacío omitir Bs.): ").strip().replace(',','.')
            if not t_str: print("Bs. omitido."); return
            tasa=float(t_str)
            if tasa>0: break
            else: print(Fore.YELLOW+"Positiva.")
        except ValueError: print(Fore.YELLOW+"Inválida.")
    v_bs=v_usd*tasa; print(f"Valor (Bs.): "+ Fore.GREEN+Style.BRIGHT+f"Bs. {v_bs:,.2f}".replace(',','#').replace('.',',').replace('#','.'))
def eliminar_producto(inv):
    print(Fore.CYAN+"\n--- Eliminar Producto ---"); pid=input("ID a ELIMINAR: ").strip().upper()
    if not pid: print(Fore.YELLOW+"ID vacío."); return
    prod=inv.get(pid)
    if prod:
        print("\nEncontrado:"); print(Style.BRIGHT+f" ID: {pid}"); print(f" Nom: {prod.get('nombre','N/A')}")
        print(f" Cat: {prod.get('categoria','N/A')}"); print(f" P.USD: {prod.get('precio',0):.2f}"); print(f" Cant: {prod.get('cantidad',0)}")
        print(Fore.RED+Style.BRIGHT+"\n¡ADVERTENCIA! Permanente."); conf=input(f"¿SEGURO eliminar '{prod.get('nombre',pid)}'? (s/n): ").lower()
        if conf=='s':
            del inv[pid]
            if guardar_inventario(inv): print(Fore.GREEN+f"ID {pid} eliminado.")
            else: print(Fore.RED+"Error guardando inventario."); inv=cargar_inventario()
        else: print("Cancelado.")
    else: print(Fore.YELLOW+f"ID {pid} no encontrado.")

# ACTUALIZADO v3.19: Carga Inventario CSV más robusta
def cargar_inventario_desde_csv(inv_act):
    """Carga inventario desde CSV, con mapeo flexible y fallback encoding."""
    print(Fore.CYAN+"\n--- Cargar Inventario CSV ---"); n_csv=input("Archivo CSV: ").strip()
    if not n_csv: print(Fore.YELLOW+"Cancelado."); return inv_act
    if not os.path.exists(n_csv): print(Fore.RED+f"Error: '{n_csv}' no encontrado."); return inv_act
    delim=input("Separador (, o ;) [;]: ").strip() or ';';
    if delim not in [',',';']: print(Fore.YELLOW+"Inválido. Usando ';'."); delim=';'
    print("\nNombres (o aprox.) de columnas en CSV:");
    col_id_usr=input("   Col ID [ID]: ").strip() or "ID"
    col_n_usr=input("   Col Nombre [Nombre]: ").strip() or "Nombre"
    col_p_usr=input("   Col Precio USD [PrecioUSD]: ").strip() or "PrecioUSD"
    col_c_usr=input("   Col Cantidad [Cantidad]: ").strip() or "Cantidad"
    col_cat_usr=input("   Col Categoría [Categoria]: ").strip() or "Categoria"
    col_img_usr=input("   Col Imagen [Imagen]: ").strip() or "Imagen"
    n_datos={}; errores=[]; ln=1; file_content=None; encoding_usado=None
    try:
        try:
            with open(n_csv,mode='r',encoding='utf-8-sig', newline='') as f: file_content=f.readlines(); encoding_usado='utf-8-sig'
        except UnicodeDecodeError:
            print(Fore.YELLOW+"Falló UTF-8-SIG, intentando Latin-1...");
            with open(n_csv,mode='r',encoding='latin-1', newline='') as f: file_content=f.readlines(); encoding_usado='latin-1'
    except Exception as e_open: print(Fore.RED+f"Error abriendo CSV: {e_open}"); return inv_act
    if not file_content: print(Fore.RED+"CSV vacío."); return inv_act
    try:
        header_line = file_content[0].strip(); n_cols_orig = [h.strip() for h in header_line.split(delim)]
        if not n_cols_orig: print(Fore.RED+"CSV sin cabeceras?"); return inv_act
        header_lookup = {h.replace(" ","").lower().lstrip('\ufeff'): h for h in n_cols_orig}
        col_map_inv = {}; faltan_inv = []; user_cols_inv = {"ID":col_id_usr,"Nombre":col_n_usr,"PrecioUSD":col_p_usr,"Cantidad":col_c_usr,"Categoria":col_cat_usr,"Imagen":col_img_usr}
        requeridas_inv = {"ID", "Nombre", "PrecioUSD", "Cantidad"}
        for nl, nu in user_cols_inv.items():
            kb = nu.replace(" ","").lower(); no = header_lookup.get(kb)
            if no: col_map_inv[nl] = no
            elif nl in requeridas_inv: faltan_inv.append(nu)
            else: col_map_inv[nl] = None
        if faltan_inv: print(Fore.RED+f"Error: Faltan cols:{','.join(faltan_inv)}"); print(f"   Encontradas:{n_cols_orig}"); return inv_act
        print(f"Leyendo CSV (encoding: {encoding_usado})...");
        reader_data = csv.DictReader(file_content[1:], fieldnames=n_cols_orig, delimiter=delim);
        for row in reader_data:
            ln+=1; row_l={k:str(v).strip() if v is not None else '' for k,v in row.items()}
            try:
                pid=row_l.get(col_map_inv["ID"],'').strip().upper();
                if not pid: errores.append(f"L:{ln}: ID vacío."); continue
                nom=row_l.get(col_map_inv["Nombre"],'').strip()
                try: p_usd=float(row_l.get(col_map_inv["PrecioUSD"],'0').strip().replace(',','.'))
                except: p_usd=0.0; errores.append(f"L:{ln}({pid}): Precio inv->0.0")
                if p_usd<0: p_usd=0.0; errores.append(f"L:{ln}({pid}): Precio neg->0.0")
                try: cant=int(row_l.get(col_map_inv["Cantidad"],'0').strip())
                except: cant=0; errores.append(f"L:{ln}({pid}): Cant inv->0")
                if cant<0: cant=0; errores.append(f"L:{ln}({pid}): Cant neg->0")
                cat=row_l.get(col_map_inv.get("Categoria"),'').strip() if col_map_inv.get("Categoria") else ''
                img=row_l.get(col_map_inv.get("Imagen"),'').strip() if col_map_inv.get("Imagen") else ''
                ent_p=inv_act.get(pid,{}).get('ultima_entrada',None); sal_p=inv_act.get(pid,{}).get('ultima_salida',None)
                n_datos[pid]={'nombre':nom,'precio':p_usd,'cantidad':cant,'categoria':cat,'ruta_imagen':img,'ultima_entrada':ent_p,'ultima_salida':sal_p}
            except KeyError as e: errores.append(f"L:{ln}: Error interno, col '{e}' no."); continue
            except Exception as er: errores.append(f"L:{ln}: Error procesando fila - {er}")
    except Exception as ef: print(Fore.RED+f"Error procesando CSV: {ef}"); return inv_act
    if errores:
        print(Fore.YELLOW+"\nProblemas:"); [print(Fore.YELLOW+f" - {e}") for e in errores[:10]];
        if len(errores)>10: print(Fore.YELLOW+f" ... {len(errores)-10} más.")
        if input("¿Continuar? (s/n): ").lower()!='s': print("Cancelado."); return inv_act
    if n_datos:
        print(f"\n{len(n_datos)} productos leídos. Actualizando..."); inv_act.update(n_datos)
        if guardar_inventario(inv_act): print(Fore.GREEN+"Inventario actualizado."); return inv_act
        else: print(Fore.RED+"Error guardando."); return cargar_inventario()
    else: print(Fore.YELLOW+"No se cargaron datos válidos."); return inv_act

# --- Gestión Cuentas por Cobrar ---
# ... (cargar_cuentas_cobrar, guardar_cuentas_cobrar, cargar_cuentas_desde_csv, ver_estado_cuentas, registrar_abono sin cambios) ...
def cargar_cuentas_cobrar(): return cargar_datos(ARCHIVO_CUENTAS_COBRAR)
def guardar_cuentas_cobrar(cuentas): return guardar_datos(cuentas, ARCHIVO_CUENTAS_COBRAR)
def cargar_cuentas_desde_csv(cuentas_actuales):
    print(Fore.CYAN + "\n--- Cargar Estado de Cuentas desde CSV ---")
    nombre_csv = input("Nombre archivo CSV registro ventas: ").strip()
    if not nombre_csv: print(Fore.YELLOW + "Cancelado."); return cuentas_actuales
    if not os.path.exists(nombre_csv): print(Fore.RED + f"Error: '{nombre_csv}' no encontrado."); return cuentas_actuales
    delim = ';'; col_num_fact = "NRO.FACTURA"; col_rif = "RIF"; col_total_usd = "TOTAL  USD"; col_abonado = "ABONADO"; col_estado_csv_hdr = "TOTAL ESTADO"
    print(Fore.YELLOW + f"\nUsando columnas FIJAS: Nro='{col_num_fact}', RIF='{col_rif}', TotalUSD='{col_total_usd}', Abonado='{col_abonado}', EstadoCSV='{col_estado_csv_hdr}'")
    print(Fore.RED + f"ADVERTENCIA: Columna '{col_estado_csv_hdr}' se IGNORA para el estado, se CALCULA de montos.")
    nuevas_cuentas = {}; errores = []; linea_num = 1; procesados = 0
    file_content = None; encoding_usado = 'utf-8-sig'
    try:
        try:
            with open(nombre_csv, mode='r', encoding=encoding_usado, newline='') as fcsv: file_content = fcsv.readlines()
        except UnicodeDecodeError:
            encoding_usado = 'latin-1'; print(Fore.YELLOW + f"Falló {encoding_usado}, intentando {encoding_usado}...");
            with open(nombre_csv, mode='r', encoding=encoding_usado, newline='') as fcsv: file_content = fcsv.readlines()
    except Exception as e_open: print(Fore.RED + f"Error abriendo archivo '{nombre_csv}': {e_open}"); return cuentas_actuales
    if not file_content: print(Fore.RED + "Archivo CSV vacío."); return cuentas_actuales
    try:
        header_line = file_content[0].strip(); n_cols_orig = [h.strip() for h in header_line.split(delim)]
        if not n_cols_orig: print(Fore.RED+"CSV sin cabeceras?"); return cuentas_actuales
        if n_cols_orig[0].startswith('\ufeff'): n_cols_orig[0] = n_cols_orig[0][1:]
        columnas_requeridas_fijas = {col_num_fact.lstrip('\ufeff'), col_rif, col_total_usd, col_abonado, col_estado_csv_hdr}; columnas_encontradas_set = set(n_cols_orig)
        if not columnas_requeridas_fijas.issubset(columnas_encontradas_set):
            faltan = columnas_requeridas_fijas - columnas_encontradas_set
            print(Fore.RED+f"Error: Columnas requeridas no encontradas: {', '.join(faltan)}"); print(f"   Encontradas: {n_cols_orig}"); return cuentas_actuales
        print(f"Leyendo CSV (encoding: {encoding_usado})...");
        reader_data = csv.DictReader(file_content[1:], fieldnames=n_cols_orig, delimiter=delim);
        for row in reader_data:
            linea_num += 1
            try:
                num_fact_str = row.get(col_num_fact.lstrip('\ufeff'), '').strip()
                try: int(num_fact_str); num_fact = f"{int(num_fact_str):04d}"
                except ValueError: errores.append(f"L:{linea_num}: Nro Factura '{num_fact_str}' inválido."); continue
                rif_cli = row.get(col_rif, '').strip().upper()
                try: total_usd = float(row.get(col_total_usd, '0').strip().replace(',','.'))
                except: total_usd = 0.0; errores.append(f"L:{linea_num}({num_fact}): TotalUSD inv->0.0")
                if total_usd < 0: total_usd = 0.0; errores.append(f"L:{linea_num}({num_fact}): TotalUSD neg->0.0")
                abonado_str = row.get(col_abonado, '0').strip()
                try: abonado_usd = float(abonado_str.replace(',','.')) if abonado_str else 0.0
                except: abonado_usd = 0.0; errores.append(f"L:{linea_num}({num_fact}): Abonado inv->0.0")
                if abonado_usd < 0: abonado_usd = 0.0; errores.append(f"L:{linea_num}({num_fact}): Abonado neg->0.0")
                if total_usd > 0:
                     if abs(abonado_usd - total_usd) < 0.01: estado_calculado = "Cobrada"
                     elif abonado_usd > 0: estado_calculado = "Abonada"
                     else: estado_calculado = "Por Cobrar"
                else: estado_calculado = "Cobrada"; abonado_usd = 0.0; total_usd = 0.0
                nuevas_cuentas[num_fact]={'rif': rif_cli,'total_usd': total_usd,'abonado_usd': abonado_usd,'estado': estado_calculado}
                procesados += 1
            except KeyError as e: errores.append(f"L:{linea_num}: Columna FIJA '{e}' no."); continue
            except Exception as er: errores.append(f"L:{linea_num}: Error procesando fila - {er}")
    except Exception as ef: print(Fore.RED+f"Error procesando CSV: {ef}"); return cuentas_actuales
    if errores:
        print(Fore.YELLOW+"\nProblemas/Ajustes:"); [print(Fore.YELLOW+f" - {e}") for e in errores[:15]];
        if len(errores)>15: print(Fore.YELLOW+f" ... {len(errores)-15} más.")
    if nuevas_cuentas:
        print(f"\n{procesados} regs leídos. Actualizando CxC...");
        cuentas_actuales = nuevas_cuentas
        if guardar_cuentas_cobrar(cuentas_actuales): print(Fore.GREEN+"CxC actualizadas."); return cuentas_actuales
        else: print(Fore.RED+"Error guardando CxC."); return cargar_cuentas_cobrar()
    else: print(Fore.YELLOW+"No se cargaron datos válidos."); return cuentas_actuales
def ver_estado_cuentas(cuentas_cobrar, clientes):
    print(Fore.CYAN + Style.BRIGHT + "\n=== CUENTAS POR COBRAR ===")
    print("-" * 80)
    print(f"{'Nro Fact':<10} {'Cliente':<25} {'Total USD':>12} {'Pendiente USD':>12}")
    print("-" * 80)
    
    hay_pendientes = False
    total_facturado_pend = 0
    total_abonado_pend = 0
    total_pendiente_pend = 0
    
    for num_fact, datos in sorted(cuentas_cobrar.items()):
        estado = datos.get('estado', '').lower()
        total = datos.get('total_usd', 0)
        abonado = datos.get('abonado_usd', 0)
        pendiente = max(0, total - abonado)
        
        # Solo mostrar si está pendiente o abonada con saldo pendiente
        if estado in ['por cobrar', 'abonada'] and pendiente > 0.01:
            hay_pendientes = True
            rif = datos.get('rif', 'N/A')
            cliente_nombre = clientes.get(rif, {}).get('nombre', 'N/A')[:25]
            print(f"{num_fact:<10} {cliente_nombre:<25} {total:>12,.2f} {pendiente:>12,.2f}")
            
            # Acumular totales
            total_facturado_pend += total
            total_abonado_pend += abonado
            total_pendiente_pend += pendiente
    
    if not hay_pendientes:
        print(Fore.GREEN + "\nNo hay cuentas pendientes por cobrar.")
        print("-" * 80)
    else:
        print("-" * 80)
        print(Style.BRIGHT + f"{'TOTALES PENDIENTES:':<51} {total_facturado_pend:>10,.2f} {total_abonado_pend:>12,.2f} {total_pendiente_pend:>14,.2f}")
        print("-" * 105)
def registrar_abono(cuentas_cobrar):
    print(Fore.CYAN + "\n=== Registrar Pago ===")
    
    # Mostrar cuentas pendientes
    print("\nCuentas pendientes:")
    print("-" * 80)
    print(f"{'Nro Fact':<10} {'Cliente':<25} {'Total USD':>12} {'Pendiente USD':>12}")
    print("-" * 80)
    
    for num_fact, datos in cuentas_cobrar.items():
        if datos.get('estado', '').lower() in ['por cobrar', 'abonada']:
            total = datos.get('total_usd', 0)
            abonado = datos.get('abonado_usd', 0)
            pendiente = max(0, total - abonado)
            cliente_nombre = datos.get('nombre_cliente', 'N/A')[:25]
            print(f"{num_fact:<10} {cliente_nombre:<25} {total:>12,.2f} {pendiente:>12,.2f}")
    print("-" * 80)
    
    num_fact = input(Fore.YELLOW + "\nIngrese el número de factura: " + Style.RESET_ALL)
    if num_fact not in cuentas_cobrar:
        print(Fore.RED + "Factura no encontrada.")
        return
    
    datos = cuentas_cobrar[num_fact]
    if datos.get('estado', '').lower() == 'cobrada':
        print(Fore.YELLOW + "Esta factura ya está cobrada.")
        return
    
    total = datos.get('total_usd', 0)
    abonado = datos.get('abonado_usd', 0)
    pendiente = max(0, total - abonado)
    
    print(f"\nDetalles de la factura:")
    print(f"Total: ${total:,.2f}")
    print(f"Abonado: ${abonado:,.2f}")
    print(f"Pendiente: ${pendiente:,.2f}")
    
    try:
        monto = float(input(Fore.YELLOW + "\nIngrese el monto a abonar (USD): " + Style.RESET_ALL))
        if monto <= 0:
            print(Fore.RED + "El monto debe ser mayor a 0.")
            return
        if monto > pendiente:
            print(Fore.RED + "El monto excede el saldo pendiente.")
            return
    except ValueError:
        print(Fore.RED + "Monto inválido.")
        return
    
    # Seleccionar método de pago
    print("\nMétodos de pago disponibles:")
    print("1. Efectivo (Bs)")
    print("2. Efectivo (USD)")
    print("3. Transferencia")
    print("4. Pago móvil")
    
    while True:
        metodo = input(Fore.YELLOW + "\nSeleccione el método de pago (1-4): " + Style.RESET_ALL)
        if metodo in ['1', '2', '3', '4']:
            break
        print(Fore.RED + "Opción inválida. Por favor seleccione 1-4.")
    
    # Mapear selección a método de pago
    metodos = {
        '1': 'Efectivo (Bs)',
        '2': 'Efectivo (USD)',
        '3': 'Transferencia',
        '4': 'Pago móvil'
    }
    metodo_pago = metodos[metodo]
    
    # Solicitar número de referencia si aplica
    referencia = None
    if metodo in ['3', '4']:  # Transferencia o Pago móvil
        referencia = input(Fore.YELLOW + "Ingrese el número de referencia: " + Style.RESET_ALL)
    
    # Obtener fecha y hora actual
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # Actualizar datos
    nuevo_abonado = abonado + monto
    # Actualizar estado basado en el nuevo monto abonado
    if abs(nuevo_abonado - total) < 0.01:  # Usar una pequeña tolerancia para comparaciones de punto flotante
        nuevo_estado = "Cobrada"
    else:
        nuevo_estado = "Abonada"
    
    datos['abonado_usd'] = nuevo_abonado
    datos['estado'] = nuevo_estado
    datos['tipo_pago'] = metodo_pago
    datos['fecha_ultimo_abono'] = fecha_actual
    if referencia:
        datos['referencia_pago'] = referencia
    
    # Guardar cambios
    guardar_cuentas_cobrar(cuentas_cobrar)
    
    print(Fore.GREEN + f"\nPago registrado exitosamente.")
    print(f"Nuevo estado: {nuevo_estado}")
    print(f"Total abonado: ${nuevo_abonado:,.2f}")
    print(f"Saldo pendiente: ${max(0, total - nuevo_abonado):,.2f}")
    print(f"Método de pago: {metodo_pago}")
    print(f"Fecha del pago: {fecha_actual}")
    if referencia:
        print(f"Número de referencia: {referencia}")

# --- Funciones de Configuración ---
def cargar_configuracion(): config = cargar_datos(ARCHIVO_CONFIG); config.setdefault('proximo_numero_factura', 1); return config
def guardar_configuracion(config): guardar_datos(config, ARCHIVO_CONFIG)
def obtener_siguiente_numero_factura(config):
    numero = config.get('proximo_numero_factura', 1); config['proximo_numero_factura'] = numero + 1
    guardar_configuracion(config); return f"{numero:04d}"

# --- FUNCIÓN PARA CARGAR HISTORIAL ---
def cargar_todas_las_facturas():
    historial_facturas = []
    if not os.path.exists(CARPETA_FACTURAS_JSON) or not os.path.isdir(CARPETA_FACTURAS_JSON): print(Fore.YELLOW + f"Adv: Carpeta '{CARPETA_FACTURAS_JSON}' no existe."); return []
    print(Fore.BLUE + f"Leyendo historial desde '{CARPETA_FACTURAS_JSON}'...")
    archivos_json = []
    try: archivos_json = [f for f in os.listdir(CARPETA_FACTURAS_JSON) if f.endswith('.json') and os.path.isfile(os.path.join(CARPETA_FACTURAS_JSON, f))]
    except Exception as e: print(Fore.RED + f"Error listando '{CARPETA_FACTURAS_JSON}': {e}"); return []
    print(f"Se encontraron {len(archivos_json)} archivos JSON.")
    facturas_cargadas = 0
    for nombre_archivo in archivos_json:
        ruta_completa = os.path.join(CARPETA_FACTURAS_JSON, nombre_archivo)
        factura_data = cargar_datos(ruta_completa)
        if isinstance(factura_data, dict) and all(k in factura_data for k in ['numero_factura', 'cliente', 'items', 'total_bs', 'total_usd', 'fecha']) and \
           'rif' in factura_data['cliente'] and isinstance(factura_data['items'], list):
               historial_facturas.append(factura_data); facturas_cargadas += 1
        elif isinstance(factura_data, dict): print(Fore.YELLOW + f"Adv: '{nombre_archivo}' omitido (claves inválidas).")
    print(Fore.GREEN + f"Se cargaron datos de {facturas_cargadas} facturas válidas.")
    try: historial_facturas.sort(key=lambda x: int(x.get('numero_factura', 0)))
    except ValueError: print(Fore.YELLOW + "Adv: No se pudo ordenar facturas."); historial_facturas.sort(key=lambda x: x.get('numero_factura', '0'))
    return historial_facturas

# --- Generación de PDF Factura ---
# ACTUALIZADO v3.20: Subtotal USD en tabla, Fecha pago
def generar_pdf_factura(factura_data, nombre_archivo_pdf):
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        # --- Logo centrado en la parte superior ---
        logo_w = 32
        logo_h = 32
        logo_x = (210 - logo_w) / 2  # Centrado en A4 (210mm de ancho)
        logo_y = 10
        try:
            if os.path.exists(ARCHIVO_LOGO):
                pdf.image(ARCHIVO_LOGO, x=logo_x, y=logo_y, w=logo_w, h=logo_h)
        except Exception as e_logo:
            print(f"Adv: Error al cargar el logo: {e_logo}")
        # Espacio debajo del logo
        pdf.set_y(logo_y + logo_h + 2)
        def to_latin1(t):
            txt = str(t) if t is not None else ''
            return txt.encode('latin-1','replace').decode('latin-1')
        # --- Datos de la empresa centrados ---
        pdf.set_font('Arial','B',14)
        pdf.set_text_color(0,0,128)
        pdf.cell(0,8,to_latin1(NOMBRE_EMPRESA),0,1,'C')
        pdf.set_font('Arial','',10)
        pdf.set_text_color(0,0,0)
        pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C')
        pdf.cell(0,5,f"Teléfono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C')
        pdf.cell(0,5,"Centro Comercial Caña de Azucar (Antiguo Merbumar), Nave A, Locales 154-156-Maracay-Edo.Aragua",0,1,'C')
        pdf.ln(2)
        pdf.set_font('Arial','B',16)
        pdf.set_text_color(0,0,128)
        pdf.cell(0,10,'FACTURA',0,1,'C')
        pdf.set_text_color(0,0,0)
        pdf.ln(2)
        # --- Datos Factura (esquina superior derecha) ---
        pdf.set_font('Arial','B',10)
        num_f = factura_data.get('numero_factura','N/A')
        fecha_iso = factura_data.get('fecha','N/A')
        try:
            fecha_dt = datetime.datetime.fromisoformat(fecha_iso)
            fecha_legible = fecha_dt.strftime('%d/%m/%Y %H:%M:%S')
        except Exception:
            fecha_legible = fecha_iso
        condicion = factura_data.get('condicion_pago', 'Contado')
        dias_cred = factura_data.get('dias_credito', 0)
        if condicion.lower() == 'credito' and dias_cred > 0:
            cond_texto = f"CRÉDITO ({dias_cred} días)"
        else:
            cond_texto = f"{condicion.upper()}"
        # Guardar posición actual para datos cliente
        y_datos = pdf.get_y()
        # Datos de factura a la derecha
        pdf.set_xy(130, 18)  # Más arriba y a la derecha
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Nro. Factura:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,num_f,0,1,'L')
        pdf.set_x(130)
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Fecha Emisión:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,fecha_legible,0,1,'L')
        pdf.set_x(130)
        pdf.set_font('Arial','B',10)
        pdf.cell(40,6,"Condición:",0,0,'R')
        pdf.set_font('Arial','',10)
        pdf.cell(30,6,cond_texto,0,1,'L')
        # Si es crédito, mostrar fecha de pago debajo de condición
        if condicion.lower() == 'credito' and dias_cred > 0:
            try:
                fecha_pago = (fecha_dt + datetime.timedelta(days=dias_cred)).strftime('%d/%m/%Y')
            except Exception:
                fecha_pago = 'N/A'
            pdf.set_x(130)
            pdf.set_font('Arial','B',10)
            pdf.cell(40,6,"Fecha a Pagar:",0,0,'R')
            pdf.set_font('Arial','',10)
            pdf.cell(30,6,fecha_pago,0,1,'L')
        # --- Datos Cliente (a la izquierda, bajo el logo) ---
        cli = factura_data.get('cliente',{})
        pdf.set_xy(10, y_datos + 2)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Cliente RIF:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('rif','')),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Nombre:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('nombre','')),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Dirección:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('direccion','')),0,1,'L')
        pdf.set_x(10)
        pdf.set_font('Arial','B',10)
        pdf.cell(30,6,"Teléfono:",0,0,'L')
        pdf.set_font('Arial','',10)
        pdf.cell(60,6,to_latin1(cli.get('telefono','')),0,1,'L')
        pdf.ln(5)
        # --- Tabla de Productos con P. Unit Bs y Subtotal Bs ---
        pdf.set_font('Arial','B',9)
        pdf.set_fill_color(240,240,240)
        pdf.set_draw_color(100,100,100)
        # Ajustar anchos de columna para aprovechar mejor el espacio
        c_w = [20, 60, 15, 25, 25, 25, 25]  # Ajustados para 7 columnas
        headers = ['Código', 'Descripción', 'Cantidad', 'P. Unit USD', 'P. Unit Bs', 'Subtotal USD', 'Subtotal Bs']
        for i, h in enumerate(headers):
            pdf.cell(c_w[i], 7, h, 1, 0, 'C', fill=True)
        pdf.ln()
        pdf.set_font('Arial','',8)
        items = factura_data.get('items',[])
        tasa = factura_data.get('tasa_cambio', 0)
        for item in items:
            codigo = to_latin1(item.get('id',''))
            desc = to_latin1(item.get('nombre',''))
            cant = item.get('cantidad',0)
            pu_usd = item.get('precio_unitario_usd',0)
            pu_bs = pu_usd * tasa
            subtotal_usd = cant * pu_usd
            subtotal_bs = cant * pu_bs
            pdf.set_fill_color(255,255,255)
            pdf.cell(c_w[0], 6, str(codigo), 1, 0, 'C')
            pdf.cell(c_w[1], 6, desc, 1, 0, 'L')
            pdf.cell(c_w[2], 6, str(cant), 1, 0, 'C')
            pdf.cell(c_w[3], 6, f"${pu_usd:,.2f}", 1, 0, 'R')
            pdf.cell(c_w[4], 6, f"{pu_bs:,.2f} Bs", 1, 0, 'R')
            pdf.cell(c_w[5], 6, f"${subtotal_usd:,.2f}", 1, 0, 'R')
            pdf.cell(c_w[6], 6, f"{subtotal_bs:,.2f} Bs", 1, 1, 'R')
        pdf.ln(5)
        # --- Bloque de Totales (alineados a la derecha de la hoja) ---
        sub_bs = factura_data.get('subtotal_bs',0)
        iva_bs = factura_data.get('iva_bs',0)
        desc_bs = factura_data.get('descuento_bs',0)
        tot_bs = factura_data.get('total_bs',0)
        sub_usd = factura_data.get('subtotal_usd',0)
        iva_usd = factura_data.get('iva_usd',0)
        desc_usd = factura_data.get('descuento_usd',0)
        tot_usd = factura_data.get('total_usd',0)
        def fmt(val):
            return f"{abs(val):,.2f}"
        w_label = 50  # Espacio para el texto
        w_val = 40    # Espacio para el valor
        # Posición X: completamente a la derecha de la hoja
        x_totales = pdf.w - pdf.r_margin - (w_label + w_val)
        pdf.set_font('Arial','',10)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'SUBTOTAL BS:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(sub_bs)} Bs",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'IVA:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(iva_bs)} Bs",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'DESCUENTO:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(desc_bs)} Bs",0,1,'R')
        pdf.set_font('Arial','B',11)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'TOTAL BS:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(tot_bs)} Bs",0,1,'R')
        pdf.ln(2)
        pdf.set_font('Arial','',10)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'SUBTOTAL USD:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(sub_usd)} $",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'IVA:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(iva_usd)} $",0,1,'R')
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'DESCUENTO:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(desc_usd)} $",0,1,'R')
        pdf.set_font('Arial','B',11)
        pdf.set_x(x_totales)
        pdf.cell(w_label,6,'TOTAL USD:',0,0,'R'); pdf.cell(w_val,6,f"{fmt(tot_usd)} $",0,1,'R')
        pdf.ln(10)
        # --- Pie de Página centrado y tasa en negro ---
        tasa = factura_data.get('tasa_cambio', 0)
        # Pie de página en cursiva y negrita
        pdf.set_font('Arial','BI',9)
        pdf.set_text_color(0,0,0)
        pie_1 = "El documento es calculado a la tasa de cambio BCV vigente a la fecha de emisión en Bolívares. Si la factura no es pagada de contado, deberá ser cancelada al valor de la tasa activa bancaria publicada por el BCV para la fecha de pago de la factura, siempre referido por su fecha de emisión."
        pdf.set_x(10)
        pdf.set_y(pdf.get_y()+5)
        pdf.multi_cell(0,6,pie_1,0,'J')
        pdf.set_font('Arial','B',9)
        pdf.set_x(0)
        pdf.cell(0,6,f"Tasa de cambio utilizada: {tasa:.2f} Bs/USD",0,1,'C')
        os.makedirs(os.path.dirname(nombre_archivo_pdf), exist_ok=True)
        pdf.output(nombre_archivo_pdf)
        print(Fore.GREEN + f"Factura PDF: '{nombre_archivo_pdf}'")
        return True
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF FACTURA ---")
        print(Fore.RED + f"Error: {type(e).__name__} - {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")
        if os.path.exists(nombre_archivo_pdf):
            print(f"Eliminando PDF fallido: {nombre_archivo_pdf}")
            try:
                os.remove(nombre_archivo_pdf)
                print("Eliminado.")
            except OSError as err:
                print(Fore.YELLOW + f"Adv: No se pudo: {err}")
            except Exception as e_del:
                print(Fore.YELLOW + f"Adv: Error inesperado: {e_del}")
        return False

# --- Generación de PDF Inventario ---
# ... (sin cambios) ...
def generar_pdf_inventario(inventario):
    print(Fore.CYAN + "\n--- Generando PDF Inventario con QR ---");
    if not inventario: print(Fore.YELLOW + "Inv vacío."); return
    if qrcode is None: print(Fore.RED + "Error: 'qrcode' no instalado."); return
    tasa=0
    while True:
        try:
            t_str=input(Fore.YELLOW + "Tasa Bs./USD para valor PDF (o vacío omitir Bs.): ").strip().replace(',','.')
            if not t_str: print("Se omitirá valor Bs."); break
            tasa=float(t_str)
            if tasa > 0: break
            else: print(Fore.YELLOW + "Tasa positiva.")
        except ValueError: print(Fore.YELLOW + "Tasa inválida.")
    try:
        pdf=FPDF(orientation='L',unit='mm',format='A4'); pdf.add_page()
        try:
            if os.path.exists(ARCHIVO_LOGO): pdf.image(ARCHIVO_LOGO,x=10,y=8,w=30)
            else: print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
            pdf.set_xy(45,10)
        except Exception: pdf.set_xy(10,10)
        def to_latin1(t): txt=str(t) if t is not None else ''; return txt.encode('latin-1','replace').decode('latin-1')
        pdf.set_font('Arial','B',12); pdf.cell(0,6,to_latin1(NOMBRE_EMPRESA),0,1,'C'); pdf.set_xy(45,pdf.get_y()); pdf.set_font('Arial','',10); pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C'); pdf.ln(5)
        pdf.set_font('Arial','B',14); f_rep=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'); pdf.cell(0,10,f"Listado Inventario - {f_rep}",0,1,'C'); pdf.ln(5)
        pdf.set_font('Arial','B',8); pdf.set_fill_color(220,220,220); pdf.set_draw_color(50,50,50); c_w={'id':20,'nom':60,'cat':30,'pre':20,'cant':15,'entr':18,'sal':18,'qr':25}; hdr=['ID','Nombre','Cat','P.USD','Cant','Ult.Ent','Ult.Sal','QR']
        t_w=sum(c_w.values()); sx=(pdf.w-t_w)/2; pdf.set_x(sx)
        for i,cn in enumerate(hdr): pdf.cell(list(c_w.values())[i],6,cn,1,0 if i<len(hdr)-1 else 1,'C',fill=True)
        pdf.set_font('Arial','',7); r_h=22; qr_s=20; qr_p=(r_h-qr_s)/2
        for pid,p in sorted(inventario.items()):
            y_b=pdf.get_y();
            if y_b+r_h>pdf.h-pdf.b_margin:
                 pdf.add_page(); pdf.set_font('Arial','B',8); pdf.set_fill_color(220,220,220); pdf.set_x(sx)
                 for i,cn in enumerate(hdr): pdf.cell(list(c_w.values())[i],6,cn,1,0 if i<len(hdr)-1 else 1,'C',fill=True)
                 pdf.set_font('Arial','',7); y_b=pdf.get_y()
            pdf.set_x(sx)
            n_q=p.get('nombre','N/A'); c_q=p.get('categoria','N/A'); p_q=p.get('precio',0); qr_d=f"ID:{pid}\nNom:{n_q}\nCat:{c_q}\nPrecio:${p_q:.2f} USD"; qr_gen=False
            try: qr_img=qrcode.make(qr_d); qr_img.save(ARCHIVO_TEMP_QR); qr_gen=True
            except Exception as e_qr: print(Fore.RED + f"Err QR {pid}:{e_qr}")
            id_t=to_latin1(pid); n_t=to_latin1(n_q); c_t=to_latin1(c_q); p_t=f"{p_q:.2f}"; cant_t=str(p.get('cantidad',0)); ue_s=p.get('ultima_entrada'); us_s=p.get('ultima_salida')
            try: ue=datetime.datetime.fromisoformat(ue_s).strftime('%d/%m/%y') if ue_s else '-'
            except: ue='??/??/??'
            try: us=datetime.datetime.fromisoformat(us_s).strftime('%d/%m/%y') if us_s else '-'
            except: us='??/??/??'
            cx=sx; pdf.multi_cell(c_w['id'],r_h,id_t,1,'L',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['id']
            pdf.set_x(cx); pdf.multi_cell(c_w['nom'],r_h,n_t,1,'L',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['nom']
            pdf.set_x(cx); pdf.multi_cell(c_w['cat'],r_h,c_t,1,'L',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['cat']
            pdf.set_x(cx); pdf.multi_cell(c_w['pre'],r_h,p_t,1,'R',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['pre']
            pdf.set_x(cx); pdf.multi_cell(c_w['cant'],r_h,cant_t,1,'C',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['cant']
            pdf.set_x(cx); pdf.multi_cell(c_w['entr'],r_h,ue,1,'C',new_x=XPos.RIGHT,new_y=YPos.TOP); pdf.set_y(y_b); cx+=c_w['entr']
            pdf.set_x(cx); pdf.multi_cell(c_w['sal'],r_h,us,1,'C',new_x=XPos.RIGHT,new_y=YPos.TOP)
            x_qr=cx+c_w['sal']; pdf.set_xy(x_qr,y_b); pdf.cell(c_w['qr'],r_h,"",1,1)
            if qr_gen and os.path.exists(ARCHIVO_TEMP_QR):
                 img_x=x_qr+(c_w['qr']-qr_s)/2; img_y=y_b+qr_p
                 try: pdf.image(ARCHIVO_TEMP_QR,x=img_x,y=img_y,w=qr_s,h=qr_s)
                 except Exception as e_qr_img: print(Fore.RED + f"Err img QR {pid}: {e_qr_img}")
            pdf.set_y(y_b+r_h)
        pdf.ln(5); v_usd=sum(p.get('precio',0)*p.get('cantidad',0) for p in inventario.values() if p.get('cantidad',0)>0); t_items=sum(p.get('cantidad',0) for p in inventario.values() if p.get('cantidad',0)>0)
        pdf.set_font('Arial','B',10); pdf.cell(0,6,f"Total Items: {t_items}",0,1,'R'); pdf.cell(0,6,f"Valor Total (USD): ${v_usd:,.2f}",0,1,'R')
        if tasa>0: v_bs=v_usd*tasa; pdf.cell(0,6,f"Valor Total (Bs. @{tasa:,.2f}): Bs. {v_bs:,.2f}".replace(',','#').replace('.',',').replace('#','.'),0,1,'R')
        os.makedirs(CARPETA_LISTAS_INVENTARIO, exist_ok=True); pdf_fname=os.path.join(CARPETA_LISTAS_INVENTARIO,f"inventario_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        pdf.output(pdf_fname); print(Fore.GREEN + f"PDF inventario: '{pdf_fname}'"); return True
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF INVENTARIO ---"); print(f"Error: {type(e).__name__} - {e}"); print("--- Traceback ---"); traceback.print_exc(); print("--- Fin Traceback ---"); return False
    finally:
        if os.path.exists(ARCHIVO_TEMP_QR):
            try: os.remove(ARCHIVO_TEMP_QR)
            except OSError as err_del: print(Fore.YELLOW + f"Adv: No se pudo eliminar QR temp: {err_del}")
            except Exception as e_del: print(Fore.YELLOW + f"Adv: Error inesperado eliminando QR temp: {e_del}")

# --- Generación de PDF Historial Cliente ---
# ... (sin cambios) ...
def generar_pdf_historial_cliente(clientes, historial_completo):
    print(Fore.CYAN + "\n--- Generar PDF Historial de Cliente ---")
    rif_buscar = input("Ingrese RIF del cliente: ").strip().upper()
    cliente_info = clientes.get(rif_buscar)
    if not cliente_info: print(Fore.YELLOW + f"Cliente RIF {rif_buscar} no encontrado."); return
    facturas_cliente = [f for f in historial_completo if f.get('cliente', {}).get('rif') == rif_buscar]
    if not facturas_cliente: print(Fore.YELLOW + f"No hay facturas para {cliente_info.get('nombre', rif_buscar)}."); return
    tasa_reporte=0
    while True:
        try:
            t_str=input(Fore.YELLOW + "Tasa Bs./USD para resumen PDF (o vacío omitir Bs.): ").strip().replace(',','.')
            if not t_str: print("Se omitirá valor Bs. equivalente."); break
            tasa_reporte=float(t_str)
            if tasa_reporte > 0: break
            else: print(Fore.YELLOW + "Tasa positiva.")
        except ValueError: print(Fore.YELLOW + "Tasa inválida.")
    print(f"Generando historial para: {cliente_info.get('nombre', rif_buscar)} ({len(facturas_cliente)} facturas)")
    total_gastado_bs_hist = 0; total_gastado_usd = 0; productos_comprados = Counter()
    inventario_actual = cargar_inventario()
    for f in facturas_cliente:
        if f.get('cliente',{}).get('rif') in clientes:
            total_gastado_bs_hist += f.get('total_bs', 0); total_gastado_usd += f.get('total_usd', 0)
            for item in f.get('items', []):
                pid = item.get('id'); cant = item.get('cantidad', 0)
                if pid and cant > 0 and pid in inventario_actual: productos_comprados[pid] += cant
    prod_top = "-";
    if productos_comprados:
        p_mas_comunes = productos_comprados.most_common()
        if p_mas_comunes:
            max_c = p_mas_comunes[0][1]; p_top_ids = [pid for pid, c in p_mas_comunes if c == max_c and c > 0]
            if p_top_ids: n_top = [inventario_actual.get(pid, {}).get('nombre', pid) for pid in p_top_ids]; prod_top = ", ".join(n_top) + f" ({max_c} uds)"
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
        try: # Header
            if os.path.exists(ARCHIVO_LOGO): pdf.image(ARCHIVO_LOGO, x=10, y=8, w=30)
            else: print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
            pdf.set_xy(45, 10)
        except Exception: pdf.set_xy(10, 10)
        def to_latin1(t): txt=str(t) if t is not None else ''; return txt.encode('latin-1','replace').decode('latin-1')
        pdf.set_font('Arial','B',11); pdf.cell(0,5,to_latin1(NOMBRE_EMPRESA),0,1,'C'); pdf.set_font('Arial','',9); pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C'); pdf.cell(0,5,f"Telefono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C'); pdf.ln(8)
        pdf.set_font('Arial','B',14); pdf.cell(0,10,f"Historial de Cliente",0,1,'C'); pdf.ln(5)
        pdf.set_font('Arial','B',10); pdf.cell(30, 5, "Cliente RIF:", 0, 0, 'L'); pdf.set_font('Arial','',10); pdf.cell(0, 5, to_latin1(rif_buscar), 0, 1, 'L')
        pdf.set_font('Arial','B',10); pdf.cell(30, 5, "Nombre:", 0, 0, 'L'); pdf.set_font('Arial','',10); pdf.multi_cell(0, 5, to_latin1(cliente_info.get('nombre')), 0, 'L')
        pdf.ln(5)
        pdf.set_font('Arial','B',10); pdf.cell(0, 6, "Resumen General:", 0, 1, 'L'); pdf.set_font('Arial','',10)
        pdf.cell(0, 5, f"  - Total Facturas: {len(facturas_cliente)}", 0, 1, 'L');
        pdf.cell(0, 5, f"  - Total Comprado (USD): ${total_gastado_usd:,.2f}", 0, 1, 'L')
        if tasa_reporte > 0:
            total_eq_bs = total_gastado_usd * tasa_reporte
            pdf.cell(0, 5, f"  - Total Comprado (Bs. Eq. @{tasa_reporte:.2f}): {total_eq_bs:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), 0, 1, 'L')
        pdf.cell(0, 5, f"  - Producto(s) Más Comprado(s) (Activos): {to_latin1(prod_top)}", 0, 1, 'L'); pdf.ln(8)
        pdf.set_font('Arial','B',10); pdf.cell(0, 6, "Historial de Facturas:", 0, 1, 'L'); pdf.set_font('Arial','B',9); pdf.set_fill_color(230,230,230); pdf.set_draw_color(50,50,50)
        col_w = {'nro': 25, 'fecha': 40, 'tot_usd': 50, 'tot_bs': 50}; th = ['Nro Factura', 'Fecha', 'Total USD', 'Total Bs.']
        twh=sum(col_w.values()); lwh=twh*0.65; vwh=twh*0.35
        def print_total_line(label, value_usd, value_eq_bs=None, is_total=False): # Def local
             pdf.set_font('Arial', 'B' if is_total else '', 10); label_lt1 = to_latin1(label)
             vusd_s = f"USD {value_usd:,.2f}" if value_usd is not None else None
             vbs_eq_s = None
             if value_eq_bs is not None: vbs_eq_s = f"Bs. Eq. {value_eq_bs:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
             pdf.cell(lwh, 6, label_lt1, 0, 0, 'R', new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.cell(vwh, 6, vusd_s if vusd_s else "-", 0, 1, 'R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
             if vbs_eq_s: pdf.set_font('Arial', 'B' if is_total else '', 10); pdf.cell(lwh, 6, "", 0, 0, 'R', new_x=XPos.RIGHT, new_y=YPos.TOP); pdf.cell(vwh, 6, vbs_eq_s, 0, 1, 'R', new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for i, h in enumerate(th): pdf.cell(col_w[list(col_w.keys())[i]], 7, h, 1, 0, 'C', fill=True)
        pdf.ln(); pdf.set_font('Arial','',8)
        for f in facturas_cliente:
             num=f.get('numero_factura','N/A'); fdt=datetime.datetime.fromisoformat(f.get('fecha','')) if f.get('fecha') else None; fec=fdt.strftime('%d/%m/%Y %H:%M') if fdt else 'N/A'
             tbs=f"{f.get('total_bs',0):,.2f}".replace(',','#').replace('.',',').replace('#','.'); tusd=f"${f.get('total_usd',0):,.2f}"
             pdf.cell(col_w['nro'],6,num,1,0,'C'); pdf.cell(col_w['fecha'],6,fec,1,0,'C'); pdf.cell(col_w['tot_usd'],6,tusd,1,0,'R'); pdf.cell(col_w['tot_bs'],6,tbs,1,1,'R')
        pdf.ln(5); print_total_line("TOTAL Histórico:", total_gastado_usd, total_gastado_usd * tasa_reporte if tasa_reporte > 0 else None, is_total=True)
        os.makedirs(CARPETA_HISTORIAL_CLIENTES, exist_ok=True); pdf_fname=os.path.join(CARPETA_HISTORIAL_CLIENTES, f"historial_cliente_{rif_buscar}.pdf")
        pdf.output(pdf_fname); print(Fore.GREEN + f"PDF historial: '{pdf_fname}'"); return True
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF HISTORIAL CLIENTE ---"); print(Fore.RED + f"Error CRITICO: {type(e).__name__} - {e}"); print("--- Traceback ---"); traceback.print_exc(); print("--- Fin Traceback ---"); return False

# --- NUEVA FUNCIÓN: PDF Reporte General ---
# ... (sin cambios) ...
def generar_pdf_reporte_top(clientes, inventario, historial_completo):
    print(Fore.CYAN + "\n--- Generando PDF Reporte General ---")
    if not historial_completo: print(Fore.YELLOW + "No hay historial."); return
    tasa=0
    while True:
        try:
            t_str=input(Fore.YELLOW + "Tasa Bs./USD para valor total Gral. PDF (o vacío omitir): ").strip().replace(',','.')
            if not t_str: print("Se omitirá valor Gral. Bs."); break
            tasa=float(t_str)
            if tasa > 0: break
            else: print(Fore.YELLOW + "Tasa positiva.")
        except ValueError: print(Fore.YELLOW + "Tasa inválida.")
    ventas_cliente_usd = Counter(); ventas_cliente_bs = Counter(); prods_vendidos = Counter()
    print("Procesando facturas para reporte general...")
    for f in historial_completo:
        rif = f.get('cliente',{}).get('rif')
        if rif and rif in clientes:
             total_usd_factura = f.get('total_usd', 0); total_bs_factura = f.get('total_bs', 0)
             ventas_cliente_usd[rif] += total_usd_factura; ventas_cliente_bs[rif] += total_bs_factura
             for item in f.get('items',[]):
                 pid = item.get('id'); cant = item.get('cantidad',0)
                 if pid and cant>0 and pid in inventario: prods_vendidos[pid] += cant
    top_cli_data = ventas_cliente_usd.most_common(10); top_prod_data = prods_vendidos.most_common(10)
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4'); pdf.add_page()
        try: # Header
            if os.path.exists(ARCHIVO_LOGO): pdf.image(ARCHIVO_LOGO, x=10, y=8, w=30)
            else: print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
            pdf.set_xy(45, 10)
        except Exception: pdf.set_xy(10, 10)
        def to_latin1(t): txt=str(t) if t is not None else ''; return txt.encode('latin-1','replace').decode('latin-1')
        pdf.set_font('Arial','B',11); pdf.cell(0,5,to_latin1(NOMBRE_EMPRESA),0,1,'C'); pdf.set_font('Arial','',9); pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C'); pdf.cell(0,5,f"Telefono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C'); pdf.ln(8)
        pdf.set_font('Arial','B',14); pdf.cell(0,10,f"Reporte General de Ventas",0,1,'C'); pdf.ln(2)
        f_rep=datetime.datetime.now().strftime('%d/%m/%Y %H:%M'); pdf.set_font('Arial','',10); pdf.cell(0,5,f"Generado: {f_rep}",0,1,'C'); pdf.ln(8)
        # Top Clientes (USD primero)
        pdf.set_font('Arial','B',12); pdf.cell(0, 8, "Top 10 Clientes (Por Monto Total Facturado en USD)", 0, 1, 'L'); pdf.ln(2)
        pdf.set_font('Arial','B',9); pdf.set_fill_color(230,230,230); pdf.set_draw_color(50,50,50)
        col_w_cli={'rank':10,'rif':30,'nombre':75,'total_usd':35,'total_bs':35}; th_cli=['#','RIF','Nombre','Total USD','Total Bs.']
        for i, h in enumerate(th_cli): pdf.cell(col_w_cli[list(col_w_cli.keys())[i]], 7, h, 1, 0, 'C', fill=True)
        pdf.ln(); pdf.set_font('Arial','',8)
        if top_cli_data:
            for i, (rif, total_usd) in enumerate(top_cli_data):
                nom_cli = to_latin1(clientes.get(rif, {}).get('nombre', 'N/A'))[:35]
                total_bs_cli = ventas_cliente_bs.get(rif, 0)
                tot_usd_f = f"${total_usd:,.2f}"; tot_bs_f = f"{total_bs_cli:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.')
                pdf.cell(col_w_cli['rank'], 6, str(i+1), 1, 0, 'C'); pdf.cell(col_w_cli['rif'], 6, to_latin1(rif), 1, 0, 'L')
                pdf.cell(col_w_cli['nombre'], 6, nom_cli, 1, 0, 'L'); pdf.cell(col_w_cli['total_usd'], 6, tot_usd_f, 1, 0, 'R'); pdf.cell(col_w_cli['total_bs'], 6, tot_bs_f, 1, 1, 'R')
        else: pdf.cell(sum(col_w_cli.values()), 6, "No hay datos.", 1, 1, 'C')
        pdf.ln(10)
        # Top Productos
        pdf.set_font('Arial','B',12); pdf.cell(0, 8, "Top 10 Productos Vendidos (Por Cantidad Total)", 0, 1, 'L'); pdf.ln(2)
        pdf.set_font('Arial','B',9); pdf.set_fill_color(230,230,230)
        col_w_prod={'rank':15,'id':35,'nombre':100,'total':20}; th_prod=['#','ID Producto','Nombre','Cant. Vendida']
        for i, h in enumerate(th_prod): pdf.cell(col_w_prod[list(col_w_prod.keys())[i]], 7, h, 1, 0, 'C', fill=True)
        pdf.ln(); pdf.set_font('Arial','',8)
        if top_prod_data:
            for i, (pid, cant) in enumerate(top_prod_data):
                nom_prod = to_latin1(inventario.get(pid, {}).get('nombre', 'N/A'))[:45]
                pdf.cell(col_w_prod['rank'], 6, str(i+1), 1, 0, 'C'); pdf.cell(col_w_prod['id'], 6, to_latin1(pid), 1, 0, 'L')
                pdf.cell(col_w_prod['nombre'], 6, nom_prod, 1, 0, 'L'); pdf.cell(col_w_prod['total'], 6, str(cant), 1, 1, 'C')
        else: pdf.cell(sum(col_w_prod.values()), 6, "No hay datos.", 1, 1, 'C')
        # Total General (USD primero)
        pdf.ln(10)
        total_general_usd = sum(ventas_cliente_usd.values()); total_general_bs = sum(ventas_cliente_bs.values())
        pdf.set_font('Arial','B',10)
        pdf.cell(0, 6, f"Total General Facturado (USD): ${total_general_usd:,.2f}", 0, 1, 'R')
        if tasa > 0: pdf.cell(0, 6, f"Total General Facturado (Bs. @{tasa:,.2f}): Bs. {total_general_bs:,.2f}".replace(',', '#').replace('.', ',').replace('#', '.'), 0, 1, 'R')
        # Guardar PDF
        os.makedirs(CARPETA_REPORTES_GENERALES, exist_ok=True)
        pdf_fname=os.path.join(CARPETA_REPORTES_GENERALES, f"reporte_general_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        pdf.output(pdf_fname); print(Fore.GREEN + f"PDF reporte general: '{pdf_fname}'"); return True
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF REPORTE GENERAL ---"); print(Fore.RED + f"Error CRITICO: {type(e).__name__} - {e}"); print("--- Traceback ---"); traceback.print_exc(); print("--- Fin Traceback ---"); return False

# --- Gestión de Facturas ---
# ACTUALIZADO v3.20: Modificar precio último ítem, Nro Factura Manual
def buscar_producto_por_nombre(inventario):
    print(Fore.CYAN + "\n--- Buscar Producto por Nombre ---")
    nombre = input("Nombre (o parte): ").strip().lower()
    encontrados = []
    for pid, datos in inventario.items():
        if nombre in datos.get('nombre', '').lower():
            encontrados.append((pid, datos))
    if encontrados:
        print(Style.BRIGHT + f"\nResultados:")
        print(f"{'ID':<10} {'Nombre':<30} {'Precio USD':>10} {'Stock':>8}")
        print("-" * 60)
        for pid, datos in encontrados:
            print(f"{pid:<10} {datos['nombre'][:30]:<30} {datos.get('precio',0):>10.2f} {datos.get('cantidad',0):>8}")
        print("-" * 60)
        return encontrados
    else:
        print(Fore.YELLOW + "No se encontraron productos con ese nombre.")
        return None

def menu_buscar_producto(inventario):
    while True:
        print(Fore.CYAN + "\n--- Buscar Producto ---")
        print("1. Buscar por ID")
        print("2. Buscar por Nombre")
        print("0. Volver")
        op = input(Fore.YELLOW + "Seleccione: ")
        if op == '1':
            pid = input("ID del producto: ").strip().upper()
            prod = get_producto(inventario, pid)
            if prod:
                print(Style.BRIGHT + f"\nProducto encontrado:")
                print(f"ID: {pid}")
                print(f"Nombre: {prod['nombre']}")
                print(f"Precio USD: ${prod.get('precio',0):.2f}")
                print(f"Stock: {prod.get('cantidad',0)}")
                return pid, prod
            else:
                print(Fore.YELLOW + f"Producto con ID {pid} no encontrado.")
        elif op == '2':
            resultados = buscar_producto_por_nombre(inventario)
            if resultados:
                pid = input("\nIngrese el ID del producto deseado: ").strip().upper()
                prod = get_producto(inventario, pid)
                if prod:
                    return pid, prod
                else:
                    print(Fore.YELLOW + f"Producto con ID {pid} no encontrado.")
        elif op == '0':
            return None, None
        else:
            print(Fore.YELLOW + "Opción inválida.")

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

def crear_factura(clientes, inventario, config):
    try:
        print(Fore.CYAN + "\n--- Crear Factura (Base USD) ---")
        # Obtener fecha y hora actual
        fecha_hora_actual = datetime.datetime.now()
        # Preguntar si desea modificar la fecha y hora
        print(Fore.WHITE + f"\nFecha y hora actual: {fecha_hora_actual.strftime('%d/%m/%Y %H:%M')}")
        modificar_fecha = input(Fore.YELLOW + "¿Desea modificar la fecha y hora? (S/N): ").upper()
        if modificar_fecha == 'S':
            while True:
                try:
                    fecha_str = input(Fore.WHITE + "Ingrese la fecha (DD/MM/YYYY): ")
                    hora_str = input(Fore.WHITE + "Ingrese la hora (HH:MM): ")
                    fecha_hora_str = f"{fecha_str} {hora_str}"
                    fecha_hora_actual = datetime.datetime.strptime(fecha_hora_str, '%d/%m/%Y %H:%M')
                    break
                except ValueError:
                    print(Fore.RED + "Formato inválido. Use DD/MM/YYYY para la fecha y HH:MM para la hora.")
        # --- TASA AUTOMÁTICA BCV ---
        tasa = 0; tasa_valida = False
        tasa_bcv = obtener_tasa_bcv()
        if tasa_bcv:
            print(Fore.GREEN + f"Tasa BCV obtenida automáticamente: {tasa_bcv:.2f} Bs/USD")
        else:
            print(Fore.YELLOW + "No se pudo obtener la tasa BCV automáticamente.")
        while not tasa_valida:
            try:
                sugerida = f" [{tasa_bcv:.2f}]" if tasa_bcv else ''
                t_s = input(Fore.YELLOW+f"TASA Bs./USD{sugerida}: ").strip().replace(',','.')
                if not t_s and tasa_bcv:
                    tasa = tasa_bcv
                    tasa_valida = True
                    break
                tasa_temp = float(t_s)
                if tasa_temp <= 0:
                    print(Fore.YELLOW+"Positiva.")
                else:
                    tasa = tasa_temp
                    tasa_valida = True
            except ValueError:
                print(Fore.YELLOW+"Inválida.")
        print(f"Tasa: {tasa:.2f} Bs./USD");
        # Preguntar por la tasa de IVA
        print(Fore.WHITE + "\nTasa IVA predeterminada: 0%")
        while True:
            try:
                iva_str = input(Fore.YELLOW + "Ingrese tasa IVA (0-100%) o Enter para 0%: ").strip().replace(',','.')
                if not iva_str:
                    t_iva = 0.0
                    print(Fore.GREEN + "Usando tasa IVA: 0%")
                    break
                t_iva = float(iva_str) / 100
                if 0 <= t_iva <= 1:
                    print(Fore.GREEN + f"Usando tasa IVA: {t_iva*100:.0f}%")
                    break
                else:
                    print(Fore.RED + "La tasa debe estar entre 0% y 100%")
            except ValueError:
                print(Fore.RED + "Valor inválido. Ingrese un número entre 0 y 100")
        # Preguntar por descuento
        while True:
            try:
                desc_str = input(Fore.YELLOW + "Ingrese porcentaje de DESCUENTO (0-100%) o Enter para 0%: ").strip().replace(',','.')
                if not desc_str:
                    descuento_porcentaje = 0.0
                    print(Fore.GREEN + "Sin descuento.")
                    break
                descuento_porcentaje = float(desc_str)
                if 0 <= descuento_porcentaje <= 100:
                    print(Fore.GREEN + f"Descuento aplicado: {descuento_porcentaje:.2f}%")
                    break
                else:
                    print(Fore.RED + "El descuento debe estar entre 0% y 100%")
            except ValueError:
                print(Fore.RED + "Valor inválido. Ingrese un número entre 0 y 100")
        cond=""; dias_c=0; cond_txt=""
        while cond not in ['1','2']: # Condición
            cond=input(Fore.YELLOW+"Condición(1=Contado, 2=Crédito): ").strip()
            if cond=='2': # Días Crédito
                while True:
                    dias_c = -1;    
                    try: dias_str = input(Fore.YELLOW + " Días Crédito: ").strip(); dias_c = int(dias_str)
                    except ValueError: print(Fore.YELLOW+"Inválido."); continue
                    if dias_c > 0: break
                    else: print(Fore.YELLOW + "Positivo.")
                cond_txt="Credito"
            elif cond=='1': cond_txt="Contado"; dias_c=0
            else: print(Fore.YELLOW+"Inválida.")
        print(f"Condición: {cond_txt}"+(f" ({dias_c} días)" if dias_c>0 else ""));

        # Obtener número de factura
        num_fact = obtener_siguiente_numero_factura(config)
        if not num_fact:
            print(Fore.RED + "Error al generar número de factura.")
            return False

        # Buscar cliente
        cli = None
        while not cli:
            print("\n--- Buscar Cliente ---")
            print("1. Buscar por RIF")
            print("2. Buscar por Nombre")
            op_cli = input(Fore.YELLOW + "Seleccione: ")
            if op_cli == '1':
                rif = input(Fore.WHITE + "RIF del Cliente: ").strip().upper()
                cli = clientes.get(rif)
                if cli:
                    cli = dict(cli)
                    cli['rif'] = rif
                    print(f"Cliente: {cli['nombre']}")
                    break
            elif op_cli == '2':
                resultados = buscar_cliente_por_nombre(clientes)
                if resultados:
                    rif = input("\nIngrese el RIF del cliente deseado: ").strip().upper()
                    cli = clientes.get(rif)
                    if cli:
                        cli = dict(cli)
                        cli['rif'] = rif
                        print(f"Cliente: {cli['nombre']}")
                        break
            else:
                print(Fore.YELLOW + "Opción inválida.")
                continue

            if not cli:
                print(Fore.YELLOW + f"Cliente no encontrado.")
                if input("¿Desea crear un nuevo cliente? (s/n): ").lower() == 's':
                    agregar_o_modificar_cliente(clientes)
                    clientes = cargar_clientes()
                    cli = clientes.get(rif)
                    if cli:
                        print(f"Cliente creado: {cli['nombre']}")
                        break
                    else:
                        print(Fore.RED + "Error al crear el cliente.")
                        return False
                else:
                    print("Operación cancelada.")
                    return False

        items_f=[]
        while True:
            print(Style.BRIGHT+"\n--- Agregar Ítem ---")
            if items_f: # Mostrar ítems actuales
                 print(Fore.BLUE+"--- Ítems en Factura Actual ---")
                 temp_sub_usd = sum(it['cantidad']*it.get('precio_unitario_usd',0) for it in items_f)
                 print(f"{'ID':<10} {'Nombre':<25} {'Cant':>5} {'P.U USD':>10} {'SubT USD':>10}")
                 print("-" * 65)
                 for item in items_f: subt_usd = item['cantidad'] * item['precio_unitario_usd']; print(f"{item['id']:<10} {item['nombre'][:25]:<25} {item['cantidad']:>5} {item['precio_unitario_usd']:>10.2f} {subt_usd:>10.2f}")
                 print("-" * 65); print(f"{'Subtotal actual:':>54} ${temp_sub_usd:,.2f}"); print("-" * 65)

            op_prod = input("¿Cómo desea buscar el producto? (1: ID, 2: Nombre, 'fin' terminar, 'm' modificar último): ").strip()

            if op_prod == 'FIN': break # Terminar

            # Modificar último ítem (Cantidad o Precio)
            if op_prod == 'M' and items_f:
                item_a_modificar = items_f[-1]; prod_mod = get_producto(inventario, item_a_modificar['id'])
                if not prod_mod: print(Fore.RED + "Error: Producto no existe."); continue
                print(Fore.YELLOW + f"\n--- Modificando: {item_a_modificar['id']} - {item_a_modificar['nombre']} ---")
                print(f" Cantidad actual: {item_a_modificar['cantidad']} | Precio Unitario USD actual: ${item_a_modificar['precio_unitario_usd']:.2f}")
                while True: # Bucle para elegir qué modificar
                    op_mod = input("¿Qué desea modificar? (1: Cantidad, 2: Precio USD, 0: Cancelar): ").strip()
                    if op_mod == '1': # Modificar Cantidad
                        stock_disponible_mod = prod_mod.get('cantidad', 0) + item_a_modificar['cantidad']
                        print(f" Stock disponible real: {stock_disponible_mod}")
                        try:
                            cant_str_mod = input(f" Nueva Cantidad (max {stock_disponible_mod}) o 'eliminar': ").strip()
                            if cant_str_mod.lower() == 'eliminar': print(Fore.RED + f"Eliminando ítem..."); items_f.pop(); break
                            nueva_cant = int(cant_str_mod)
                            if 0 < nueva_cant <= stock_disponible_mod:
                                 print(Fore.GREEN + f"Cantidad actualizada a {nueva_cant}")
                                 items_f[-1]['cantidad'] = nueva_cant; break
                            elif nueva_cant > stock_disponible_mod: print(Fore.YELLOW + "Excede stock.")
                            else: print(Fore.YELLOW + "Cantidad > 0.")
                        except ValueError: print(Fore.YELLOW + "Inválida.")
                        break # Sale bucle opción modificación
                    elif op_mod == '2': # Modificar Precio
                        while True: # Bucle 
                            try:
                                nuevo_precio_str = input(" Nuevo Precio Unitario USD: ").strip().replace(',','.')
                                nuevo_precio = float(nuevo_precio_str)
                                if nuevo_precio > 0:
                                    print(Fore.GREEN + f"Precio actualizado a ${nuevo_precio:.2f}")
                                    items_f[-1]['precio_unitario_usd'] = nuevo_precio
                                    items_f[-1]['precio_unitario_bs'] = nuevo_precio * tasa
                                    break
                                else: print(Fore.YELLOW + "Precio > 0.")
                            except ValueError: print(Fore.YELLOW + "Inválido.")
                        break # Sale bucle opción modificación
                    elif op_mod == '0': print("Modificación cancelada."); break
                    else: print(Fore.YELLOW + "Opción inválida.")
                continue # Vuelve al inicio del bucle principal

            # Buscar producto
            pid, prod = None, None
            if op_prod == '1':
                pid = input("ID del producto: ").strip().upper()
                prod = get_producto(inventario, pid)
            elif op_prod == '2':
                resultados = buscar_producto_por_nombre(inventario)
                if resultados:
                    pid = input("\nIngrese el ID del producto deseado: ").strip().upper()
                    prod = get_producto(inventario, pid)
            else:
                print(Fore.YELLOW + "Opción inválida.")
                continue

            if not prod:
                print(Fore.RED + "Producto no existe.")
                continue

            # Verificar stock
            if prod.get('cantidad', 0) <= 0:
                print(Fore.RED + "Sin stock disponible.")
                continue

            # Agregar ítem
            while True: # Cantidad Item
                try:
                    cant=int(input(f"Cant (max {prod.get('cantidad',0)}): ").strip());
                    if 0<cant<=prod.get('cantidad',0):
                        pu_u=prod.get('precio',0); pu_b=pu_u*tasa;
                        it={"id":pid,"nombre":prod['nombre'],"cantidad":cant,"precio_unitario_usd":pu_u,"precio_unitario_bs":pu_b,"categoria":prod.get('categoria',''),"ruta_imagen":prod.get('ruta_imagen','')}
                        items_f.append(it); print(Fore.GREEN+"-> Ítem agregado."); break
                    elif cant>prod.get('cantidad',0): print(Fore.YELLOW+"Insuficiente.")
                    else: print(Fore.YELLOW+"Cant > 0.")
                except ValueError: print(Fore.YELLOW+"Inválida.")

        if not items_f: print("Cancelada (sin ítems)."); return False

        # --- NUEVO v3.21: Preguntar por número de factura manual ---
        n_f = None
        prox_n_auto = config.get('proximo_numero_factura', 1)
        while n_f is None:
            n_f_manual_str = input(Fore.YELLOW + f"Ingrese Nro Factura deseado (o deje vacío para usar {prox_n_auto:04d}): ").strip()
            if not n_f_manual_str:
                n_f = obtener_siguiente_numero_factura(config) # Usa automático y actualiza config
                print(f"Usando número automático: {n_f}")
                break
            else:
                try:
                    num_manual = int(n_f_manual_str)
                    if num_manual <= 0: print(Fore.RED + "Número debe ser positivo."); continue
                    n_f_temp = f"{num_manual:04d}"
                    json_path_check = os.path.join(CARPETA_FACTURAS_JSON, f"factura_{n_f_temp}.json")
                    if os.path.exists(json_path_check):
                        print(Fore.RED + f"¡Error! Factura Nro. {n_f_temp} ya existe.")
                    else:
                        n_f = n_f_temp; print(Fore.GREEN + f"Usando número manual: {n_f}")
                        # No actualizamos el contador automático de config.json
                        break
                except ValueError: print(Fore.RED + "Número inválido.")

        # Cálculos Finales
        sub_bs = sum(it['cantidad']*it.get('precio_unitario_bs',0) for it in items_f)
        iva_bs = sub_bs * t_iva  # Aplicar el IVA al subtotal en Bs
        tot_bs = sub_bs + iva_bs  # Total en Bs incluye IVA
        
        # Aplicar descuento
        monto_descuento_bs = (sub_bs + iva_bs) * (descuento_porcentaje/100)
        tot_bs -= monto_descuento_bs
        
        sub_usd = sum(it['cantidad']*it.get('precio_unitario_usd',0) for it in items_f)
        iva_usd = sub_usd * t_iva  # Aplicar el IVA al subtotal en USD
        tot_usd = sub_usd + iva_usd  # Total en USD incluye IVA
        monto_descuento_usd = (sub_usd + iva_usd) * (descuento_porcentaje/100)
        tot_usd -= monto_descuento_usd

        # Resumen Final en Consola
        print(Fore.CYAN+Style.BRIGHT+"\n--- Resumen Final Factura ---")
        f_a=datetime.datetime.now()
        print(f"Nro:{n_f}|Ctrl:{n_f}|Fecha:{f_a.strftime('%d/%m/%Y %H:%M')}")
        print(f"Cli:{cli['nombre']}({rif})|Cond:{cond_txt}"+(f" {dias_c}d" if dias_c>0 else ""))
        print(f"Tasa:{tasa:.2f}Bs/USD")
        print("-" * 70)
        print(f"{'Cant':<4}{'Producto':<25}{'P.U USD':>10}{'P.U Bs':>12}{'SubT Bs':>12}")
        print("-" * 70)
        for i in items_f:
            s_it_b=i['cantidad']*i.get('precio_unitario_bs',0)
            n_m=i.get('nombre','N/A')[:25]
            pu_u_m=i.get('precio_unitario_usd',0)
            pu_b_m=i.get('precio_unitario_bs',0)
            print(f"{i['cantidad']:<4}{n_m:<25}{pu_u_m:>10.2f}{pu_b_m:>12.2f}{s_it_b:>12,.2f}")
        print("-" * 70)
        print(f"{'Subtotal (Bs):':>53} Bs. {sub_bs:>12,.2f}")
        print(f"{'Subtotal USD:':>53} USD {sub_usd:>10,.2f}")
        print(f"{f'IVA ({t_iva*100:.0f}%):':>53} Bs. {iva_bs:>12,.2f}")
        print(Style.BRIGHT+f"{'Total a Pagar (Bs):':>53} Bs. {tot_bs:>12,.2f}")
        print(Style.BRIGHT+f"{'Total a Pagar (USD):':>53} USD {tot_usd:>10,.2f}")
        print("-" * 70)

        # Confirmar y Guardar
        while True:
            confirmar = input(Fore.YELLOW + "¿Generar/Guardar factura? (s/n): ").lower()
            if confirmar == 's':
                ok=True
                inventario_original_cantidades = {}
                items_a_ajustar = Counter(item['id'] for item in items_f)
                cantidades_netas = {pid: sum(item['cantidad'] for item in items_f if item['id'] == pid) for pid in items_a_ajustar}
                for pid_ajustar, cantidad_neta in cantidades_netas.items():
                    prod_actual = get_producto(inventario, pid_ajustar)
                    if prod_actual: inventario_original_cantidades[pid_ajustar] = prod_actual.get('cantidad', 0)
                    if not ajustar_stock(inventario, pid_ajustar, -cantidad_neta, 'salida'):
                         ok=False
                         print(Fore.RED+f"¡ALERTA! Fallo ajuste stock {pid_ajustar}. Factura NO.")
                         print(Fore.YELLOW + "Revirtiendo ajustes...")
                         for pid_revertir, cant_original in inventario_original_cantidades.items():
                             inventario[pid_revertir]['cantidad'] = cant_original
                         guardar_inventario(inventario)
                         print(Fore.YELLOW + "Ajustes revertidos.")
                         break
                if not ok: return False
                print(Fore.GREEN+"Inventario actualizado.")
                f_d={
                    "numero_factura":n_f,
                    "fecha":fecha_hora_actual.isoformat(),
                    "tasa_cambio":tasa,
                    "cliente":{"rif":rif,**cli},
                    "items":items_f,
                    "subtotal_bs":sub_bs,
                    "iva_bs":iva_bs,
                    "total_bs":tot_bs,
                    "subtotal_usd":sub_usd,
                    "iva_usd":iva_usd,
                    "total_usd":tot_usd,
                    "condicion_pago":cond_txt,
                    "dias_credito":dias_c,
                    "tasa_iva_aplicada":t_iva,
                    "descuento_porcentaje":descuento_porcentaje,
                    "descuento_bs":monto_descuento_bs,
                    "descuento_usd":monto_descuento_usd
                }
                n_json=os.path.join(CARPETA_FACTURAS_JSON,f"factura_{n_f}.json")
                if guardar_datos(f_d,n_json):
                     print(Fore.GREEN+f"Factura JSON: '{n_json}'")
                     n_pdf=os.path.join(CARPETA_FACTURAS_PDF,f"factura_{n_f}.pdf")
                     if generar_pdf_factura(f_d,n_pdf): print(Fore.GREEN + f"Factura PDF generada: '{n_pdf}'")
                     else: print(Fore.RED+f"Error PDF {n_f}.")
                     # Cargar CxC ANTES de modificar
                     cuentas_cobrar_actual = cargar_cuentas_cobrar()
                     # Agregar a CxC con el estado correspondiente
                     if cond_txt == "Credito":
                         cuentas_cobrar_actual[n_f] = {
                             'rif': rif,
                             'total_usd': tot_usd,
                             'abonado_usd': 0,
                             'estado': 'Por Cobrar'
                         }
                     else:  # Contado
                         cuentas_cobrar_actual[n_f] = {
                             'rif': rif,
                             'total_usd': tot_usd,
                             'abonado_usd': tot_usd,  # Se marca como pagada completa
                             'estado': 'Cobrada',
                             'fecha_ultimo_abono': fecha_hora_actual.strftime('%Y-%m-%d %H:%M'),
                             'tipo_pago': 'Contado'
                         }
                     if guardar_cuentas_cobrar(cuentas_cobrar_actual):
                         print(Fore.GREEN + f"Factura {n_f} añadida a CxC como {'crédito' if cond_txt == 'Credito' else 'contado'}.")
                     else:
                         print(Fore.RED + f"Error al guardar CxC para Factura {n_f}.")
                     return True
            elif confirmar == 'n':
                print("Operación cancelada.")
                return False
            else:
                print(Fore.YELLOW + "Opción inválida. Ingrese 's' o 'n'.")
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR CREAR FACTURA ---")
        print(Fore.RED + f"Error CRITICO: {type(e).__name__} - {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")
        return False

def generar_pdf_cliente_individual(clientes):
    print(Fore.CYAN + "\n--- Generando Reporte Individual de Cliente ---")
    
    # Permitir buscar por RIF o por nombre
    print("¿Cómo desea buscar el cliente?")
    print("1. Por RIF")
    print("2. Por Nombre")
    op_buscar = input(Fore.YELLOW + "Seleccione: ").strip()
    rif = None
    if op_buscar == '1':
        rif = input(Fore.YELLOW + "Ingrese el RIF del cliente: ").strip().upper()
        if rif not in clientes:
            print(Fore.RED + "Cliente no encontrado.")
            return False
    elif op_buscar == '2':
        nombre_buscar = input(Fore.YELLOW + "Ingrese el nombre (o parte): ").strip().lower()
        coincidencias = [(r, d) for r, d in clientes.items() if nombre_buscar in d.get('nombre', '').lower()]
        if not coincidencias:
            print(Fore.RED + "No se encontraron clientes con ese nombre.")
            return False
        print(Style.BRIGHT + f"\nResultados:")
        for i, (r, d) in enumerate(coincidencias):
            print(f"{i+1}. RIF: {r} | Nombre: {d['nombre']} | Tel: {d['telefono']}")
        idx_sel = input(Fore.YELLOW + "Seleccione el número del cliente: ").strip()
        try:
            idx_sel = int(idx_sel) - 1
            rif = coincidencias[idx_sel][0]
        except:
            print(Fore.RED + "Selección inválida.")
            return False
    else:
        print(Fore.RED + "Opción inválida.")
        return False
    
    try:
        pdf = FPDF(orientation='P', unit='mm', format='A4')
        pdf.add_page()
        
        # Encabezado
        try:
            if os.path.exists(ARCHIVO_LOGO):
                pdf.image(ARCHIVO_LOGO, x=10, y=8, w=30)
            else:
                print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
            pdf.set_xy(45, 10)
        except Exception:
            pdf.set_xy(10, 10)
            
        def to_latin1(t):
            txt = str(t) if t is not None else ''
            return txt.encode('latin-1','replace').decode('latin-1')
            
        pdf.set_font('Arial','B',14)
        pdf.cell(0,10,'Reporte Individual de Cliente',0,1,'C')
        pdf.ln(5)
        
        # Fecha de generación
        pdf.set_font('Arial','',10)
        pdf.cell(0,5,f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}',0,1,'R')
        pdf.ln(8)
        
        # Datos del cliente en ficha con bordes
        cliente = clientes[rif]
        fecha_creacion = datetime.datetime.fromtimestamp(os.path.getctime(ARCHIVO_CLIENTES)).strftime('%d/%m/%Y')
        ficha_x = 30
        ficha_y = pdf.get_y() + 5
        ficha_w = 150
        label_w = 40
        value_w = ficha_w - label_w
        row_h = 9
        pdf.set_xy(ficha_x, ficha_y)
        pdf.set_font('Arial','B',11)
        pdf.cell(ficha_w, row_h, 'DATOS DEL CLIENTE', 1, 2, 'C', fill=True)
        pdf.set_font('Arial','',11)
        # RIF
        pdf.set_xy(ficha_x, pdf.get_y())
        pdf.cell(label_w, row_h, 'RIF:', 1, 0, 'L')
        pdf.cell(value_w, row_h, to_latin1(rif), 1, 1, 'L')
        # Nombre (multi-línea)
        nombre = to_latin1(cliente.get('nombre', ''))
        nombre_lines = pdf.multi_cell(value_w, row_h/2, nombre, 0, 'L', split_only=True)
        nombre_h = max(len(nombre_lines), 1) * (row_h/2)
        pdf.set_xy(ficha_x, pdf.get_y())
        pdf.cell(label_w, nombre_h, 'Nombre:', 1, 0, 'L')
        y_actual = pdf.get_y()
        x_val = ficha_x + label_w
        pdf.set_xy(x_val, y_actual)
        pdf.multi_cell(value_w, row_h/2, nombre, 1, 'L')
        # Dirección (multi-línea)
        direccion = to_latin1(cliente.get('direccion', ''))
        direccion_lines = pdf.multi_cell(value_w, row_h/2, direccion, 0, 'L', split_only=True)
        direccion_h = max(len(direccion_lines), 1) * (row_h/2)
        pdf.set_xy(ficha_x, pdf.get_y())
        pdf.cell(label_w, direccion_h, 'Dirección:', 1, 0, 'L')
        y_actual = pdf.get_y()
        x_val = ficha_x + label_w
        pdf.set_xy(x_val, y_actual)
        pdf.multi_cell(value_w, row_h/2, direccion, 1, 'L')
        # Teléfono
        pdf.set_xy(ficha_x, pdf.get_y())
        pdf.cell(label_w, row_h, 'Teléfono:', 1, 0, 'L')
        pdf.cell(value_w, row_h, to_latin1(cliente.get('telefono', '')), 1, 1, 'L')
        # Fecha de Registro
        pdf.set_xy(ficha_x, pdf.get_y())
        pdf.cell(label_w, row_h, 'Fecha de Registro:', 1, 0, 'L')
        pdf.cell(value_w, row_h, fecha_creacion, 1, 1, 'L')
        # Guardar PDF
        os.makedirs(CARPETA_REPORTES_CLIENTES, exist_ok=True)
        pdf_fname = os.path.join(CARPETA_REPORTES_CLIENTES, f"reporte_cliente_{rif}_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
        pdf.output(pdf_fname)
        print(Fore.GREEN + f"PDF Reporte Individual de Cliente: '{pdf_fname}'")
        return True
        
    except Exception as e:
        print(Fore.RED + f"\n--- ERROR PDF REPORTE CLIENTE ---")
        print(Fore.RED + f"Error CRITICO: {type(e).__name__} - {e}")
        print("--- Traceback ---")
        traceback.print_exc()
        print("--- Fin Traceback ---")
        return False

def ver_cuentas_contado(cuentas_cobrar, clientes):
    # Título centrado con bordes
    print(Fore.CYAN + Style.BRIGHT + "\n" + "="*100)
    print(" " * 35 + "CUENTAS AL CONTADO")
    print("="*100)
    
    if not cuentas_cobrar:
        print(Fore.YELLOW + "\nNo hay cuentas registradas.")
        return

    # Filtrar cuentas al contado
    cuentas_contado = {}
    for k, v in cuentas_cobrar.items():
        tipo_pago = v.get('tipo_pago', '').lower()
        estado = v.get('estado', '').lower()
        
        # Incluir facturas que son al contado o que están cobradas completamente
        if tipo_pago == 'contado' or estado == 'cobrada':
            cuentas_contado[k] = v

    if not cuentas_contado:
        print(Fore.GREEN + "\nNo hay cuentas al contado registradas.")
        return

    # Encabezado de la tabla
    print("\n" + "-"*100)
    print(f"{'Nro Fact':^10} {'RIF':^15} {'Cliente':^30} {'Total USD':^12} {'Fecha Pago':^12} {'Método':^15}")
    print("-"*100)

    total_facturado = 0

    # Ordenar por número de factura
    for num_fact, datos in sorted(cuentas_contado.items()):
        rif_cli = datos.get('rif', 'N/A')
        cliente_nombre = clientes.get(rif_cli,{}).get('nombre', 'N/A')[:30]
        total_usd = datos.get('total_usd', 0)
        fecha_pago = datos.get('fecha_ultimo_abono', 'N/A')
        metodo_pago = datos.get('tipo_pago', 'N/A')

        # Formatear números con separadores de miles
        total_str = f"${total_usd:,.2f}"

        # Imprimir línea con alineación centrada
        print(f"{num_fact:^10} {rif_cli:^15} {cliente_nombre:^30} {total_str:^12} {fecha_pago:^12} {metodo_pago:^15}")

        total_facturado += total_usd

    # Línea de totales
    print("-"*100)
    total_str = f"${total_facturado:,.2f}"
    print(f"{'TOTAL:':^55} {total_str:^12}")
    print("-"*100)

    # Resumen con viñetas
    print(f"\nResumen:")
    print(f"• Total de cuentas al contado: {len(cuentas_contado)}")
    print(f"• Monto total facturado: ${total_facturado:,.2f}")
    print("="*100)

def menu_gestion_cuentas(cuentas_cobrar, clientes):
    while True:
        print(Fore.CYAN + Style.BRIGHT + "\n=== GESTIÓN DE CUENTAS ===")
        print("1. Ver Cuentas al Contado")
        print("2. Ver Cuentas por Cobrar")
        print("3. Registrar Abono")
        print("4. Reporte de Pagos Recibidos")
        print("5. Reporte de Cuentas Pendientes")
        print("6. Reporte de Todas las Cuentas")
        print("7. Reporte Individual de Pagos por Cliente")
        print("0. Volver al Menú Principal")
        
        opcion = input(Fore.YELLOW + "\nSeleccione una opción: ").strip()
        
        if opcion == '1':
            ver_cuentas_contado(cuentas_cobrar, clientes)
        elif opcion == '2':
            ver_estado_cuentas(cuentas_cobrar, clientes)
        elif opcion == '3':
            registrar_abono(cuentas_cobrar)
        elif opcion == '4':
            generar_reporte_pagos(cuentas_cobrar, clientes)
        elif opcion == '5':
            generar_reporte_cuentas_pendientes(cuentas_cobrar, clientes)
        elif opcion == '6':
            generar_reporte_todas_cuentas(cuentas_cobrar, clientes)
        elif opcion == '7':
            generar_reporte_pagos_individual(cuentas_cobrar, clientes)
        elif opcion == '0':
            print(Fore.GREEN + "\nVolviendo al menú principal...")
            break
        else:
            print(Fore.RED + "\nOpción inválida.")
    
    return True

# --- Utilidad para pedir rango de fechas mejorada ---
def pedir_rango_fechas():
    print(Fore.CYAN + "\n--- Filtro de Fechas ---")
    print("1. Por año completo")
    print("2. Por mes y año")
    print("3. Por rango de fechas")
    print("4. Sin filtro (todos)")
    while True:
        op = input(Fore.YELLOW + "Seleccione filtro (1-4): ").strip()
        if op == '1':
            anio = input(Fore.YELLOW + "Año (YYYY): ").strip()
            try:
                anio_int = int(anio)
                fecha_ini = datetime.datetime(anio_int, 1, 1)
                fecha_fin = datetime.datetime(anio_int, 12, 31, 23, 59, 59)
                return fecha_ini, fecha_fin
            except ValueError:
                print(Fore.RED + "Año inválido.")
        elif op == '2':
            anio = input(Fore.YELLOW + "Año (YYYY): ").strip()
            mes = input(Fore.YELLOW + "Mes (1-12): ").strip()
            try:
                anio_int = int(anio)
                mes_int = int(mes)
                fecha_ini = datetime.datetime(anio_int, mes_int, 1)
                if mes_int == 12:
                    fecha_fin = datetime.datetime(anio_int, 12, 31, 23, 59, 59)
                else:
                    fecha_fin = datetime.datetime(anio_int, mes_int + 1, 1) - datetime.timedelta(seconds=1)
                return fecha_ini, fecha_fin
            except ValueError:
                print(Fore.RED + "Año o mes inválido.")
        elif op == '3':
            fecha_ini_str = input(Fore.YELLOW + "Fecha inicio (DD/MM/YYYY): ").strip()
            fecha_fin_str = input(Fore.YELLOW + "Fecha fin (DD/MM/YYYY): ").strip()
            try:
                fecha_ini = datetime.datetime.strptime(fecha_ini_str, '%d/%m/%Y')
                fecha_fin = datetime.datetime.strptime(fecha_fin_str, '%d/%m/%Y')
                if fecha_ini > fecha_fin:
                    print(Fore.RED + "La fecha de inicio no puede ser mayor que la de fin.")
                    continue
                fecha_fin = fecha_fin.replace(hour=23, minute=59, second=59)
                return fecha_ini, fecha_fin
            except ValueError:
                print(Fore.RED + "Formato inválido. Use DD/MM/YYYY.")
        elif op == '4':
            return None, None
        else:
            print(Fore.YELLOW + "Opción inválida.")

def obtener_fecha_emision(num_fact):
    try:
        json_path = os.path.join(CARPETA_FACTURAS_JSON, f"factura_{num_fact}.json")
        if os.path.exists(json_path):
            data = cargar_datos(json_path)
            fecha = data.get('fecha')
            if fecha:
                try:
                    dt = datetime.datetime.fromisoformat(fecha)
                    return dt.strftime('%Y-%m-%d %H:%M')
                except Exception:
                    return fecha
    except Exception:
        pass
    return None

# --- Reporte de Todas las Cuentas (LANDSCAPE + FILTRO FECHA, tolerante) ---
def generar_reporte_todas_cuentas(cuentas_cobrar, clientes):
    print(Fore.CYAN + "\n--- Generando Reporte de Todas las Cuentas ---")
    fecha_ini, fecha_fin = pedir_rango_fechas()
    
    # Filtrar cuentas por fecha si se especificó
    cuentas_filtradas = {}
    for k, v in cuentas_cobrar.items():
        fecha_emision = v.get('fecha_emision', None)
        if not fecha_emision:
            fecha_emision = obtener_fecha_emision(k)
        v['fecha_emision'] = fecha_emision
        
        incluir = True
        if fecha_ini and fecha_emision:
            try:
                dt = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d %H:%M')
                if dt < fecha_ini:
                    incluir = False
            except Exception:
                pass
        if fecha_fin and fecha_emision:
            try:
                dt = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d %H:%M')
                if dt > fecha_fin:
                    incluir = False
            except Exception:
                pass
        if incluir:
            cuentas_filtradas[k] = v

    # Crear PDF
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    
    def to_latin1(t):
        txt = str(t) if t is not None else ''
        return txt.encode('latin-1','replace').decode('latin-1')
    
    # Agregar logo
    try:
        if os.path.exists(ARCHIVO_LOGO):
            pdf.image(ARCHIVO_LOGO, x=10, y=8, w=40)
        else:
            print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
    except Exception as e_logo:
        print(f"Adv: Error al cargar el logo: {e_logo}")
    
    # Título y fecha - Centrado
    pdf.set_font('Arial','B',12)
    pdf.cell(0,6,to_latin1(NOMBRE_EMPRESA),0,1,'C')
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C')
    pdf.cell(0,5,f"Telefono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C')
    pdf.ln(5)
    
    # Título del reporte
    pdf.set_font('Arial','B',14)
    pdf.set_text_color(0,0,128)
    pdf.cell(0,8,'REPORTE DE TODAS LAS CUENTAS',0,1,'C')
    pdf.set_text_color(0,0,0)
    pdf.ln(1)
    
    # Fecha de generación
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}',0,1,'R')
    pdf.ln(8)
    
    # Encabezados
    col_w = [18, 25, 40, 28, 18, 18, 25, 25, 22, 22, 22, 22]
    headers = ['Nro Fact', 'RIF', 'Cliente', 'Fecha Emisión', 'Tipo', 'Fecha Pago', 'Hora', 'Método Pago', 'Referencia', 'Total USD', 'Abonado USD', 'Pend. USD']
    pdf.set_font('Arial','B',9)
    pdf.set_fill_color(230,230,230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()
    
    # Datos
    pdf.set_font('Arial','',8)
    total_facturas = 0
    monto_total_facturado = 0
    monto_total_abonado = 0
    monto_total_pendiente = 0
    
    for num_fact, datos in sorted(cuentas_filtradas.items()):
        total_facturas += 1
        rif_cli = datos.get('rif', 'N/A')
        cliente_nombre = to_latin1(clientes.get(rif_cli,{}).get('nombre', 'N/A'))[:25]
        fecha_emision = datos.get('fecha_emision') or obtener_fecha_emision(num_fact) or 'Sin fecha'
        tipo = datos.get('estado', 'N/A').capitalize()
        fecha_pago = datos.get('fecha_ultimo_abono', 'N/A')
        fecha_str, hora_str = 'N/A', 'N/A'
        if fecha_pago and fecha_pago != 'N/A':
            try:
                dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except Exception:
                fecha_str = fecha_pago
        metodo = datos.get('tipo_pago', 'N/A')
        referencia = datos.get('referencia_pago', 'N/A')
        total_usd = datos.get('total_usd', 0)
        abonado = datos.get('abonado_usd', 0)
        pendiente = max(0, total_usd - abonado)
        
        monto_total_facturado += total_usd
        monto_total_abonado += abonado
        monto_total_pendiente += pendiente
        
        row = [num_fact, rif_cli, cliente_nombre, fecha_emision, tipo, fecha_str, hora_str, metodo, referencia,
               f"${total_usd:,.2f}", f"${abonado:,.2f}", f"${pendiente:,.2f}"]
        
        for i, val in enumerate(row):
            align = 'R' if i >= 9 else 'C' if i != 2 else 'L'
            pdf.cell(col_w[i], 6, str(val), 1, 0, align)
        pdf.ln()
    
    # Totales
    if total_facturas > 0:
        pdf.set_font('Arial','B',9)
        pdf.cell(sum(col_w[:9]), 7, 'TOTALES:', 1, 0, 'R', fill=True)
        pdf.cell(col_w[9], 7, f"${monto_total_facturado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[10], 7, f"${monto_total_abonado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[11], 7, f"${monto_total_pendiente:,.2f}", 1, 1, 'R', fill=True)
        
        # Resumen
        pdf.ln(5)
        pdf.set_font('Arial','B',10)
        pdf.cell(0, 7, 'RESUMEN DEL REPORTE:', 0, 1, 'L')
        pdf.set_font('Arial','',9)
        porcentaje_cobrado = (monto_total_abonado / monto_total_facturado * 100) if monto_total_facturado > 0 else 0
        resumen = [
            f"Total de facturas: {total_facturas}",
            f"Monto total facturado: ${monto_total_facturado:,.2f}",
            f"Monto total abonado: ${monto_total_abonado:,.2f}",
            f"Porcentaje cobrado: {porcentaje_cobrado:.1f}%",
            f"Monto total pendiente: ${monto_total_pendiente:,.2f}"
        ]
        for r in resumen:
            pdf.cell(0, 6, r, 0, 1, 'L')
    else:
        pdf.set_font('Arial','B',16)
        pdf.cell(0, 20, 'No hay cuentas registradas en el rango seleccionado.', 0, 1, 'C')
    
    # Guardar PDF
    os.makedirs(CARPETA_REPORTES_CUENTAS, exist_ok=True)
    pdf_fname = os.path.join(CARPETA_REPORTES_CUENTAS, f"reporte_todas_cuentas_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
    pdf.output(pdf_fname)
    print(Fore.GREEN + f"PDF Reporte de Todas las Cuentas: '{pdf_fname}'")
    return True

# --- Reporte de Cuentas Pendientes (LANDSCAPE + FILTRO FECHA, tolerante) ---
def generar_reporte_cuentas_pendientes(cuentas_cobrar, clientes):
    print(Fore.CYAN + "\n--- Generando Reporte de Cuentas Pendientes ---")
    fecha_ini, fecha_fin = pedir_rango_fechas()
    cuentas_pendientes = {}
    for k, v in cuentas_cobrar.items():
        estado = v.get('estado', '').lower()
        if estado in ['por cobrar', 'abonada']:
            fecha_emision = v.get('fecha_emision', None)
            if not fecha_emision:
                fecha_emision = obtener_fecha_emision(k)
            v['fecha_emision'] = fecha_emision
            incluir = True
            if fecha_ini and fecha_emision:
                try:
                    dt = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d %H:%M')
                    if dt < fecha_ini:
                        incluir = False
                except Exception:
                    pass
            if fecha_fin and fecha_emision:
                try:
                    dt = datetime.datetime.strptime(fecha_emision, '%Y-%m-%d %H:%M')
                    if dt > fecha_fin:
                        incluir = False
                except Exception:
                    pass
            if incluir:
                cuentas_pendientes[k] = v
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    def to_latin1(t):
        txt = str(t) if t is not None else ''
        return txt.encode('latin-1','replace').decode('latin-1')
    
    # Agregar logo
    try:
        if os.path.exists(ARCHIVO_LOGO):
            pdf.image(ARCHIVO_LOGO, x=10, y=8, w=40)
        else:
            print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
    except Exception as e_logo:
        print(f"Adv: Error al cargar el logo: {e_logo}")
    
    # Título y fecha - Centrado
    pdf.set_font('Arial','B',12)
    pdf.cell(0,6,to_latin1(NOMBRE_EMPRESA),0,1,'C')
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C')
    pdf.cell(0,5,f"Telefono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C')
    pdf.ln(5)
    
    # Título del reporte
    pdf.set_font('Arial','B',14)
    pdf.set_text_color(0,0,128)
    pdf.cell(0,8,'REPORTE DE CUENTAS PENDIENTES',0,1,'C')
    pdf.set_text_color(0,0,0)
    pdf.ln(1)
    
    # Fecha de generación
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}',0,1,'R')
    pdf.ln(8)
    
    # Resto del código igual...
    col_w = [18, 25, 40, 28, 18, 18, 25, 25, 22, 22, 22, 22]
    headers = ['Nro Fact', 'RIF', 'Cliente', 'Fecha Emisión', 'Tipo', 'Fecha Pago', 'Hora', 'Método Pago', 'Referencia', 'Total USD', 'Abonado USD', 'Pend. USD']
    pdf.set_font('Arial','B',9)
    pdf.set_fill_color(230,230,230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_font('Arial','',8)
    total_facturas = 0
    monto_total_facturado = 0
    monto_total_abonado = 0
    monto_total_pendiente = 0
    for num_fact, datos in sorted(cuentas_pendientes.items()):
        total_facturas += 1
        rif_cli = datos.get('rif', 'N/A')
        cliente_nombre = to_latin1(clientes.get(rif_cli,{}).get('nombre', 'N/A'))[:25]
        fecha_emision = datos.get('fecha_emision') or obtener_fecha_emision(num_fact) or 'Sin fecha'
        tipo = datos.get('estado', 'N/A').capitalize()
        fecha_pago = datos.get('fecha_ultimo_abono', 'N/A')
        fecha_str, hora_str = 'N/A', 'N/A'
        if fecha_pago and fecha_pago != 'N/A':
            try:
                dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except Exception:
                fecha_str = fecha_pago
        metodo = datos.get('tipo_pago', 'N/A')
        referencia = datos.get('referencia_pago', 'N/A')
        total_usd = datos.get('total_usd', 0)
        abonado = datos.get('abonado_usd', 0)
        pendiente = max(0, total_usd - abonado)
        monto_total_facturado += total_usd
        monto_total_abonado += abonado
        monto_total_pendiente += pendiente
        row = [num_fact, rif_cli, cliente_nombre, fecha_emision, tipo, fecha_str, hora_str, metodo, referencia,
               f"${total_usd:,.2f}", f"${abonado:,.2f}", f"${pendiente:,.2f}"]
        for i, val in enumerate(row):
            align = 'R' if i >= 9 else 'C' if i != 2 else 'L'
            pdf.cell(col_w[i], 6, str(val), 1, 0, align)
        pdf.ln()
    if total_facturas == 0:
        pdf.set_font('Arial','B',16)
        pdf.cell(0, 20, 'No hay cuentas pendientes en el rango seleccionado.', 0, 1, 'C')
    else:
        pdf.set_font('Arial','B',9)
        pdf.cell(sum(col_w[:9]), 7, 'TOTALES:', 1, 0, 'R', fill=True)
        pdf.cell(col_w[9], 7, f"${monto_total_facturado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[10], 7, f"${monto_total_abonado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[11], 7, f"${monto_total_pendiente:,.2f}", 1, 1, 'R', fill=True)
        pdf.ln(5)
        pdf.set_font('Arial','B',10)
        pdf.cell(0, 7, 'RESUMEN DEL REPORTE:', 0, 1, 'L')
        pdf.set_font('Arial','',9)
        porcentaje_cobrado = (monto_total_abonado / monto_total_facturado * 100) if monto_total_facturado > 0 else 0
        resumen = [
            f"Total de facturas: {total_facturas}",
            f"Monto total facturado: ${monto_total_facturado:,.2f}",
            f"Monto total abonado: ${monto_total_abonado:,.2f}",
            f"Porcentaje cobrado: {porcentaje_cobrado:.1f}%",
            f"Monto total pendiente: ${monto_total_pendiente:,.2f}"
        ]
        for r in resumen:
            pdf.cell(0, 6, r, 0, 1, 'L')
    os.makedirs(CARPETA_REPORTES_CUENTAS, exist_ok=True)
    pdf_fname = os.path.join(CARPETA_REPORTES_CUENTAS, f"reporte_pendientes_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
    pdf.output(pdf_fname)
    print(Fore.GREEN + f"PDF Reporte de Cuentas Pendientes: '{pdf_fname}'")
    return True

# --- Reporte de Pagos Recibidos (LANDSCAPE + FILTRO FECHA, tolerante, tabla real) ---
def generar_reporte_pagos(cuentas_cobrar, clientes):
    print(Fore.CYAN + "\n--- Generando Reporte de Pagos Recibidos ---")
    fecha_ini, fecha_fin = pedir_rango_fechas()
    pagos_registrados = {}
    for k, v in cuentas_cobrar.items():
        if v.get('abonado_usd', 0) > 0:
            fecha_pago = v.get('fecha_ultimo_abono', None)
            incluir = True
            if fecha_ini and fecha_pago and fecha_pago != 'N/A':
                try:
                    dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                    if dt < fecha_ini:
                        incluir = False
                except Exception:
                    pass
            if fecha_fin and fecha_pago and fecha_pago != 'N/A':
                try:
                    dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                    if dt > fecha_fin:
                        incluir = False
                except Exception:
                    pass
            if incluir:
                pagos_registrados[k] = v
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    def to_latin1(t):
        txt = str(t) if t is not None else ''
        return txt.encode('latin-1','replace').decode('latin-1')
    
    # Agregar logo
    try:
        if os.path.exists(ARCHIVO_LOGO):
            pdf.image(ARCHIVO_LOGO, x=10, y=8, w=40)
        else:
            print(f"Adv: Logo '{ARCHIVO_LOGO}' no encontrado.")
    except Exception as e_logo:
        print(f"Adv: Error al cargar el logo: {e_logo}")
    
    # Título y fecha - Centrado
    pdf.set_font('Arial','B',12)
    pdf.cell(0,6,to_latin1(NOMBRE_EMPRESA),0,1,'C')
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f"RIF: {to_latin1(RIF_EMPRESA)}",0,1,'C')
    pdf.cell(0,5,f"Telefono: {to_latin1(TELEFONO_EMPRESA)}",0,1,'C')
    pdf.ln(5)
    
    # Título del reporte
    pdf.set_font('Arial','B',14)
    pdf.set_text_color(0,0,128)
    pdf.cell(0,8,'REPORTE DE PAGOS RECIBIDOS',0,1,'C')
    pdf.set_text_color(0,0,0)
    pdf.ln(1)
    
    # Fecha de generación
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}',0,1,'R')
    pdf.ln(8)
    
    # Resto del código igual...
    col_w = [18, 25, 40, 28, 18, 18, 25, 25, 22, 22, 22, 22]
    headers = ['Nro Fact', 'RIF', 'Cliente', 'Fecha Emisión', 'Tipo', 'Fecha Pago', 'Hora', 'Método Pago', 'Referencia', 'Total USD', 'Abonado USD', 'Pend. USD']
    pdf.set_font('Arial','B',9)
    pdf.set_fill_color(230,230,230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_font('Arial','',8)
    total_facturas = 0
    total_contado = 0
    total_credito = 0
    monto_total_facturado = 0
    monto_total_abonado = 0
    monto_total_pendiente = 0
    for num_fact, datos in sorted(pagos_registrados.items()):
        total_facturas += 1
        rif_cli = datos.get('rif', 'N/A')
        cliente_nombre = to_latin1(clientes.get(rif_cli,{}).get('nombre', 'N/A'))[:25]
        fecha_emision = datos.get('fecha_emision') or obtener_fecha_emision(num_fact) or 'Sin fecha'
        tipo = datos.get('estado', 'N/A').capitalize() if datos.get('estado','').lower() in ['cobrada','abonada'] else 'Crédito'
        if tipo.lower() == 'cobrada' or datos.get('tipo_pago','').lower() == 'contado':
            total_contado += datos.get('total_usd', 0)
        else:
            total_credito += datos.get('total_usd', 0)
        fecha_pago = datos.get('fecha_ultimo_abono', 'N/A')
        fecha_str, hora_str = 'N/A', 'N/A'
        if fecha_pago and fecha_pago != 'N/A':
            try:
                dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except Exception:
                fecha_str = fecha_pago
        metodo = datos.get('tipo_pago', 'N/A')
        referencia = datos.get('referencia_pago', 'N/A')
        total_usd = datos.get('total_usd', 0)
        abonado = datos.get('abonado_usd', 0)
        pendiente = max(0, total_usd - abonado)
        monto_total_facturado += total_usd
        monto_total_abonado += abonado
        monto_total_pendiente += pendiente
        row = [num_fact, rif_cli, cliente_nombre, fecha_emision, tipo, fecha_str, hora_str, metodo, referencia,
               f"${total_usd:,.2f}", f"${abonado:,.2f}", f"${pendiente:,.2f}"]
        for i, val in enumerate(row):
            align = 'R' if i >= 9 else 'C' if i != 2 else 'L'
            pdf.cell(col_w[i], 6, str(val), 1, 0, align)
        pdf.ln()
    if total_facturas == 0:
        pdf.set_font('Arial','B',16)
        pdf.cell(0, 20, 'No hay pagos registrados en el rango seleccionado.', 0, 1, 'C')
    else:
        pdf.set_font('Arial','B',9)
        pdf.cell(sum(col_w[:9]), 7, 'TOTALES:', 1, 0, 'R', fill=True)
        pdf.cell(col_w[9], 7, f"${monto_total_facturado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[10], 7, f"${monto_total_abonado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[11], 7, f"${monto_total_pendiente:,.2f}", 1, 1, 'R', fill=True)
        pdf.ln(5)
        pdf.set_font('Arial','B',10)
        pdf.cell(0, 7, 'RESUMEN DEL REPORTE:', 0, 1, 'L')
        pdf.set_font('Arial','',9)
        porcentaje_cobrado = (monto_total_abonado / monto_total_facturado * 100) if monto_total_facturado > 0 else 0
        resumen = [
            f"Total de facturas: {total_facturas}",
            f"Total facturas al contado: ${total_contado:,.2f}",
            f"Total facturas a crédito: ${total_credito:,.2f}",
            f"Monto total facturado: ${monto_total_facturado:,.2f}",
            f"Monto total abonado: ${monto_total_abonado:,.2f}",
            f"Porcentaje cobrado: {porcentaje_cobrado:.1f}%",
            f"Monto total pendiente: ${monto_total_pendiente:,.2f}"
        ]
        for r in resumen:
            pdf.cell(0, 6, r, 0, 1, 'L')
    os.makedirs(CARPETA_REPORTES_PAGOS, exist_ok=True)
    pdf_fname = os.path.join(CARPETA_REPORTES_PAGOS, f"reporte_pagos_general_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
    pdf.output(pdf_fname)
    print(Fore.GREEN + f"PDF Reporte de Pagos: '{pdf_fname}'")
    return True

# --- Reporte Individual de Pagos por Cliente ---
def generar_reporte_pagos_individual(cuentas_cobrar, clientes):
    print(Fore.CYAN + "\n--- Reporte Individual de Pagos por Cliente ---")
    rif = input(Fore.YELLOW + "Ingrese el RIF del cliente: ").strip().upper()
    if rif not in clientes:
        print(Fore.RED + "Cliente no encontrado.")
        return
    fecha_ini, fecha_fin = pedir_rango_fechas()
    pagos_cliente = {}
    for k, v in cuentas_cobrar.items():
        if v.get('rif', '').upper() == rif and v.get('abonado_usd', 0) > 0:
            fecha_pago = v.get('fecha_ultimo_abono', None)
            incluir = True
            if fecha_ini and fecha_pago and fecha_pago != 'N/A':
                try:
                    dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                    if dt < fecha_ini:
                        incluir = False
                except Exception:
                    pass
            if fecha_fin and fecha_pago and fecha_pago != 'N/A':
                try:
                    dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                    if dt > fecha_fin:
                        incluir = False
                except Exception:
                    pass
            if incluir:
                pagos_cliente[k] = v
    pdf = FPDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    def to_latin1(t):
        txt = str(t) if t is not None else ''
        return txt.encode('latin-1','replace').decode('latin-1')
    pdf.set_font('Arial','B',14)
    nombre_cliente = to_latin1(clientes[rif].get('nombre', rif))
    pdf.cell(0,10,f'Reporte de Pagos Recibidos - {nombre_cliente}',0,1,'C')
    pdf.ln(5)
    pdf.set_font('Arial','',10)
    pdf.cell(0,5,f'Generado el: {datetime.datetime.now().strftime("%d/%m/%Y %H:%M")}',0,1,'R')
    pdf.ln(8)
    col_w = [18, 28, 18, 18, 25, 25, 22, 22, 22, 22]
    headers = ['Nro Fact', 'Fecha Emisión', 'Tipo', 'Fecha Pago', 'Hora', 'Método Pago', 'Referencia', 'Total USD', 'Abonado USD', 'Pend. USD']
    pdf.set_font('Arial','B',9)
    pdf.set_fill_color(230,230,230)
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 8, h, 1, 0, 'C', fill=True)
    pdf.ln()
    pdf.set_font('Arial','',8)
    total_facturas = 0
    monto_total_facturado = 0
    monto_total_abonado = 0
    monto_total_pendiente = 0
    for num_fact, datos in sorted(pagos_cliente.items()):
        total_facturas += 1
        fecha_emision = datos.get('fecha_emision') or obtener_fecha_emision(num_fact) or 'Sin fecha'
        tipo = datos.get('estado', 'N/A').capitalize() if datos.get('estado','').lower() in ['cobrada','abonada'] else 'Crédito'
        fecha_pago = datos.get('fecha_ultimo_abono', 'N/A')
        fecha_str, hora_str = 'N/A', 'N/A'
        if fecha_pago and fecha_pago != 'N/A':
            try:
                dt = datetime.datetime.strptime(fecha_pago, '%Y-%m-%d %H:%M')
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except Exception:
                fecha_str = fecha_pago
        metodo = datos.get('tipo_pago', 'N/A')
        referencia = datos.get('referencia_pago', 'N/A')
        total_usd = datos.get('total_usd', 0)
        abonado = datos.get('abonado_usd', 0)
        pendiente = max(0, total_usd - abonado)
        monto_total_facturado += total_usd
        monto_total_abonado += abonado
        monto_total_pendiente += pendiente
        row = [num_fact, fecha_emision, tipo, fecha_str, hora_str, metodo, referencia,
               f"${total_usd:,.2f}", f"${abonado:,.2f}", f"${pendiente:,.2f}"]
        for i, val in enumerate(row):
            align = 'R' if i >= 7 else 'C'
            pdf.cell(col_w[i], 6, str(val), 1, 0, align)
        pdf.ln()
    if total_facturas == 0:
        pdf.set_font('Arial','B',16)
        pdf.cell(0, 20, 'No hay pagos registrados para este cliente en el rango seleccionado.', 0, 1, 'C')
    else:
        pdf.set_font('Arial','B',9)
        pdf.cell(sum(col_w[:7]), 7, 'TOTALES:', 1, 0, 'R', fill=True)
        pdf.cell(col_w[7], 7, f"${monto_total_facturado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[8], 7, f"${monto_total_abonado:,.2f}", 1, 0, 'R', fill=True)
        pdf.cell(col_w[9], 7, f"${monto_total_pendiente:,.2f}", 1, 1, 'R', fill=True)
        pdf.ln(5)
        pdf.set_font('Arial','B',10)
        pdf.cell(0, 7, 'RESUMEN DEL REPORTE:', 0, 1, 'L')
        pdf.set_font('Arial','',9)
        porcentaje_cobrado = (monto_total_abonado / monto_total_facturado * 100) if monto_total_facturado > 0 else 0
        resumen = [
            f"Total de facturas: {total_facturas}",
            f"Monto total facturado: ${monto_total_facturado:,.2f}",
            f"Monto total abonado: ${monto_total_abonado:,.2f}",
            f"Porcentaje cobrado: {porcentaje_cobrado:.1f}%",
            f"Monto total pendiente: ${monto_total_pendiente:,.2f}"
        ]
        for r in resumen:
            pdf.cell(0, 6, r, 0, 1, 'L')
    os.makedirs(CARPETA_REPORTES_PAGOS, exist_ok=True)
    pdf_fname = os.path.join(CARPETA_REPORTES_PAGOS, f"reporte_pagos_{rif}_{datetime.datetime.now():%Y%m%d_%H%M%S}.pdf")
    pdf.output(pdf_fname)
    print(Fore.GREEN + f"PDF Reporte de Pagos Individual: '{pdf_fname}'")
    return True

# --- Función del Menú Principal ---
def mostrar_menu():
    print(Fore.CYAN + Style.BRIGHT + "\n=== SISTEMA DE FACTURACIÓN ===")
    print("1. Crear Factura")
    print("2. Gestionar Facturas")
    print("3. Gestionar Clientes")
    print("4. Gestionar Inventario")
    print("5. Calcular Valor Inventario")
    print("6. Generar PDF Inventario")
    print("7. Ajustar Stock (Entrada)")
    print("8. Ajustar Stock (Salida)")
    print("9. Cargar Inventario desde CSV")
    print("10. Cargar Clientes desde CSV")
    print("11. Generar PDF Historial Cliente")
    print("12. Generar PDF Reporte General")
    print("13. Crear Cotización")
    print("14. Gestionar Cuentas por Cobrar")
    print("0. Salir")
    return input(Fore.YELLOW + "\nSeleccione una opción: ").strip()

# --- Funciones de Menú ---
def menu_clientes(clientes):
    while True:
        print(Fore.CYAN + Style.BRIGHT + "\n=== GESTIÓN DE CLIENTES ===")
        print("1. Agregar/Modificar Cliente")
        print("2. Buscar Cliente")
        print("3. Listar Clientes")
        print("4. Eliminar Cliente")
        print("0. Volver")
        op = input(Fore.YELLOW + "\nSeleccione: ").strip()
        if op == '1': agregar_o_modificar_cliente(clientes)
        elif op == '2': buscar_cliente_por_rif(clientes)
        elif op == '3': listar_clientes(clientes)
        elif op == '4': eliminar_cliente(clientes)
        elif op == '0': break
        else: print(Fore.YELLOW + "Opción inválida.")

def menu_inventario(inventario):
    while True:
        print(Fore.CYAN + Style.BRIGHT + "\n=== GESTIÓN DE INVENTARIO ===")
        print("1. Agregar/Modificar Producto")
        print("2. Listar Productos")
        print("3. Eliminar Producto")
        print("0. Volver")
        op = input(Fore.YELLOW + "\nSeleccione: ").strip()
        if op == '1': agregar_o_modificar_producto(inventario)
        elif op == '2': listar_productos(inventario)
        elif op == '3': eliminar_producto(inventario)
        elif op == '0': break
        else: print(Fore.YELLOW + "Opción inválida.")

def menu_ajustar_stock(inventario, tipo_mov):
    print(Fore.CYAN + f"\n--- Ajuste de Stock ({tipo_mov.upper()}) ---")
    pid = input("ID del producto: ").strip().upper()
    prod = get_producto(inventario, pid)
    if not prod:
        print(Fore.RED + f"Producto {pid} no encontrado.")
        return
    print(f"\nProducto: {prod['nombre']}")
    print(f"Stock actual: {prod.get('cantidad', 0)}")
    try:
        cant = int(input(f"Cantidad a {tipo_mov}: ").strip())
        if cant <= 0:
            print(Fore.YELLOW + "Cantidad debe ser positiva.")
            return
        if tipo_mov == 'salida' and cant > prod.get('cantidad', 0):
            print(Fore.RED + "Stock insuficiente.")
            return
        if ajustar_stock(inventario, pid, cant if tipo_mov == 'entrada' else -cant, tipo_mov):
            print(Fore.GREEN + "Stock actualizado.")
        else:
            print(Fore.RED + "Error actualizando stock.")
    except ValueError:
        print(Fore.YELLOW + "Cantidad inválida.")

def menu_gestion_facturas(historial_facturas, clientes, inventario, cuentas_cobrar):
    def resumen_factura(f):
        print("\n--- Resumen de la Factura ---")
        print(f"Nro: {f.get('numero_factura','N/A')}")
        fecha = f.get('fecha','N/A')
        try:
            fecha_legible = datetime.datetime.fromisoformat(fecha).strftime('%d/%m/%Y %H:%M')
        except:
            fecha_legible = fecha
        print(f"Fecha: {fecha_legible}")
        cli = f.get('cliente',{})
        print(f"Cliente: {cli.get('nombre','N/A')} | RIF: {cli.get('rif','N/A')}")
        print(f"Total USD: {f.get('total_usd',0):,.2f}")
        print("Productos:")
        for item in f.get('items', []):
            print(f"  - {item.get('cantidad',0)} x {item.get('nombre','')} (${item.get('precio_unitario_usd',0):,.2f} c/u)")
        print("---------------------------")

    while True:
        print(Fore.CYAN + Style.BRIGHT + "\n=== GESTIÓN DE FACTURAS ===")
        print("1. Ver Historial de Facturas")
        print("2. Regenerar PDF de Factura")
        print("3. Editar Fecha/Hora de Factura")
        print("4. Eliminar Factura")
        print("0. Volver")
        op = input(Fore.YELLOW + "\nSeleccione: ").strip()
        if op == '1':
            if not historial_facturas:
                print(Fore.YELLOW + "No hay facturas en el historial.")
                continue
            print(Fore.CYAN + "\n--- Historial de Facturas ---")
            print(f"{'Nro':<8} {'Fecha':<12} {'Cliente':<30} {'Total USD':>12}")
            print("-" * 65)
            for f in historial_facturas:
                num = f.get('numero_factura', 'N/A')
                fecha = datetime.datetime.fromisoformat(f.get('fecha', '')).strftime('%d/%m/%Y') if f.get('fecha') else 'N/A'
                cliente = f.get('cliente', {}).get('nombre', 'N/A')[:30]
                total = f"{f.get('total_usd', 0):,.2f}"
                print(f"{num:<8} {fecha:<12} {cliente:<30} ${total:>12}")
        elif op == '2':
            num_fact = input("\nNúmero de factura a regenerar: ").strip()
            factura = next((f for f in historial_facturas if f.get('numero_factura') == num_fact), None)
            if factura:
                resumen_factura(factura)
                n_pdf = os.path.join(CARPETA_FACTURAS_PDF, f"factura_{num_fact}.pdf")
                if generar_pdf_factura(factura, n_pdf):
                    print(Fore.GREEN + f"PDF regenerado: '{n_pdf}'")
                else:
                    print(Fore.RED + "Error regenerando PDF.")
            else:
                print(Fore.YELLOW + f"Factura {num_fact} no encontrada.")
        elif op == '3':
            num_fact = input("\nNúmero de factura a editar fecha/hora: ").strip()
            factura = next((f for f in historial_facturas if f.get('numero_factura') == num_fact), None)
            if not factura:
                print(Fore.YELLOW + f"Factura {num_fact} no encontrada.")
                continue
            resumen_factura(factura)
            print(f"Fecha actual: {factura.get('fecha','N/A')}")
            nueva_fecha = input("Nueva fecha y hora (DD/MM/YYYY HH:MM o DD/MM/YYYY HH:MM:SS): ").strip()
            dt = None
            for fmt in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M'):
                try:
                    dt = datetime.datetime.strptime(nueva_fecha, fmt)
                    break
                except Exception:
                    continue
            if dt is None:
                print(Fore.RED + "Formato inválido. Usa DD/MM/YYYY HH:MM o DD/MM/YYYY HH:MM:SS")
                continue
            factura['fecha'] = dt.isoformat()
            # Guardar en JSON
            json_path = os.path.join(CARPETA_FACTURAS_JSON, f"factura_{num_fact}.json")
            guardar_datos(factura, json_path)
            print(Fore.GREEN + "Fecha/hora actualizada.")
        elif op == '4':
            num_fact = input("\nNúmero de factura a ELIMINAR: ").strip()
            factura = next((f for f in historial_facturas if f.get('numero_factura') == num_fact), None)
            if not factura:
                print(Fore.YELLOW + f"Factura {num_fact} no encontrada.")
                continue
            resumen_factura(factura)
            conf = input(Fore.RED + f"¿Seguro que desea ELIMINAR la factura {num_fact}? (s/n): ").strip().lower()
            if conf == 's':
                json_path = os.path.join(CARPETA_FACTURAS_JSON, f"factura_{num_fact}.json")
                pdf_path = os.path.join(CARPETA_FACTURAS_PDF, f"factura_{num_fact}.pdf")
                try:
                    if os.path.exists(json_path): os.remove(json_path)
                    if os.path.exists(pdf_path): os.remove(pdf_path)
                    print(Fore.GREEN + f"Factura {num_fact} eliminada.")
                except Exception as e:
                    print(Fore.RED + f"Error eliminando archivos: {e}")
            else:
                print("Eliminación cancelada.")
        elif op == '0':
            break
        else:
            print(Fore.YELLOW + "Opción inválida.")
    return True

# --- Bloque Principal ---
if __name__ == "__main__":
    # Crear carpetas necesarias
    for folder in [CARPETA_FACTURAS_JSON, CARPETA_FACTURAS_PDF, CARPETA_IMAGENES,
                  CARPETA_LISTAS_INVENTARIO, CARPETA_HISTORIAL_CLIENTES, CARPETA_REPORTES_GENERALES,
                  CARPETA_REPORTES_FACTURAS, CARPETA_REPORTES_CUENTAS, CARPETA_REPORTES_PAGOS,
                  CARPETA_COTIZACIONES_JSON, CARPETA_COTIZACIONES_PDF]:
        os.makedirs(folder, exist_ok=True)
    clientes=cargar_clientes(); inventario=cargar_inventario(); config=cargar_configuracion()
    cuentas_cobrar = cargar_cuentas_cobrar()
    if not isinstance(config,dict): config={}; config.setdefault('proximo_numero_factura',1)
    print(Fore.BLUE + f"Cli:{len(clientes)}, Prod:{len(inventario)}, PróxFact:{config.get('proximo_numero_factura',1):04d}, CxC:{len(cuentas_cobrar)}")
    historial_facturas_cache = None

    while True:
        opcion = mostrar_menu()
        if opcion in ['2', '11', '12', '14'] and historial_facturas_cache is None:
             print(Fore.BLUE + "Cargando historial de facturas...")
             historial_facturas_cache = cargar_todas_las_facturas()
             if not historial_facturas_cache and opcion != '2': print(Fore.YELLOW + "No hay historial disponible."); continue

        if opcion == '1': # Crear Factura
            if crear_factura(clientes, inventario, config):
                print(Fore.YELLOW + "Recargando todos los datos...")
                clientes = cargar_clientes()
                inventario = cargar_inventario()
                config = cargar_configuracion()
                cuentas_cobrar = cargar_cuentas_cobrar()
                historial_facturas_cache = None
        elif opcion == '2': # Gestionar Facturas
            historial_a_pasar = cargar_historial_facturas() if historial_facturas_cache is None else historial_facturas_cache
            if menu_gestion_facturas(historial_a_pasar, clientes, inventario, cuentas_cobrar):
                print(Fore.YELLOW + "Recargando todos los datos...")
                clientes = cargar_clientes()
                inventario = cargar_inventario()
                config = cargar_configuracion()
                cuentas_cobrar = cargar_cuentas_cobrar()
                historial_facturas_cache = None
        elif opcion == '3': menu_clientes(clientes); clientes = cargar_clientes()
        elif opcion == '4': menu_inventario(inventario); inventario = cargar_inventario()
        elif opcion == '5': calcular_valor_inventario(inventario)
        elif opcion == '6': generar_pdf_inventario(inventario)
        elif opcion == '7': menu_ajustar_stock(inventario, 'entrada'); inventario = cargar_inventario()
        elif opcion == '8': menu_ajustar_stock(inventario, 'salida'); inventario = cargar_inventario()
        elif opcion == '9': inventario = cargar_inventario_desde_csv(inventario); print("\nVolviendo...")
        elif opcion == '10': clientes = cargar_clientes_desde_csv(clientes); print("\nVolviendo...")
        elif opcion == '11': # PDF Historial Cliente
             if historial_facturas_cache is not None: generar_pdf_historial_cliente(clientes, historial_facturas_cache)
             else: print(Fore.YELLOW + "No hay historial.")
        elif opcion == '12': # PDF Reporte General
             if historial_facturas_cache is not None: generar_pdf_reporte_top(clientes, inventario, historial_facturas_cache)
             else: print(Fore.YELLOW + "No hay historial.")
        elif opcion == '13': # Crear Cotización
            crear_cotizacion(clientes, inventario)
        elif opcion == '14': # Gestionar Cuentas por Cobrar
             menu_gestion_cuentas(cuentas_cobrar, clientes); cuentas_cobrar = cargar_cuentas_cobrar()
        elif opcion == '0': print(Fore.RED + "Saliendo..."); break
        else: print(Fore.YELLOW + "Opción inválida.")

def cargar_historial_facturas():
    print(Fore.BLUE + "Cargando historial de facturas...")
    historial = cargar_todas_las_facturas()
    if not historial:
        print(Fore.YELLOW + "No hay facturas en el historial.")
    return historial

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

def mostrar_interfaz_principal():
    try:
        root = tk.Tk()
        root.title("Sistema de Facturación")
        root.geometry("400x300")
        root.configure(bg="#f0f0f0")

        # Título
        titulo = tk.Label(root, text="Sistema de Facturación", font=("Arial", 16, "bold"), bg="#f0f0f0")
        titulo.pack(pady=20)

        # Frame para botones
        frame_botones = tk.Frame(root, bg="#f0f0f0")
        frame_botones.pack(pady=10)

        # Botones para cada módulo
        botones = [
            ("Crear Factura", lambda: messagebox.showinfo("Info", "Módulo: Crear Factura")),
            ("Gestionar Facturas", lambda: messagebox.showinfo("Info", "Módulo: Gestionar Facturas")),
            ("Gestionar Clientes", lambda: messagebox.showinfo("Info", "Módulo: Gestionar Clientes")),
            ("Gestionar Inventario", lambda: messagebox.showinfo("Info", "Módulo: Gestionar Inventario")),
            ("Crear Cotización", lambda: messagebox.showinfo("Info", "Módulo: Crear Cotización")),
            ("Cuentas por Cobrar", lambda: messagebox.showinfo("Info", "Módulo: Cuentas por Cobrar")),
            ("Salir", root.destroy)
        ]

        for texto, comando in botones:
            boton = tk.Button(frame_botones, text=texto, command=comando, width=20, height=2)
            boton.pack(pady=5)

        root.mainloop()
    except Exception as e:
        print(f"Error al iniciar la interfaz Tkinter: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    mostrar_interfaz_principal()