from functools import wraps
from flask import session, redirect, url_for, flash
import json
import os
from werkzeug.security import check_password_hash

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario' not in session:
            flash('Debe iniciar sesión para acceder a esta página', 'warning')
            return redirect(url_for('login'))
        
        # Cargar usuarios
        if os.path.exists('usuarios.json'):
            with open('usuarios.json', 'r', encoding='utf-8') as f:
                usuarios = json.load(f)
        else:
            usuarios = {}
            
        user = usuarios.get(session['usuario'])
        if not user or not user.get('is_admin', False):
            flash('No tiene permisos de administrador para acceder a esta página', 'danger')
            return redirect(url_for('index'))
            
        return f(*args, **kwargs)
    return decorated_function

def verify_password(username, password):
    """Verifica las credenciales del usuario"""
    if os.path.exists('usuarios.json'):
        with open('usuarios.json', 'r', encoding='utf-8') as f:
            usuarios = json.load(f)
    else:
        usuarios = {}
        
    user = usuarios.get(username)
    if user and check_password_hash(user['password'], password):
        return True
    return False 