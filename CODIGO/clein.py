import streamlit as st
import pandas as pd
import hashlib
import os
import re
from datetime import datetime
import io
import yaml
from pathlib import Path
import glob
# pip install streamlit-authenticator==0.2.2
import streamlit_authenticator as stauth

# Intentar importar plotly 
try:
    import plotly.express as px
    import plotly.graph_objects as go
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# CONSTANTES DEL SISTEMA
# ==========================================
CSV_FILE = "registro_documentos.csv"
# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Sistema de Gestión Documental",
    page_icon="�",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# FUNCIONES DE BLOCKCHAIN POR DOCUMENTO
# ==========================================

def crear_bloque_genesis(hash_doc, datos_documento):
    """Crea el bloque génesis para un nuevo documento"""
    bloque = {
        'numero_bloque': 0,
        'hash_documento': hash_doc,
        'nombre_documento': datos_documento['NOMBRE'],
        'tipo': datos_documento['TIPO'],
        'fecha_creacion': datos_documento['FECHA_CREACION'],
        'fecha_actualizacion': datos_documento['FECHA_ACTUALIZACION'],
        'version': datos_documento['VERSION'],
        'estatus': datos_documento['ESTATUS'],
        'modificacion': datos_documento['MODIFICACION'],
        'creador': datos_documento['CREADOR'],
        'area': datos_documento['AREA'],
        'revisor': datos_documento['REVISOR'],
        'aprobador': datos_documento['APROBADOR'],
        'no_conformidad': datos_documento['NO_CONFORMIDAD'],
        'auditoria': datos_documento['AUDITORIA'],
        'hash_bloque_anterior': '0',
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'accion': 'Documento Creado'
    }
    return bloque

def calcular_hash_bloque(bloque):
    """Calcula el hash SHA-256 de un bloque"""
    bloque_string = f"{bloque['numero_bloque']}{bloque['hash_documento']}{bloque['timestamp']}{bloque['accion']}{bloque['hash_bloque_anterior']}"
    return hashlib.sha256(bloque_string.encode()).hexdigest()

def agregar_bloque_a_cadena(hash_doc, accion, datos_modificacion=None):
    """Agrega un nuevo bloque a la cadena de un documento"""
    blockchain_path = f"blockchain_{hash_doc[:16]}.csv"
    
    # Cargar cadena existente o crear nueva
    if os.path.exists(blockchain_path):
        try:
            df_blockchain = pd.read_csv(blockchain_path)
            ultimo_numero = df_blockchain['numero_bloque'].max()
            ultimo_hash = df_blockchain[df_blockchain['numero_bloque'] == ultimo_numero]['hash_bloque'].iloc[0]
        except:
            return crear_nueva_cadena(hash_doc, datos_modificacion)
    else:
        return crear_nueva_cadena(hash_doc, datos_modificacion)
    
    # Crear nuevo bloque
    nuevo_numero = ultimo_numero + 1
    usuario_actual = st.session_state.get('name', '')
    
    nuevo_bloque = {
        'numero_bloque': nuevo_numero,
        'hash_documento': hash_doc,
        'nombre_documento': datos_modificacion.get('NOMBRE', '') if datos_modificacion else '',
        'tipo': datos_modificacion.get('TIPO', '') if datos_modificacion else '',
        'fecha_creacion': datos_modificacion.get('FECHA_CREACION', '') if datos_modificacion else '',
        'fecha_actualizacion': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'version': datos_modificacion.get('VERSION', '') if datos_modificacion else '',
        'estatus': datos_modificacion.get('ESTATUS', '') if datos_modificacion else '',
        'modificacion': datos_modificacion.get('MODIFICACION', '') if datos_modificacion else f"{accion} por {usuario_actual}",
        'creador': datos_modificacion.get('CREADOR', '') if datos_modificacion else '',
        'area': datos_modificacion.get('AREA', '') if datos_modificacion else '',
        'revisor': datos_modificacion.get('REVISOR', '') if datos_modificacion else '',
        'aprobador': datos_modificacion.get('APROBADOR', '') if datos_modificacion else '',
        'no_conformidad': datos_modificacion.get('NO_CONFORMIDAD', '') if datos_modificacion else '',
        'auditoria': datos_modificacion.get('AUDITORIA', '') if datos_modificacion else '',
        'hash_bloque_anterior': ultimo_hash,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'accion': accion,
        'usuario_accion': usuario_actual
    }
    
    # Calcular hash del nuevo bloque
    nuevo_bloque['hash_bloque'] = calcular_hash_bloque(nuevo_bloque)
    
    # Agregar a la cadena
    df_nuevo_bloque = pd.DataFrame([nuevo_bloque])
    df_blockchain_actualizada = pd.concat([df_blockchain, df_nuevo_bloque], ignore_index=True)
    
    # Guardar cadena actualizada
    df_blockchain_actualizada.to_csv(blockchain_path, index=False)
    return True

def crear_nueva_cadena(hash_doc, datos_documento):
    """Crea una nueva cadena blockchain para un documento"""
    blockchain_path = f"blockchain_{hash_doc[:16]}.csv"
    
    # Crear bloque génesis
    bloque_genesis = crear_bloque_genesis(hash_doc, datos_documento)
    bloque_genesis['hash_bloque'] = calcular_hash_bloque(bloque_genesis)
    bloque_genesis['usuario_accion'] = datos_documento['CREADOR']
    
    # Guardar como CSV
    df_blockchain = pd.DataFrame([bloque_genesis])
    df_blockchain.to_csv(blockchain_path, index=False)
    return True

def cargar_blockchain_documento(hash_doc):
    """Carga la cadena blockchain completa de un documento"""
    blockchain_path = f"blockchain_{hash_doc[:16]}.csv"
    
    if not os.path.exists(blockchain_path):
        return pd.DataFrame()
    
    try:
        df_blockchain = pd.read_csv(blockchain_path)
        return df_blockchain.sort_values('numero_bloque')
    except:
        return pd.DataFrame()

def validar_integridad_cadena(hash_doc):
    """Valida la integridad de una cadena blockchain"""
    df_blockchain = cargar_blockchain_documento(hash_doc)
    
    if df_blockchain.empty:
        return False, "Cadena no encontrada"
    
    for idx, bloque in df_blockchain.iterrows():
        # Validar hash del bloque
        hash_calculado = calcular_hash_bloque(bloque.to_dict())
        if hash_calculado != bloque['hash_bloque']:
            return False, f"Hash inválido en bloque {bloque['numero_bloque']}"
        
        # Validar enlace con bloque anterior (excepto génesis)
        if bloque['numero_bloque'] > 0:
            bloque_anterior = df_blockchain[df_blockchain['numero_bloque'] == bloque['numero_bloque'] - 1]
            if not bloque_anterior.empty:
                if bloque['hash_bloque_anterior'] != bloque_anterior.iloc[0]['hash_bloque']:
                    return False, f"Enlace roto en bloque {bloque['numero_bloque']}"
    
    return True, "Cadena íntegra"

# ==========================================
# FUNCIONES UTILITARIAS
# ==========================================

def calcular_hash(archivo_bytes):
    """Calcula el hash SHA-256 de un archivo"""
    sha256_hash = hashlib.sha256()
    sha256_hash.update(archivo_bytes)
    return sha256_hash.hexdigest()

def cargar_registros():
    """Carga los registros desde el CSV y asegura que las columnas requeridas existan"""
    columnas = [
        'HASH', 'NOMBRE', 'TIPO', 'FECHA_CREACION', 'FECHA_ACTUALIZACION', 
        'VERSION', 'ESTATUS', 'MODIFICACION', 'CREADOR', 'AREA', 'REVISOR', 
        'APROBADOR', 'NO_CONFORMIDAD', 'AUDITORIA'
    ]
    
    csv_path = "registro_documentos.csv"
    if os.path.exists(csv_path):
        try:
            df = pd.read_csv(csv_path)
            for col in columnas:
                if col not in df.columns:
                    df[col] = ""
            return df[columnas]  # Devolver con columnas ordenadas
        except:
            return pd.DataFrame(columns=columnas)
    else:
        return pd.DataFrame(columns=columnas)

def crear_dataframe_vacio():
    """Crea un DataFrame vacío con las columnas necesarias"""
    columnas = [
        'HASH', 'NOMBRE', 'TIPO', 'FECHA_CREACION', 'FECHA_ACTUALIZACION', 
        'VERSION', 'ESTATUS', 'MODIFICACION', 'CREADOR', 'AREA', 'REVISOR', 
        'APROBADOR', 'NO_CONFORMIDAD', 'AUDITORIA'
    ]
    return pd.DataFrame(columns=columnas)

def hash_ya_existe(hash_valor, df):
    """Verifica si el hash ya existe en el registro"""
    if df.empty:
        return False
    return hash_valor in df['HASH'].values

def detectar_tipo_archivo(nombre_archivo):
    """Detecta el tipo de documento basado en el nombre"""
    nombre_lower = nombre_archivo.lower()
    
    tipos = {
        r'(manual|guia|instructivo)': 'Manual',
        r'(contrato|convenio|acuerdo)': 'Contrato',
        r'(politica|norma|lineamiento)': 'Política',
        r'(procedimiento|proceso|flujo)': 'Procedimiento',
        r'(reporte|informe)': 'Reporte',
        r'(formato|plantilla|template)': 'Formato',
        r'(especificacion|spec)': 'Especificación',
        r'(plan|planificacion)': 'Plan',
        r'(acta|minuta)': 'Acta',
        r'(presupuesto|budget)': 'Presupuesto'
    }
    
    import re
    for patron, tipo in tipos.items():
        if re.search(patron, nombre_lower):
            return tipo
    
    return 'Documento'

def detectar_version(nombre_archivo):
    """Detecta la versión del archivo"""
    import re
    patrones_version = [
        r'[_\-\s]v(\d+(?:\.\d+)*)',
        r'[_\-\s]version[_\-\s]*(\d+(?:\.\d+)*)',
        r'[_\-\s]ver[_\-\s]*(\d+(?:\.\d+)*)',
        r'[_\-\s](\d+\.\d+)',
        r'[_\-\s](\d+)(?=\.|_|$)'
    ]
    
    for patron in patrones_version:
        match = re.search(patron, nombre_archivo, re.IGNORECASE)
        if match:
            version = match.group(1)
            return f"v{version}" if not version.startswith('v') else version
    
    return "1.0"

def limpiar_nombre_archivo(nombre_archivo):
    """Limpia el nombre del archivo removiendo versiones y caracteres especiales"""
    import re
    # Remover extensión
    nombre = os.path.splitext(nombre_archivo)[0]
    
    # Remover versiones
    nombre = re.sub(r'[_\-\s]*v\d+(?:\.\d+)*', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'[_\-\s]*version[_\-\s]*\d+(?:\.\d+)*', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'[_\-\s]*ver[_\-\s]*\d+(?:\.\d+)*', '', nombre, flags=re.IGNORECASE)
    nombre = re.sub(r'[_\-\s]*\d+\.\d+', '', nombre)
    nombre = re.sub(r'[_\-\s]*\d+(?=\.|_|$)', '', nombre)
    
    # Remover caracteres especiales y normalizar
    nombre = re.sub(r'[_\-]', ' ', nombre)
    nombre = re.sub(r'\s+', ' ', nombre)
    nombre = nombre.strip()
    
    # Capitalizar palabras
    return ' '.join(word.capitalize() for word in nombre.split())

def guardar_registro(nuevo_registro):
    """Guarda un nuevo registro en el CSV y crea su blockchain"""
    csv_path = "registro_documentos.csv"
    df_existente = cargar_registros()
    
    # Convertir el nuevo registro a DataFrame
    df_nuevo = pd.DataFrame([nuevo_registro])
    
    # Concatenar con los registros existentes
    df_final = pd.concat([df_existente, df_nuevo], ignore_index=True)
    
    # Guardar en CSV
    df_final.to_csv(csv_path, index=False)
    
    # Crear blockchain para el documento
    crear_nueva_cadena(nuevo_registro['HASH'], nuevo_registro)
    
    return df_final

# ==========================================
# FUNCIONES DE BITÁCORA Y AUDITORÍA
# ==========================================

def registrar_bitacora(hash_doc, accion, comentario=""):
    """Registra una acción en la bitácora del sistema"""
    bitacora_path = "bitacora.csv"
    
    # Obtener información del usuario actual
    usuario = st.session_state.get('name', '')
    rol = st.session_state.get('rol', '')
    fecha_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Crear registro de bitácora
    nuevo_registro = {
        'hash': hash_doc,
        'fecha_hora': fecha_hora,
        'usuario': usuario,
        'rol': rol,
        'accion': accion,
        'comentario_opcional': comentario
    }
    
    # Cargar bitácora existente o crear nueva
    if os.path.exists(bitacora_path):
        try:
            df_bitacora = pd.read_csv(bitacora_path)
        except:
            df_bitacora = pd.DataFrame(columns=['hash', 'fecha_hora', 'usuario', 'rol', 'accion', 'comentario_opcional'])
    else:
        df_bitacora = pd.DataFrame(columns=['hash', 'fecha_hora', 'usuario', 'rol', 'accion', 'comentario_opcional'])
    
    # Agregar nuevo registro
    df_nuevo = pd.DataFrame([nuevo_registro])
    df_bitacora_final = pd.concat([df_bitacora, df_nuevo], ignore_index=True)
    
    # Guardar bitácora
    df_bitacora_final.to_csv(bitacora_path, index=False)
    return True

def cargar_bitacora(filtro_area=None, filtro_hash=None):
    """Carga la bitácora según permisos del usuario"""
    bitacora_path = "bitacora.csv"
    
    if not os.path.exists(bitacora_path):
        return pd.DataFrame(columns=['hash', 'fecha_hora', 'usuario', 'rol', 'accion', 'comentario_opcional'])
    
    try:
        df_bitacora = pd.read_csv(bitacora_path)
        
        # Aplicar filtros si se especifican
        if filtro_hash:
            df_bitacora = df_bitacora[df_bitacora['hash'] == filtro_hash]
        
        return df_bitacora.sort_values('fecha_hora', ascending=False)
    except:
        return pd.DataFrame(columns=['hash', 'fecha_hora', 'usuario', 'rol', 'accion', 'comentario_opcional'])

def aprobar_documento(hash_doc, comentario=""):
    """Aprueba un documento y actualiza su estatus"""
    df_registros = cargar_registros()
    
    if hash_doc in df_registros['HASH'].values:
        # Verificar si ya está aprobado o rechazado
        documento = df_registros[df_registros['HASH'] == hash_doc].iloc[0]
        
        if documento['ESTATUS'] in ['Vigente', 'Rechazado']:
            return False, f"El documento ya está {documento['ESTATUS'].lower()}"
        
        # Verificar si el usuario actual ya aprobó este documento en la blockchain
        df_blockchain = cargar_blockchain_documento(hash_doc)
        usuario_actual = st.session_state.get('name', '')
        
        aprobaciones_previas = df_blockchain[
            (df_blockchain['accion'] == 'Aprobado') & 
            (df_blockchain['usuario_accion'] == usuario_actual)
        ]
        
        if not aprobaciones_previas.empty:
            return False, "Ya has aprobado este documento anteriormente"
        
        # Actualizar estatus a Vigente
        df_registros.loc[df_registros['HASH'] == hash_doc, 'ESTATUS'] = 'Vigente'
        df_registros.loc[df_registros['HASH'] == hash_doc, 'APROBADOR'] = usuario_actual
        df_registros.loc[df_registros['HASH'] == hash_doc, 'FECHA_ACTUALIZACION'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Agregar comentario si existe
        if comentario:
            modificacion_actual = df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'].iloc[0]
            nueva_modificacion = f"{modificacion_actual} | Aprobado: {comentario}" if modificacion_actual else f"Aprobado: {comentario}"
            df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'] = nueva_modificacion
        
        # Guardar cambios
        df_registros.to_csv("registro_documentos.csv", index=False)
        
        # Agregar bloque a la blockchain
        datos_bloque = df_registros[df_registros['HASH'] == hash_doc].iloc[0].to_dict()
        datos_bloque['MODIFICACION'] = f"Aprobado por {usuario_actual}: {comentario}" if comentario else f"Aprobado por {usuario_actual}"
        agregar_bloque_a_cadena(hash_doc, "Aprobado", datos_bloque)
        
        # Registrar en bitácora tradicional
        registrar_bitacora(hash_doc, "Aprobado", comentario)
        return True, "Documento aprobado exitosamente"
    
    return False, "Documento no encontrado"

def rechazar_documento(hash_doc, comentario=""):
    """Rechaza un documento y actualiza su estatus"""
    df_registros = cargar_registros()
    
    if hash_doc in df_registros['HASH'].values:
        # Verificar si ya está aprobado o rechazado
        documento = df_registros[df_registros['HASH'] == hash_doc].iloc[0]
        
        if documento['ESTATUS'] in ['Vigente', 'Rechazado']:
            return False, f"El documento ya está {documento['ESTATUS'].lower()}"
        
        # Verificar blockchain para evitar rechazos duplicados del mismo usuario
        df_blockchain = cargar_blockchain_documento(hash_doc)
        usuario_actual = st.session_state.get('name', '')
        
        rechazos_previos = df_blockchain[
            (df_blockchain['accion'] == 'Rechazado') & 
            (df_blockchain['usuario_accion'] == usuario_actual)
        ]
        
        if not rechazos_previos.empty:
            return False, "Ya has rechazado este documento anteriormente"
        
        # Actualizar estatus a Rechazado
        df_registros.loc[df_registros['HASH'] == hash_doc, 'ESTATUS'] = 'Rechazado'
        df_registros.loc[df_registros['HASH'] == hash_doc, 'FECHA_ACTUALIZACION'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Agregar comentario si existe
        if comentario:
            modificacion_actual = df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'].iloc[0]
            nueva_modificacion = f"{modificacion_actual} | Rechazado: {comentario}" if modificacion_actual else f"Rechazado: {comentario}"
            df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'] = nueva_modificacion
        
        # Guardar cambios
        df_registros.to_csv("registro_documentos.csv", index=False)
        
        # Agregar bloque a la blockchain
        datos_bloque = df_registros[df_registros['HASH'] == hash_doc].iloc[0].to_dict()
        datos_bloque['MODIFICACION'] = f"Rechazado por {usuario_actual}: {comentario}" if comentario else f"Rechazado por {usuario_actual}"
        agregar_bloque_a_cadena(hash_doc, "Rechazado", datos_bloque)
        
        # Registrar en bitácora tradicional
        registrar_bitacora(hash_doc, "Rechazado", comentario)
        return True, "Documento rechazado"
    
    return False, "Documento no encontrado"

# ==========================================
# FUNCIONES DE AUTENTICACIÓN Y USUARIOS
# ==========================================

def crear_usuario_admin_inicial():
    """Crea el usuario admin inicial si no existe el archivo usuarios.yaml"""
    yaml_path = "usuarios.yaml"
    
    if not os.path.exists(yaml_path):
        # Crear hash para la contraseña admin123 - Usar streamlit-authenticator==0.2.2
        hashed_passwords = stauth.Hasher(['admin123']).generate()
        
        usuarios_data = {
            'credentials': {
                'usernames': {
                    'admin': {
                        'name': 'Administrador General',
                        'password': hashed_passwords[0],
                        'role': 'ADMIN',
                        'area': 'General'
                    }
                }
            },
            'cookie': {
                'name': 'gestión_documental',
                'key': 'sistema_gestion_key',
                'expiry_days': 30
            },
            'preauthorized': {
                'emails': []
            }
        }
        
        with open(yaml_path, 'w', encoding='utf-8') as file:
            yaml.dump(usuarios_data, file, default_flow_style=False, allow_unicode=True)

def cargar_usuarios():
    """Carga los usuarios desde el archivo YAML"""
    crear_usuario_admin_inicial()
    
    with open('usuarios.yaml', 'r', encoding='utf-8') as file:
        config = yaml.safe_load(file)
    return config

def guardar_usuarios(config):
    """Guarda los usuarios en el archivo YAML"""
    with open('usuarios.yaml', 'w', encoding='utf-8') as file:
        yaml.dump(config, file, default_flow_style=False, allow_unicode=True)

def crear_nuevo_usuario(username, name, password, role, area):
    """Crea un nuevo usuario en el sistema"""
    config = cargar_usuarios()
    
    # Verificar si el usuario ya existe
    if username in config['credentials']['usernames']:
        return False, "El usuario ya existe"
    
    # Crear hash de la contraseña - Usar streamlit-authenticator==0.2.2
    hashed_password = stauth.Hasher([password]).generate()[0]
    
    # Agregar nuevo usuario
    config['credentials']['usernames'][username] = {
        'name': name,
        'password': hashed_password,
        'role': role,
        'area': area
    }
    
    # Guardar configuración
    guardar_usuarios(config)
    return True, "Usuario creado exitosamente"

def revisar_documento(hash_doc, comentario=""):
    """Marca un documento como revisado"""
    df_registros = cargar_registros()
    
    if hash_doc in df_registros['HASH'].values:
        usuario_actual = st.session_state.get('name', '')
        
        # Actualizar revisor
        df_registros.loc[df_registros['HASH'] == hash_doc, 'REVISOR'] = usuario_actual
        df_registros.loc[df_registros['HASH'] == hash_doc, 'FECHA_ACTUALIZACION'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Agregar comentario si existe
        if comentario:
            modificacion_actual = df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'].iloc[0]
            nueva_modificacion = f"{modificacion_actual} | Revisado: {comentario}" if modificacion_actual else f"Revisado: {comentario}"
            df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'] = nueva_modificacion
        
        # Guardar cambios
        df_registros.to_csv("registro_documentos.csv", index=False)
        
        # Agregar bloque a la blockchain
        datos_bloque = df_registros[df_registros['HASH'] == hash_doc].iloc[0].to_dict()
        datos_bloque['MODIFICACION'] = f"Revisado por {usuario_actual}: {comentario}" if comentario else f"Revisado por {usuario_actual}"
        agregar_bloque_a_cadena(hash_doc, "Revisado", datos_bloque)
        
        return True, "Documento revisado exitosamente"
    
    return False, "Documento no encontrado"

def actualizar_documento(hash_doc, nuevos_datos, comentario="", archivo_nuevo=None):
    """Actualiza un documento existente (solo si está aprobado) con opción de nuevo archivo"""
    df_registros = cargar_registros()
    
    if hash_doc in df_registros['HASH'].values:
        documento = df_registros[df_registros['HASH'] == hash_doc].iloc[0]
        
        # Permitir actualizar documentos en cualquier estado (excepto rechazados)
        if documento['ESTATUS'] == 'Rechazado':
            return False, "No se pueden actualizar documentos rechazados"
        
        usuario_actual = st.session_state.get('name', '')
        
        # Verificar permisos de área
        rol_usuario = st.session_state.get('rol', '')
        area_usuario = st.session_state.get('area', '')
        
        if not verificar_permisos(rol_usuario, area_usuario, documento['AREA'], "actualizar"):
            return False, "No tienes permisos para actualizar este documento"
        
        # Si hay un archivo nuevo, calcular nuevo hash
        nuevo_hash = hash_doc  # Por defecto mantener el hash actual
        if archivo_nuevo is not None:
            # Leer el archivo y calcular nuevo hash
            archivo_bytes = archivo_nuevo.read()
            nuevo_hash = calcular_hash(archivo_bytes)
            
            # Verificar si el nuevo hash ya existe en otro documento
            if nuevo_hash != hash_doc and hash_ya_existe(nuevo_hash, df_registros):
                return False, f"Ya existe un documento con este archivo (Hash: {nuevo_hash[:16]}...)"
        
        # Actualizar datos básicos
        for campo, valor in nuevos_datos.items():
            if campo in df_registros.columns:
                df_registros.loc[df_registros['HASH'] == hash_doc, campo] = valor
        
        # Si hay nuevo hash, actualizar el hash en el registro
        if nuevo_hash != hash_doc:
            df_registros.loc[df_registros['HASH'] == hash_doc, 'HASH'] = nuevo_hash
        
        # Incrementar versión
        version_actual = documento['VERSION']
        try:
            # Extraer número de versión
            match = re.search(r'(\d+(?:\.\d+)*)', version_actual)
            if match:
                num_version = float(match.group(1))
                nueva_version = f"v{num_version + 0.1:.1f}"
            else:
                nueva_version = "v1.1"
        except:
            nueva_version = "v1.1"
        
        # Actualizar campos del documento
        df_registros.loc[df_registros['HASH'] == hash_doc, 'VERSION'] = nueva_version
        df_registros.loc[df_registros['HASH'] == hash_doc, 'ESTATUS'] = 'Publicado'  # Vuelve a estado pendiente
        df_registros.loc[df_registros['HASH'] == hash_doc, 'FECHA_ACTUALIZACION'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Agregar comentario de actualización
        modificacion_actual = df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'].iloc[0]
        info_archivo = " con nuevo archivo" if archivo_nuevo is not None else ""
        nueva_modificacion = f"{modificacion_actual} | Actualizado{info_archivo}: {comentario}" if modificacion_actual else f"Actualizado{info_archivo}: {comentario}"
        df_registros.loc[df_registros['HASH'] == hash_doc, 'MODIFICACION'] = nueva_modificacion
        
        # Guardar cambios en CSV principal
        df_registros.to_csv("registro_documentos.csv", index=False)
        
        # Agregar bloque a la blockchain del documento
        datos_bloque = df_registros[df_registros['HASH'] == nuevo_hash].iloc[0].to_dict()
        datos_bloque['MODIFICACION'] = f"Actualizado por {usuario_actual}{info_archivo}: {comentario}"
        if archivo_nuevo is not None:
            datos_bloque['HASH_ANTERIOR'] = hash_doc
            datos_bloque['HASH_NUEVO'] = nuevo_hash
        
        # Usar el hash original para la blockchain (mantener la cadena del documento)
        agregar_bloque_a_cadena(hash_doc, "Actualizado", datos_bloque)
        
        # Si hay nuevo hash, crear una nueva entrada en la blockchain con el nuevo hash también
        if nuevo_hash != hash_doc:
            # Agregar bloque inicial para el nuevo hash
            agregar_bloque_a_cadena(nuevo_hash, "Actualización con nuevo archivo", datos_bloque)
        
        # Registrar en bitácora tradicional
        registrar_bitacora(nuevo_hash, "Actualizado", comentario + info_archivo)
        
        return True, f"Documento actualizado exitosamente a versión {nueva_version}{info_archivo}"
    
    return False, "Documento no encontrado"

def verificar_permisos(rol_usuario, area_usuario, documento_area=None, accion="ver"):
    """Verifica los permisos de acceso según el rol del usuario y la acción"""
    if rol_usuario == 'ADMIN':
        return True
    elif rol_usuario == 'APROBADOR':
        return True
    elif rol_usuario == 'SUPERVISOR':
        if accion in ["ver", "revisar", "bitacora", "actualizar"]:
            return True  # Permitir actualizar para todos los supervisores
        return False
    elif rol_usuario == 'COLABORADOR':
        if accion in ["ver", "actualizar"]:
            return True  # Permitir actualizar para todos los colaboradores
        elif accion == "subir":
            return True  # Puede subir a su área
        else:
            return False
    return False

def puede_editar_auditoria(rol_usuario):
    """Verifica si el usuario puede editar campos de auditoría y no conformidad"""
    return rol_usuario in ['ADMIN', 'APROBADOR']

def mostrar_historial_documento(hash_doc):
    """Muestra el historial blockchain completo de un documento específico"""
    df_blockchain = cargar_blockchain_documento(hash_doc)
    
    if df_blockchain.empty:
        st.info("No hay historial blockchain disponible para este documento.")
        return
    
    # Validar integridad de la cadena
    integridad_ok, mensaje_integridad = validar_integridad_cadena(hash_doc)
    
    if integridad_ok:
        st.success(f" **Blockchain Íntegra** - {len(df_blockchain)} bloques")
    else:
        st.error(f" **Blockchain Comprometida**: {mensaje_integridad}")
    
    st.markdown("** Historial Blockchain del Documento:**")
    
    # Mostrar cada bloque
    for idx, bloque in df_blockchain.iterrows():
        # Definir color según la acción
        accion = bloque['accion']
        if accion == "Aprobado":
            color = "green"
            icono = "✅"
        elif accion == "Rechazado":
            color = "red"
            icono = "❌"
        elif accion == "Revisado":
            color = "blue"
            icono = "👁️"
        elif accion == "Actualizado":
            color = "orange"
            icono = "🔄"
        elif accion == "Documento Creado":
            color = "violet"
            icono = "�"
        else:
            color = "gray"
            icono = "📝"
        
        with st.expander(f"Bloque #{bloque['numero_bloque']} - :{color}[{icono} {accion}]", expanded=(idx == 0)):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("** Información del Bloque:**")
                st.write(f"**Hash del Bloque:** {bloque['hash_bloque'][:32]}...")
                st.write(f"**Hash Anterior:** {bloque['hash_bloque_anterior'][:32] if bloque['hash_bloque_anterior'] != '0' else 'GÉNESIS'}...")
                st.write(f"**Timestamp:** {bloque['timestamp']}")
                st.write(f"**Usuario:** {bloque.get('usuario_accion', 'Sistema')}")
                
            with col2:
                st.markdown("** Información del Documento:**")
                st.write(f"**Nombre:** {bloque['nombre_documento']}")
                st.write(f"**Versión:** {bloque['version']}")
                st.write(f"**Estado:** {bloque['estatus']}")
                st.write(f"**Área:** {bloque['area']}")
                
                if bloque['revisor']:
                    st.write(f"**Revisor:** {bloque['revisor']}")
                if bloque['aprobador']:
                    st.write(f"**Aprobador:** {bloque['aprobador']}")
            
            if bloque['modificacion']:
                st.markdown("** Modificación/Comentario:**")
                st.info(bloque['modificacion'])
            
            if bloque['no_conformidad']:
                st.markdown("** No Conformidad:**")
                st.warning(bloque['no_conformidad'])
                
            if bloque['auditoria']:
                st.markdown("** Auditoría:**")
                st.info(bloque['auditoria'])
    
    # Información técnica de la blockchain
    st.markdown("---")
    st.markdown("**🔧 Información Técnica:**")
    col_tech1, col_tech2, col_tech3 = st.columns(3)
    
    with col_tech1:
        st.metric("Total de Bloques", len(df_blockchain))
    
    with col_tech2:
        st.metric("Algoritmo Hash", "SHA-256")
    
    with col_tech3:
        st.metric("Estado de Integridad", " Íntegra" if integridad_ok else " Comprometida")

def puede_aprobar_documentos(rol_usuario):
    """Verifica si el usuario puede aprobar o rechazar documentos"""
    return rol_usuario in ['ADMIN', 'APROBADOR', 'SUPERVISOR']

def mostrar_gestion_usuarios():
    """Muestra la interfaz de gestión de usuarios (solo para ADMIN)"""
    st.header("Gestión de Usuarios")
    
    # Cargar usuarios existentes
    config = cargar_usuarios()
    usuarios = config['credentials']['usernames']
    
    st.subheader("Usuarios Existentes")
    
    # Mostrar usuarios en tabla
    usuarios_df = []
    for username, datos in usuarios.items():
        usuarios_df.append({
            'Usuario': username,
            'Nombre': datos['name'],
            'Rol': datos['role'],
            'Área': datos['area']
        })
    
    if usuarios_df:
        st.dataframe(pd.DataFrame(usuarios_df), use_container_width=True)
    
    st.markdown("---")
    st.subheader("Crear Nuevo Usuario")
    
    with st.form("crear_usuario"):
        col1, col2 = st.columns(2)
        
        with col1:
            nuevo_username = st.text_input("Nombre de Usuario")
            nuevo_name = st.text_input("Nombre Completo")
            nueva_password = st.text_input("Contraseña", type="password")
        
        with col2:
            nuevo_role = st.selectbox("Rol", ["COLABORADOR", "SUPERVISOR", "APROBADOR"])
            nueva_area = st.text_input("Área")
        
        submit_usuario = st.form_submit_button("Crear Usuario")
        
        if submit_usuario:
            if nuevo_username and nuevo_name and nueva_password and nueva_area:
                exito, mensaje = crear_nuevo_usuario(nuevo_username, nuevo_name, nueva_password, nuevo_role, nueva_area)
                if exito:
                    st.success(mensaje)
                    st.rerun()
                else:
                    st.error(mensaje)
            else:
                st.error("Por favor completa todos los campos")

# ==========================================
# INTERFAZ STREAMLIT
# ==========================================

def main():
    # Inicializar sistema de usuarios
    crear_usuario_admin_inicial()
    
    # Cargar configuración de usuarios
    config = cargar_usuarios()
    
    # Crear el autenticador
    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days'],
        config['preauthorized']
    )
    
    # Mostrar formulario de login
    name, authentication_status, username = authenticator.login('Iniciar Sesión', 'main')
    
    if authentication_status == False:
        st.error('Usuario/contraseña incorrectos')
        return
    elif authentication_status == None:
        st.warning('Por favor ingresa tu usuario y contraseña')
        return
    elif authentication_status:
        # Usuario autenticado exitosamente
        
        # Obtener información del usuario
        user_data = config['credentials']['usernames'][username]
        
        # Guardar en session state
        st.session_state['name'] = name
        st.session_state['username'] = username
        st.session_state['rol'] = user_data['role']
        st.session_state['area'] = user_data['area']
        
        # Sidebar con información del usuario
        authenticator.logout('Cerrar Sesión', 'sidebar')
        st.sidebar.title(f"Bienvenido {name}")
        st.sidebar.write(f"**Rol:** {user_data['role']}")
        st.sidebar.write(f"**Área:** {user_data['area']}")
        st.sidebar.markdown("---")
        
        # Menú principal según rol
        if user_data['role'] == 'ADMIN':
            menu_option = st.sidebar.selectbox(
                "Menú Principal",
                ["Gestión de Documentos", "Gestión de Usuarios", "Registros del Sistema", "Dashboard Blockchain", "Bitácora de Auditoría", "Verificación de Integridad"]
            )
        elif user_data['role'] == 'APROBADOR':
            menu_option = st.sidebar.selectbox(
                "Menú Principal",
                ["Gestión de Documentos", "Registros del Sistema", "Dashboard Blockchain", "Aprobaciones Pendientes", "Bitácora de Auditoría", "Verificación de Integridad"]
            )
        elif user_data['role'] == 'SUPERVISOR':
            menu_option = st.sidebar.selectbox(
                "Menú Principal",
                ["Gestión de Documentos", "Registros de mi Área", "Dashboard Blockchain", "Bitácora de mi Área", "Verificación de Integridad"]
            )
        else:  # COLABORADOR
            menu_option = st.sidebar.selectbox(
                "Menú Principal",
                ["Subir Documentos", "Mis Documentos"]
            )
        
        # Mostrar contenido según la opción seleccionada
        if menu_option == "Gestión de Usuarios" and user_data['role'] == 'ADMIN':
            mostrar_gestion_usuarios()
        elif menu_option in ["Gestión de Documentos", "Subir Documentos"]:
            mostrar_gestion_documentos()
        elif menu_option in ["Registros del Sistema", "Registros de mi Área", "Mis Documentos"]:
            mostrar_registros(user_data['role'], user_data['area'])
        elif menu_option == "Dashboard Blockchain":
            mostrar_dashboard_blockchain()
        elif menu_option == "Aprobaciones Pendientes":
            mostrar_aprobaciones_pendientes()
        elif menu_option in ["Bitácora de Auditoría", "Bitácora de mi Área"]:
            mostrar_bitacora(user_data['role'], user_data['area'])
        elif menu_option == "Verificación de Integridad":
            mostrar_verificacion_integridad()

# ==========================================
# FUNCIONES DE VERIFICACIÓN DE INTEGRIDAD
# ==========================================

def escanear_archivos_carpeta(ruta_carpeta, limite_archivos=100, limite_tamaño_mb=50):
    """Escanea recursivamente una carpeta y calcula el hash SHA-256 de todos los archivos (optimizado)"""
    archivos_encontrados = []
    extensiones_validas = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.jpg', '.png', '.ppt', '.pptx']
    limite_tamaño_bytes = limite_tamaño_mb * 1024 * 1024
    
    try:
        ruta_path = Path(ruta_carpeta)
        
        if not ruta_path.exists():
            return [], f"La ruta {ruta_carpeta} no existe"
        
        if not ruta_path.is_dir():
            return [], f"La ruta {ruta_carpeta} no es una carpeta válida"
        
        # Contar archivos primero para mostrar progreso
        archivos_a_procesar = []
        archivos_omitidos = 0
        
        for archivo_path in ruta_path.rglob('*'):
            if archivo_path.is_file() and archivo_path.suffix.lower() in extensiones_validas:
                try:
                    tamaño = archivo_path.stat().st_size
                    if tamaño <= limite_tamaño_bytes:
                        archivos_a_procesar.append(archivo_path)
                        # Aplicar límite de archivos para evitar cuelgues
                        if len(archivos_a_procesar) >= limite_archivos:
                            break
                    else:
                        archivos_omitidos += 1
                except Exception:
                    continue
        
        total_archivos = len(archivos_a_procesar)
        
        if total_archivos == 0:
            return [], "No se encontraron archivos válidos en la carpeta"
        
        # Mostrar información sobre archivos omitidos
        if archivos_omitidos > 0:
            st.info(f"ℹ Se omitieron {archivos_omitidos} archivos por ser muy grandes (>{limite_tamaño_mb}MB)")
        
        if len(archivos_a_procesar) >= limite_archivos:
            st.warning(f" Se procesarán solo los primeros {limite_archivos} archivos. Ajusta el límite en configuración si necesitas más.")
        
        # Crear barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Procesar archivos con progreso
        for i, archivo_path in enumerate(archivos_a_procesar):
            try:
                # Actualizar progreso
                progreso = (i + 1) / total_archivos
                progress_bar.progress(progreso)
                status_text.text(f"Procesando: {archivo_path.name} ({i+1}/{total_archivos})")
                
                # Leer archivo en chunks para archivos grandes
                hash_obj = hashlib.sha256()
                with open(archivo_path, 'rb') as f:
                    while chunk := f.read(8192):  # Leer en chunks de 8KB
                        hash_obj.update(chunk)
                
                hash_calculado = hash_obj.hexdigest()
                
                archivo_info = {
                    'ruta_completa': str(archivo_path),
                    'nombre_archivo': archivo_path.name,
                    'nombre_sin_extension': archivo_path.stem,
                    'extension': archivo_path.suffix,
                    'tamaño': archivo_path.stat().st_size,
                    'hash_calculado': hash_calculado,
                    'carpeta_padre': str(archivo_path.parent)
                }
                
                archivos_encontrados.append(archivo_info)
                
            except Exception as e:
                st.warning(f" Error al procesar {archivo_path.name}: {str(e)}")
                continue
        
        # Limpiar barra de progreso
        progress_bar.empty()
        status_text.empty()
        
        return archivos_encontrados, None
        
    except Exception as e:
        return [], f"Error al escanear la carpeta: {str(e)}"

def buscar_documento_por_nombre(nombre_archivo, df_registros):
    """Busca un documento en el registro por nombre (búsqueda flexible)"""
    nombre_limpio = limpiar_nombre_archivo(nombre_archivo)
    
    # Buscar coincidencias exactas primero
    coincidencias_exactas = df_registros[df_registros['NOMBRE'].str.lower() == nombre_limpio.lower()]
    if not coincidencias_exactas.empty:
        return coincidencias_exactas.iloc[0]
    
    # Buscar coincidencias parciales
    coincidencias_parciales = df_registros[df_registros['NOMBRE'].str.lower().str.contains(nombre_limpio.lower(), na=False)]
    if not coincidencias_parciales.empty:
        return coincidencias_parciales.iloc[0]
    
    # Buscar por palabras clave del nombre
    palabras_nombre = nombre_limpio.lower().split()
    for _, documento in df_registros.iterrows():
        nombre_doc = documento['NOMBRE'].lower()
        coincidencias = sum(1 for palabra in palabras_nombre if palabra in nombre_doc)
        if coincidencias >= len(palabras_nombre) * 0.6:  # 60% de coincidencia
            return documento
    
    return None

def obtener_ultimo_hash_blockchain(hash_documento):
    """Obtiene el último hash de la blockchain de un documento"""
    blockchain_path = f"blockchain_{hash_documento[:16]}.csv"
    
    if not os.path.exists(blockchain_path):
        return None
    
    try:
        df_blockchain = pd.read_csv(blockchain_path)
        if df_blockchain.empty:
            return None
        
        # Obtener el último bloque
        ultimo_bloque = df_blockchain.sort_values('numero_bloque').iloc[-1]
        return ultimo_bloque['hash_documento']
    except Exception as e:
        st.warning(f"Error al leer blockchain {blockchain_path}: {str(e)}")
        return None

def comparar_integridad_archivos(archivos_fisicos, df_registros):
    """Compara los archivos físicos con los registros en la blockchain"""
    resultados = []
    
    for archivo in archivos_fisicos:
        nombre_archivo = archivo['nombre_archivo']
        hash_fisico = archivo['hash_calculado']
        
        # Buscar documento en registro
        documento_registrado = buscar_documento_por_nombre(nombre_archivo, df_registros)
        
        if documento_registrado is not None:
            hash_registrado = documento_registrado['HASH']
            hash_blockchain = obtener_ultimo_hash_blockchain(hash_registrado)
            
            # Determinar estado de integridad
            if hash_fisico == hash_registrado:
                estado = " ÍNTEGRO"
                estado_codigo = "integro"
            elif hash_blockchain and hash_fisico == hash_blockchain:
                estado = " ÍNTEGRO (Blockchain)"
                estado_codigo = "integro"
            else:
                estado = " MODIFICADO"
                estado_codigo = "modificado"
            
            resultado = {
                'nombre_archivo': nombre_archivo,
                'ruta_completa': archivo['ruta_completa'],
                'hash_fisico': hash_fisico,
                'hash_registrado': hash_registrado,
                'hash_blockchain': hash_blockchain or hash_registrado,
                'documento_registrado': documento_registrado['NOMBRE'],
                'version_registrada': documento_registrado['VERSION'],
                'estado_registrado': documento_registrado['ESTATUS'],
                'tamaño': archivo['tamaño'],
                'estado_integridad': estado,
                'estado_codigo': estado_codigo,
                'encontrado_en_registro': True
            }
        else:
            resultado = {
                'nombre_archivo': nombre_archivo,
                'ruta_completa': archivo['ruta_completa'],
                'hash_fisico': hash_fisico,
                'hash_registrado': 'N/A',
                'hash_blockchain': 'N/A',
                'documento_registrado': 'No encontrado',
                'version_registrada': 'N/A',
                'estado_registrado': 'N/A',
                'tamaño': archivo['tamaño'],
                'estado_integridad': "🔍 NO REGISTRADO",
                'estado_codigo': "no_registrado",
                'encontrado_en_registro': False
            }
        
        resultados.append(resultado)
    
    return resultados

def mostrar_verificacion_integridad():
    """Muestra la interfaz de verificación de integridad de documentos"""
    st.title(" Verificación de Integridad de Documentos")
    st.markdown("---")
    
    st.markdown("""
    ###  Funcionalidad:
    - **Escaneo recursivo** de carpetas y subcarpetas
    - **Cálculo automático** de hash SHA-256 para cada archivo
    - **Comparación** con registros en blockchain documental
    - **Detección** de archivos modificados o no registrados
    - **Visualización** gráfica de resultados
    """)
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN: SELECCIÓN DE CARPETA
    # ==========================================
    
    st.header(" Seleccionar Carpeta para Verificar")
    
    st.markdown("""
     **Instrucciones:**
    1. Usa el explorador de carpetas abajo para navegar
    2. Selecciona la carpeta que quieres verificar
    3. Todos los archivos de la carpeta se verificarán automáticamente
    """)
    
    # Inicializar la carpeta actual en session_state
    if 'carpeta_actual' not in st.session_state:
        st.session_state.carpeta_actual = ""
    
    if 'carpeta_seleccionada' not in st.session_state:
        st.session_state.carpeta_seleccionada = ""
    
    # Mostrar carpeta actual solo si hay una seleccionada
    if st.session_state.carpeta_actual:
        st.markdown(f"** Carpeta actual:** `{st.session_state.carpeta_actual}`")
    
    # Navegación de carpetas
    col1, col2, col3 = st.columns([1, 3, 1])
    
    with col1:
        # Botón para ir al directorio padre
        if st.button("⬆ **Subir**", help="Ir al directorio padre"):
            if st.session_state.carpeta_actual:
                parent = os.path.dirname(st.session_state.carpeta_actual)
                if parent != st.session_state.carpeta_actual:  # Evitar bucle en raíz
                    st.session_state.carpeta_actual = parent
                    st.rerun()
    
    with col2:
        # Campo para escribir ruta directamente
        nueva_ruta = st.text_input(
            "Escribe la ruta de la carpeta:",
            value="",
            placeholder="Ejemplo: C:\\Users\\Usuario\\Documentos",
            key="ruta_directa"
        )
        if nueva_ruta and nueva_ruta != st.session_state.carpeta_actual and os.path.exists(nueva_ruta) and os.path.isdir(nueva_ruta):
            st.session_state.carpeta_actual = nueva_ruta
            st.rerun()
    
    with col3:
        # Botón para ir a carpetas comunes
        if st.button(" **Inicio**", help="Ir al directorio home") and st.session_state.carpeta_actual:
            st.session_state.carpeta_actual = os.path.expanduser("~")
            st.rerun()
    
    # Mostrar contenido de la carpeta actual solo si hay una carpeta seleccionada
    if st.session_state.carpeta_actual:
        try:
            carpeta_path = Path(st.session_state.carpeta_actual)
            items = list(carpeta_path.iterdir())
            
            # Separar carpetas de archivos
            carpetas = [item for item in items if item.is_dir() and not item.name.startswith('.')]
            archivos = [item for item in items if item.is_file()]
            
            # Mostrar carpetas
            if carpetas:
                st.markdown("** Carpetas disponibles:**")
                
                # Mostrar en columnas
                num_cols = 3
                cols = st.columns(num_cols)
                
                for i, carpeta in enumerate(sorted(carpetas)):
                    with cols[i % num_cols]:
                        col_carpeta1, col_carpeta2 = st.columns([3, 1])
                        
                        with col_carpeta1:
                            # Botón para navegar a la carpeta
                            if st.button(f" {carpeta.name}", key=f"nav_{i}", use_container_width=True):
                                st.session_state.carpeta_actual = str(carpeta)
                                st.rerun()
                        
                        with col_carpeta2:
                            # Botón para seleccionar esta carpeta
                            if st.button("", key=f"sel_{i}", help=f"Seleccionar carpeta {carpeta.name}"):
                                st.session_state.carpeta_seleccionada = str(carpeta)
                                st.success(f" Carpeta seleccionada: {carpeta.name}")
                                st.rerun()
            
            # Mostrar información de archivos en la carpeta actual
            if archivos:
                with st.expander(f" Archivos en esta carpeta ({len(archivos)} archivos)", expanded=False):
                    archivos_validos = [f for f in archivos if f.suffix.lower() in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.jpg', '.png', '.ppt', '.pptx']]
                    if archivos_validos:
                        st.write(f"**{len(archivos_validos)} archivos válidos para verificación:**")
                        for archivo in sorted(archivos_validos)[:10]:  # Mostrar solo los primeros 10
                            tamaño = archivo.stat().st_size / (1024*1024)
                            st.write(f"• {archivo.name} ({tamaño:.2f} MB)")
                        if len(archivos_validos) > 10:
                            st.write(f"... y {len(archivos_validos) - 10} archivos más")
                    else:
                        st.write("No hay archivos válidos para verificación en esta carpeta")
        
        except PermissionError:
            st.error(" No tienes permisos para acceder a esta carpeta")
        except Exception as e:
            st.error(f" Error al acceder a la carpeta: {str(e)}")
    else:
        st.info(" Escribe una ruta en el campo de arriba para comenzar a explorar carpetas")
    
    # Mostrar carpeta seleccionada
    if st.session_state.carpeta_seleccionada:
        st.markdown("---")
        st.success(f" **Carpeta seleccionada para verificación:** `{st.session_state.carpeta_seleccionada}`")
        
        # Botón para cambiar selección
        if st.button(" **Cambiar selección**", type="secondary"):
            st.session_state.carpeta_seleccionada = ""
            st.rerun()
    else:
        # Botón para seleccionar la carpeta actual
        if st.session_state.carpeta_actual and st.button("✅ **Seleccionar carpeta actual**", type="secondary", use_container_width=True):
            st.session_state.carpeta_seleccionada = st.session_state.carpeta_actual
            st.rerun()
    
    # Configuración avanzada
    with st.expander(" Configuración"):
        limite_archivos = st.number_input("Máx. archivos", min_value=10, max_value=1000, value=100, help="Límite de archivos a procesar")
        limite_tamaño = st.number_input("Máx. tamaño por archivo (MB)", min_value=1, max_value=500, value=50, help="Tamaño máximo por archivo")
    
    # Botón para iniciar verificación
    if st.button(" **Iniciar Verificación de Integridad**", type="primary", use_container_width=True, disabled=not st.session_state.carpeta_seleccionada):
        if not st.session_state.carpeta_seleccionada:
            st.error(" Por favor selecciona una carpeta usando el explorador de arriba")
            return
        elif not os.path.exists(st.session_state.carpeta_seleccionada):
            st.error(" La carpeta seleccionada no existe")
            return
        
        # Mostrar progreso
        with st.spinner("🔄 Escaneando archivos y calculando hashes..."):
            # Escanear archivos con límites configurables
            archivos_fisicos, error = escanear_archivos_carpeta(st.session_state.carpeta_seleccionada, limite_archivos, limite_tamaño)
            
            if error:
                st.error(f" Error: {error}")
                return
            
            if not archivos_fisicos:
                st.warning(" No se encontraron archivos válidos en la carpeta especificada")
                return
        
        # Cargar registros
        df_registros = cargar_registros()
        
        if df_registros.empty:
            st.warning(" No hay documentos registrados en el sistema")
            return
        
        # Comparar integridad
        resultados = comparar_integridad_archivos(archivos_fisicos, df_registros)
        
        # ==========================================
        # MOSTRAR RESULTADOS
        # ==========================================
        
        st.success(f" Verificación completada. Se analizaron {len(archivos_fisicos)} archivos.")
        st.markdown("---")
        
        # Estadísticas generales
        st.subheader(" Resumen de Integridad")
        
        # Contar estados
        integros = len([r for r in resultados if r['estado_codigo'] == 'integro'])
        modificados = len([r for r in resultados if r['estado_codigo'] == 'modificado'])
        no_registrados = len([r for r in resultados if r['estado_codigo'] == 'no_registrado'])
        total = len(resultados)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(" Total Archivos", total)
        
        with col2:
            st.metric(" Íntegros", integros, delta=f"{(integros/total*100):.1f}%")
        
        with col3:
            st.metric(" Modificados", modificados, delta=f"{(modificados/total*100):.1f}%")
        
        with col4:
            st.metric(" No Registrados", no_registrados, delta=f"{(no_registrados/total*100):.1f}%")
        
        # Gráficos
        st.markdown("---")
        st.subheader(" Visualización de Resultados")
        
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            # Gráfico de pastel
            datos_grafico = {
                'Estado': ['Íntegros', 'Modificados', 'No Registrados'],
                'Cantidad': [integros, modificados, no_registrados]
            }
            
            if PLOTLY_AVAILABLE:
                fig_pie = px.pie(
                    values=datos_grafico['Cantidad'], 
                    names=datos_grafico['Estado'],
                    title="Distribución de Estados de Integridad",
                    color_discrete_sequence=['#28a745', '#dc3545', '#ffc107']
                )
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig_pie, use_container_width=True)
            else:
                # Gráfico nativo de Streamlit
                df_grafico = pd.DataFrame(datos_grafico)
                st.bar_chart(df_grafico.set_index('Estado')['Cantidad'])
        
        with col_grafico2:
            # Gráfico de barras por tipo de archivo
            tipos_archivo = {}
            for resultado in resultados:
                extension = Path(resultado['nombre_archivo']).suffix.lower()
                if extension not in tipos_archivo:
                    tipos_archivo[extension] = {'integros': 0, 'modificados': 0, 'no_registrados': 0}
                
                if resultado['estado_codigo'] == 'integro':
                    tipos_archivo[extension]['integros'] += 1
                elif resultado['estado_codigo'] == 'modificado':
                    tipos_archivo[extension]['modificados'] += 1
                else:
                    tipos_archivo[extension]['no_registrados'] += 1
            
            # Crear DataFrame para el gráfico
            df_tipos = pd.DataFrame.from_dict(tipos_archivo, orient='index')
            
            if not df_tipos.empty:
                st.markdown("**Estados por Tipo de Archivo:**")
                st.bar_chart(df_tipos)
        
        # Tabla detallada
        st.markdown("---")
        st.subheader("📋 Detalle de Archivos Analizados")
        
        # Filtros para la tabla
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            filtro_estado = st.selectbox(
                "Filtrar por Estado:",
                ["Todos", " Íntegros", " Modificados", " No Registrados"]
            )
        
        with col_filtro2:
            extensiones_disponibles = list(set([Path(r['nombre_archivo']).suffix.lower() for r in resultados]))
            filtro_extension = st.selectbox(
                "Filtrar por Tipo:",
                ["Todos"] + extensiones_disponibles
            )
        
        with col_filtro3:
            solo_problemas = st.checkbox("Solo mostrar problemas", value=False)
        
        # Aplicar filtros
        resultados_filtrados = resultados.copy()
        
        if filtro_estado != "Todos":
            if filtro_estado == " Íntegros":
                resultados_filtrados = [r for r in resultados_filtrados if r['estado_codigo'] == 'integro']
            elif filtro_estado == " Modificados":
                resultados_filtrados = [r for r in resultados_filtrados if r['estado_codigo'] == 'modificado']
            elif filtro_estado == " No Registrados":
                resultados_filtrados = [r for r in resultados_filtrados if r['estado_codigo'] == 'no_registrado']
        
        if filtro_extension != "Todos":
            resultados_filtrados = [r for r in resultados_filtrados if Path(r['nombre_archivo']).suffix.lower() == filtro_extension]
        
        if solo_problemas:
            resultados_filtrados = [r for r in resultados_filtrados if r['estado_codigo'] != 'integro']
        
        # Crear DataFrame para mostrar
        if resultados_filtrados:
            df_resultados = pd.DataFrame(resultados_filtrados)
            
            # Seleccionar columnas para mostrar
            columnas_mostrar = [
                'nombre_archivo', 'estado_integridad', 'documento_registrado', 
                'version_registrada', 'estado_registrado', 'tamaño'
            ]
            
            df_mostrar = df_resultados[columnas_mostrar].copy()
            df_mostrar.columns = ['Archivo', 'Estado Integridad', 'Documento Registrado', 'Versión', 'Estado', 'Tamaño (KB)']
            
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
        else:
            st.info("No hay resultados que mostrar con los filtros aplicados")
        
        # Acciones adicionales
        st.markdown("---")
        st.subheader(" Acciones Adicionales")
        
        col_accion1, col_accion2, col_accion3 = st.columns(3)
        
        with col_accion1:
            if st.button(" **Exportar Resultados**", type="secondary"):
                # Crear CSV con resultados
                df_export = pd.DataFrame(resultados)
                csv = df_export.to_csv(index=False)
                
                st.download_button(
                    label="⬇️ Descargar CSV",
                    data=csv,
                    file_name=f"verificacion_integridad_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
        
        with col_accion2:
            if st.button(" **Nueva Verificación**", type="secondary"):
                st.rerun()
        
        with col_accion3:
            if st.button(" **Ir a Registros**", type="secondary"):
                st.info(" Cambia a la sección 'Registros del Sistema' desde el menú lateral")

def mostrar_dashboard_blockchain():
    """Dashboard completo del estado de blockchain del sistema"""
    st.title("🔗 Dashboard Blockchain - Sistema de Trazabilidad")
    st.markdown("---")
    
    # Verificar si hay documentos
    if not os.path.exists(CSV_FILE):
        st.warning("No hay documentos registrados en el sistema.")
        return
    
    df = pd.read_csv(CSV_FILE)
    
    # Asegúrate que exista la columna 'Hash_SHA256' para compatibilidad con el dashboard
    if 'HASH' in df.columns:
        df['Hash_SHA256'] = df['HASH']
    
    if df.empty:
        st.warning("No hay documentos registrados en el sistema.")
        return
    
    # Estadísticas generales de blockchain
    col1, col2, col3, col4 = st.columns(4)
    
    total_docs = len(df)
    total_blockchains = sum(1 for _, row in df.iterrows() 
                           if os.path.exists(f"blockchain_{row['Hash_SHA256'][:16]}.csv"))
    
    with col1:
        st.metric(" Total Documentos", total_docs)
    
    with col2:
        st.metric(" Blockchains Activas", total_blockchains)
    
    with col3:
        total_blocks = 0
        for _, row in df.iterrows():
            blockchain_file = f"blockchain_{row['Hash_SHA256'][:16]}.csv"
            if os.path.exists(blockchain_file):
                blockchain_df = pd.read_csv(blockchain_file)
                total_blocks += len(blockchain_df)
        st.metric(" Total Bloques", total_blocks)
    
    with col4:
        # Verificar integridad del sistema
        docs_con_problemas = 0
        for _, row in df.iterrows():
            if not validar_integridad_cadena(row['Hash_SHA256']):
                docs_con_problemas += 1
        
        if docs_con_problemas == 0:
            st.metric(" Estado del Sistema", "ÍNTEGRO", delta="Sin problemas")
        else:
            st.metric(" Estado del Sistema", f"{docs_con_problemas} Problemas", delta="Requiere atención")
    
    st.markdown("---")
    
    # Análisis por estado de documento
    st.subheader(" Análisis por Estado de Documentos")
    
    estado_counts = df['ESTATUS'].value_counts()
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if PLOTLY_AVAILABLE:
            fig = px.pie(values=estado_counts.values, names=estado_counts.index, 
                        title="Distribución de Estados de Documentos")
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
        else:
            # Usar gráfico nativo de Streamlit si plotly no está disponible
            st.info(" Para gráficos avanzados, instala plotly: pip install plotly")
            st.bar_chart(estado_counts)
    
    with col2:
        st.dataframe(estado_counts.reset_index().rename(columns={'index': 'ESTATUS', 'ESTATUS': 'Cantidad'}))
    
    st.markdown("---")
    
    # Lista de documentos con estado de blockchain
    st.subheader(" Estado de Blockchain por Documento")
    
    # Crear tabla de estado
    blockchain_status = []
    for _, row in df.iterrows():
        blockchain_file = f"blockchain_{row['Hash_SHA256'][:16]}.csv"
        
        if os.path.exists(blockchain_file):
            blockchain_df = pd.read_csv(blockchain_file)
            num_bloques = len(blockchain_df)
            ultimo_bloque = blockchain_df.iloc[-1] if not blockchain_df.empty else None
            
            # Verificar integridad
            es_integro = validar_integridad_cadena(row['Hash_SHA256'])
            
            status = {
                'Documento': row['NOMBRE'][:30] + ('...' if len(row['NOMBRE']) > 30 else ''),
                'Tipo': row['TIPO'],
                'ESTATUS': row['ESTATUS'],
                'Hash (Inicio)': row['Hash_SHA256'][:16] + '...',
                'Bloques': num_bloques,
                'Última Acción': ultimo_bloque['accion'] if ultimo_bloque is not None else 'Genesis',
                'Última Fecha': ultimo_bloque['timestamp'] if ultimo_bloque is not None else row['FECHA_CREACION'],
                'Integridad': '✅ ÍNTEGRO' if es_integro else '❌ COMPROMETIDO'
            }
        else:
            status = {
                'Documento': row['NOMBRE'][:30] + ('...' if len(row['NOMBRE']) > 30 else ''),
                'Tipo': row['TIPO'],
                'ESTATUS': row['ESTATUS'],
                'Hash (Inicio)': row['Hash_SHA256'][:16] + '...',
                'Bloques': 0,
                'Última Acción': 'Sin blockchain',
                'Última Fecha': row['FECHA_CREACION'],
                'Integridad': '⚠️ SIN BLOCKCHAIN'
            }
        
        blockchain_status.append(status)
    
    # Mostrar tabla
    status_df = pd.DataFrame(blockchain_status)
    st.dataframe(status_df, use_container_width=True, hide_index=True)
    
    st.markdown("---")
    
    # Herramientas de análisis avanzado
    st.subheader("🔍 Herramientas de Análisis Avanzado")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Verificación de Integridad Global")
        if st.button("🔍 Verificar Integridad de Todo el Sistema", type="primary"):
            with st.spinner("Verificando integridad de todas las blockchains..."):
                problemas_encontrados = []
                
                for _, row in df.iterrows():
                    documento = row['NOMBRE']
                    hash_doc = row['Hash_SHA256']
                    
                    if not validar_integridad_cadena(hash_doc):
                        problemas_encontrados.append({
                            'Documento': documento,
                            'Hash': hash_doc,
                            'Problema': 'Integridad comprometida'
                        })
                
                if problemas_encontrados:
                    st.error(f"⚠️ Se encontraron {len(problemas_encontrados)} problemas de integridad:")
                    st.dataframe(pd.DataFrame(problemas_encontrados), hide_index=True)
                else:
                    st.success("✅ Todas las blockchains están íntegras")
    
    with col2:
        st.markdown("### Estadísticas de Actividad")
        
        # Actividad por mes
        activity_data = []
        for _, row in df.iterrows():
            blockchain_file = f"blockchain_{row['Hash_SHA256'][:16]}.csv"
            if os.path.exists(blockchain_file):
                blockchain_df = pd.read_csv(blockchain_file)
                for _, block_row in blockchain_df.iterrows():
                    activity_data.append({
                        'Fecha': block_row['timestamp'],
                        'Accion': block_row['accion'],
                        'Usuario': block_row.get('usuario_accion', 'Sistema')
                    })
        
        if activity_data:
            activity_df = pd.DataFrame(activity_data)
            activity_df['Fecha'] = pd.to_datetime(activity_df['Fecha'])
            activity_df['Mes'] = activity_df['Fecha'].dt.to_period('M')
            
            monthly_activity = activity_df.groupby('Mes').size().reset_index(name='Actividad')
            monthly_activity['Mes'] = monthly_activity['Mes'].astype(str)
            
            st.line_chart(monthly_activity.set_index('Mes')['Actividad'])
        else:
            st.info("No hay suficiente actividad para mostrar estadísticas")
    
    st.markdown("---")
    
    # Información técnica del sistema
    with st.expander("🔧 Información Técnica del Sistema"):
        st.markdown("""
        ### Especificaciones Técnicas
        
        **Algoritmo de Hash**: SHA-256  
        **Estructura de Blockchain**: Individual por documento  
        **Validación de Integridad**: Verificación automática de hash de bloques  
        **Persistencia**: Archivos CSV individuales por blockchain  
        **Seguridad**: Hash de bloque anterior + datos + timestamp  
        
        ### Estructura de Bloque
        
- Índice: Número secuencial del bloque
        - Timestamp: Fecha y hora de creación
        - Datos: Acción realizada en el documento
        - Hash Anterior: Hash del bloque previo
        - Hash: SHA-256 del bloque actual
        - Usuario: Usuario que realizó la acción

        
        ### Estados de Documento Soportados
        - **Borrador**: Documento en creación
        - **En Revisión**: Documento enviado para revisión
        - **Aprobado**: Documento aprobado por supervisor
        - **Rechazado**: Documento rechazado con observaciones
        - **Archivado**: Documento finalizado y archivado
        """)

def mostrar_gestion_documentos():
    """Muestra la interfaz de gestión de documentos"""
    # Título principal
    st.title("Sistema de Gestión Documental")
    st.markdown("---")
    
    # Descripción
    st.markdown("""
    ### Funcionalidades:
    - **Upload de archivos** con cálculo automático de hash SHA-256
    - **Detección automática** de tipo y versión del documento
    - **Verificación de duplicados** basada en hash
    - **Registro completo** con todos los metadatos
    - **Visualización** de todos los documentos registrados
    """)
    
    st.markdown("---")
    
    # ==========================================
    # SECCIÓN: UPLOAD DE ARCHIVO
    # ==========================================
    
    st.header("Seleccionar Archivo")
    
    uploaded_file = st.file_uploader(
        "Arrastra o selecciona un archivo:",
        type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'png'],
        help="Formatos soportados: PDF, Word, Excel, TXT, Imágenes"
    )
    
    # Manejar cancelación de archivo
    if st.session_state.get('archivo_cancelado'):
        st.info(" **Archivo cancelado.** Puedes seleccionar un archivo diferente arriba.")
        if st.button(" Seleccionar Nuevo Archivo", type="secondary"):
            del st.session_state['archivo_cancelado']
            st.rerun()
        return
    
    # Manejar modo actualización
    if st.session_state.get('modo_actualizacion') and st.session_state.get('hash_a_actualizar'):
        hash_documento = st.session_state['hash_a_actualizar']
        st.success(" **MODO ACTUALIZACIÓN ACTIVADO**")
        st.info("Serás redirigido a la sección de actualización de documentos...")
        
        # Limpiar session state y redirigir
        if st.button(" Ir a Actualizar Documento", type="primary"):
            del st.session_state['modo_actualizacion']
            del st.session_state['hash_a_actualizar']
            # Aquí podrías redirigir a otra página o mostrar el formulario de actualización
            st.info(f" **Hash del documento a actualizar:** `{hash_documento}`")
            st.info(" **Instrucciones:** Ve a la sección 'Registros de Documentos' y busca el documento por su hash para actualizarlo.")
        return
    
    if uploaded_file is not None:
        # Mostrar información básica del archivo
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Nombre", uploaded_file.name)
        
        with col2:
            st.metric("Tamaño", f"{uploaded_file.size:,} bytes")
        
        with col3:
            st.metric("Tipo", uploaded_file.type)
        
        st.markdown("---")
        
        # ==========================================
        # CALCULAR HASH
        # ==========================================
        
        st.header("Hash SHA-256")
        
        # Leer el archivo y calcular hash
        archivo_bytes = uploaded_file.read()
        hash_calculado = calcular_hash(archivo_bytes)
        
        st.code(hash_calculado, language="text")
        
        # Verificar si ya existe
        df_registros = cargar_registros()
        ya_existe = hash_ya_existe(hash_calculado, df_registros)
        
        if ya_existe:
            registro_existente = df_registros[df_registros['HASH'] == hash_calculado].iloc[0]
            
            st.error(" **ARCHIVO DUPLICADO DETECTADO**")
            
            # Mostrar información del documento existente
            with st.container():
                st.markdown("###  Documento Existente en el Sistema:")
                col1, col2 = st.columns(2)
                
                with col1:
                    st.info(f"** Nombre:** {registro_existente['NOMBRE']}")
                    st.info(f"** Tipo:** {registro_existente['TIPO']}")
                    st.info(f"** Versión:** {registro_existente['VERSION']}")
                    st.info(f"** Creado:** {registro_existente['FECHA_CREACION']}")
                
                with col2:
                    st.info(f"** Estado:** {registro_existente['ESTATUS']}")
                    st.info(f"** Creador:** {registro_existente['CREADOR']}")
                    st.info(f"** Área:** {registro_existente['AREA']}")
                    st.info(f"** Actualizado:** {registro_existente['FECHA_ACTUALIZACION']}")
            
            # Opciones para el usuario
            st.markdown("###  **¿Qué deseas hacer?**")
            
            col_opcion1, col_opcion2 = st.columns(2)
            
            with col_opcion1:
                if st.button(" **ACTUALIZAR DOCUMENTO EXISTENTE**", type="primary", use_container_width=True):
                    st.session_state['modo_actualizacion'] = True
                    st.session_state['hash_a_actualizar'] = hash_calculado
                    st.rerun()
            
            with col_opcion2:
                if st.button(" **CANCELAR Y ELEGIR OTRO ARCHIVO**", type="secondary", use_container_width=True):
                    st.session_state['archivo_cancelado'] = True
                    st.rerun()
            
            # Información adicional
            st.warning(" **No puedes subir el mismo archivo dos veces.** Elige actualizar el documento existente o selecciona un archivo diferente.")
            
            # Detener el procesamiento aquí para documentos duplicados
            return
        else:
            st.success(" **Archivo nuevo** - Listo para registrar")
        
        st.markdown("---")
        
        # ==========================================
        # DETECCIÓN AUTOMÁTICA
        # ==========================================
        
        st.header("Información Detectada")
        
        # Detectar información automáticamente
        tipo_detectado = detectar_tipo_archivo(uploaded_file.name)
        version_detectada = detectar_version(uploaded_file.name)
        nombre_limpio = limpiar_nombre_archivo(uploaded_file.name)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Tipo Detectado", tipo_detectado)
        
        with col2:
            st.metric("Versión Detectada", version_detectada)
        
        with col3:
            st.metric("Nombre Limpio", nombre_limpio)
        
        st.markdown("---")
        
        # ==========================================
        # FORMULARIO DE REGISTRO
        # ==========================================
        
        st.header("Registrar Documento")
        
        with st.form("formulario_registro"):
            col1, col2 = st.columns(2)
            
            with col1:
                nombre_doc = st.text_input("Nombre del Documento", value=nombre_limpio)
                tipo_doc = st.selectbox("Tipo de Documento", [
                    tipo_detectado, "Manual", "Contrato", "Política", "Procedimiento", 
                    "Reporte", "Formato", "Especificación", "Plan", "Acta", "Presupuesto", "Documento"
                ])
                version_doc = st.text_input("Versión", value=version_detectada)
                estatus_doc = st.selectbox("Estatus", ["Publicado", "Editado", "Borrador", "Vigente", "Terminado", "Rechazado"])
                modificacion_doc = st.text_area("Descripción de Modificación")
                
                # El creador se toma automáticamente del usuario logueado
                creador_doc = st.text_input("Creador", value=st.session_state.get('name', ''), disabled=True)
                area_doc = st.text_input("Área", value=st.session_state.get('area', ''), disabled=True)
            
            with col2:
                # Obtener rol y nombre del usuario para controlar permisos
                rol_usuario = st.session_state.get('rol', '')
                nombre_usuario = st.session_state.get('name', '')
                
                # Controlar campos según el rol del usuario con restricciones estrictas
                if rol_usuario == 'COLABORADOR':
                    # COLABORADOR: No puede ver ni editar Revisor, Aprobador, No Conformidad, Auditoría
                    revisor_doc = st.text_input("Revisor", disabled=True, help="Campo restringido para colaboradores")
                    aprobador_doc = st.text_input("Aprobador", value="", disabled=True, help="Se asignará automáticamente")
                    no_conformidad_doc = st.text_area("No Conformidad", disabled=True, help="Campo restringido para colaboradores")
                    auditoria_doc = st.text_area("Auditoría", disabled=True, help="Campo restringido para colaboradores")
                
                elif rol_usuario == 'SUPERVISOR':
                    # SUPERVISOR: Puede llenar Revisor, pero no los demás campos de auditoría
                    revisor_doc = st.text_input("Revisor")
                    aprobador_doc = st.text_input("Aprobador", value="", disabled=True, help="Solo los aprobadores pueden llenar este campo")
                    no_conformidad_doc = st.text_area("No Conformidad", disabled=True, help="Solo aprobadores pueden editar")
                    auditoria_doc = st.text_area("Auditoría", disabled=True, help="Solo aprobadores pueden editar")
                
                elif rol_usuario == 'APROBADOR':
                    # APROBADOR: Puede editar todos los campos, se autocompleta como aprobador
                    revisor_doc = st.text_input("Revisor")
                    aprobador_doc = st.text_input("Aprobador", value=nombre_usuario, help="Asignado automáticamente")
                    no_conformidad_doc = st.text_area("No Conformidad", help="Campo exclusivo para aprobadores")
                    auditoria_doc = st.text_area("Auditoría", help="Campo exclusivo para aprobadores")
                
                elif rol_usuario == 'ADMIN':
                    # ADMIN: Acceso completo a todos los campos
                    revisor_doc = st.text_input("Revisor")
                    aprobador_doc = st.text_input("Aprobador")
                    no_conformidad_doc = st.text_area("No Conformidad")
                    auditoria_doc = st.text_area("Auditoría")
                
                else:
                    # Fallback por seguridad - comportamiento más restrictivo
                    revisor_doc = st.text_input("Revisor", disabled=True, help="Usuario sin permisos")
                    aprobador_doc = st.text_input("Aprobador", disabled=True, help="Usuario sin permisos")
                    no_conformidad_doc = st.text_area("No Conformidad", disabled=True, help="Usuario sin permisos")
                    auditoria_doc = st.text_area("Auditoría", disabled=True, help="Usuario sin permisos")
                
                # Fechas automáticas
                fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.text_input("Fecha Creación", value=fecha_actual, disabled=True)
                st.text_input("Fecha Actualización", value=fecha_actual, disabled=True)
            
            # Botón de submit
            submitted = st.form_submit_button("Registrar Documento", type="primary")
            
            if submitted:
                if nombre_doc and tipo_doc and creador_doc:
                    # Validaciones de seguridad según rol
                    if rol_usuario == 'COLABORADOR':
                        # Los colaboradores no pueden llenar campos restringidos
                        revisor_doc = ""
                        aprobador_doc = ""
                        no_conformidad_doc = ""
                        auditoria_doc = ""
                    elif rol_usuario == 'SUPERVISOR':
                        # Los supervisores no pueden llenar campos de auditoría
                        aprobador_doc = ""
                        no_conformidad_doc = ""
                        auditoria_doc = ""
                    elif rol_usuario == 'APROBADOR':
                        # Los aprobadores se asignan automáticamente
                        aprobador_doc = nombre_usuario
                    
                    # Determinar estatus según si ya existe
                    estatus_final = "Editado" if ya_existe else "Publicado"
                    
                    # Crear el registro
                    nuevo_registro = {
                        'HASH': hash_calculado,
                        'NOMBRE': nombre_doc,
                        'TIPO': tipo_doc,
                        'FECHA_CREACION': fecha_actual,
                        'FECHA_ACTUALIZACION': fecha_actual,
                        'VERSION': version_doc,
                        'ESTATUS': estatus_final,
                        'MODIFICACION': modificacion_doc,
                        'CREADOR': creador_doc,
                        'AREA': area_doc,
                        'REVISOR': revisor_doc,
                        'APROBADOR': aprobador_doc,
                        'NO_CONFORMIDAD': no_conformidad_doc,
                        'AUDITORIA': auditoria_doc
                    }
                    
                    # Guardar el registro
                    df_actualizado = guardar_registro(nuevo_registro)
                    
                    # Registrar en bitácora la subida del documento
                    registrar_bitacora(hash_calculado, "Documento Subido", f"Subido como {estatus_final}")
                    
                    st.success(f"✅ **Documento registrado exitosamente** como '{estatus_final}'")
                    st.balloons()
                    
                    # Mostrar información del documento registrado
                    with st.container():
                        st.markdown("###  Documento Registrado:")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.info(f"** Nombre:** {nombre_doc}")
                            st.info(f"** Tipo:** {tipo_doc}")
                            st.info(f"** Versión:** {version_doc}")
                        with col2:
                            st.info(f"** Estado:** {estatus_final}")
                            st.info(f"** Creador:** {creador_doc}")
                            st.info(f"** Área:** {area_doc}")
                    
                    # Opción para subir otro documento
                    if st.button(" **Subir Otro Documento**", type="secondary"):
                        # Limpiar variables específicas del archivo actual pero mantener la sesión
                        for key in ['modo_actualizacion', 'hash_a_actualizar', 'archivo_cancelado']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
                    
                    # No recargar automáticamente - mantener el formulario visible
                    
                else:
                    st.error("Por favor completa los campos obligatorios: Nombre, Tipo y Creador")

def mostrar_registros(rol_usuario, area_usuario):
    """Muestra los registros según los permisos del usuario"""
    st.title("Registros de Documentos")
    st.markdown("---")
    
    df_registros = cargar_registros()
    
    if df_registros.empty:
        st.info("No hay documentos registrados aún.")
        return
    
    # Filtrar según rol y área
    if rol_usuario == 'COLABORADOR':
        # Colaboradores solo ven sus propios documentos
        df_filtrado = df_registros[df_registros['AREA'] == area_usuario]
        st.subheader(f"Mis Documentos - Área: {area_usuario}")
    elif rol_usuario == 'SUPERVISOR':
        # Supervisores ven todos los documentos de su área
        df_filtrado = df_registros[df_registros['AREA'] == area_usuario]
        st.subheader(f"Documentos del Área: {area_usuario}")
    else:  # ADMIN o APROBADOR
        # Admin y Aprobador ven todos los documentos
        df_filtrado = df_registros
        st.subheader("Todos los Documentos del Sistema")
    
    if df_filtrado.empty:
        st.info("No hay documentos para mostrar según tus permisos.")
        return
    
    st.write(f"**Total de documentos:** {len(df_filtrado)}")
    
    # Filtros adicionales
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_tipo = st.selectbox("Filtrar por Tipo", ["Todos"] + df_filtrado['TIPO'].unique().tolist())
    
    with col2:
        filtro_estatus = st.selectbox("Filtrar por Estatus", ["Todos"] + df_filtrado['ESTATUS'].unique().tolist())
    
    with col3:
        if rol_usuario in ['ADMIN', 'APROBADOR']:
            if "AREA" in df_filtrado.columns:
                filtro_area = st.selectbox("Filtrar por Área", ["Todos"] + df_filtrado['AREA'].unique().tolist())
            else:
                filtro_area = "Todos"
        else:
            filtro_area = "Todos"
    
    # Aplicar filtros adicionales
    df_final = df_filtrado.copy()
    
    if filtro_tipo != "Todos":
        df_final = df_final[df_final['TIPO'] == filtro_tipo]
    
    if filtro_estatus != "Todos":
        df_final = df_final[df_final['ESTATUS'] == filtro_estatus]
    
    if filtro_area != "Todos" and rol_usuario in ['ADMIN', 'APROBADOR']:
        if "AREA" in df_final.columns:
            df_final = df_final[df_final['AREA'] == filtro_area]
    
    # Mostrar tabla con acciones
    st.markdown("---")
    
    # Mostrar documentos con acciones de aprobar/rechazar
    for idx, row in df_final.iterrows():
        col_accion, col_info = st.columns([1, 10])
        
        # Estado del documento para determinar qué mostrar
        estatus = row['ESTATUS']
        aprobador = row['APROBADOR']
        usuario_actual = st.session_state.get('name', '')
        
        with col_accion:
            # Mostrar estado del documento o botón de acciones
            if estatus == 'Vigente':
                st.success("✅")
                st.caption("Aprobado")
            elif estatus == 'Rechazado':
                st.error("❌")
                st.caption("Rechazado")
            elif puede_aprobar_documentos(rol_usuario) and estatus not in ['Vigente', 'Rechazado']:
                # Solo mostrar botón de menú si puede aprobar y no está ya procesado
                if st.button("⋮", key=f"menu_{idx}", help="Acciones"):
                    # Toggle del estado de mostrar acciones
                    key_actions = f'show_actions_{row["HASH"]}'
                    st.session_state[key_actions] = not st.session_state.get(key_actions, False)
            else:
                st.write("—")
        
        with col_info:
            # Información del documento
            col_doc1, col_doc2, col_doc3, col_doc4 = st.columns([3, 2, 2, 2])
            
            with col_doc1:
                st.write(f"**{row['NOMBRE']}**")
                st.caption(f"Hash: {row['HASH'][:16]}...")
            
            with col_doc2:
                st.write(f"Tipo: {row['TIPO']}")
                st.write(f"Versión: {row['VERSION']}")
            
            with col_doc3:
                # Mostrar estado con colores y información adicional
                if estatus == 'Vigente':
                    st.markdown(f"Estado: :green[{estatus}]")
                    if aprobador:
                        st.caption(f"Aprobado por: {aprobador}")
                elif estatus == 'Rechazado':
                    st.markdown(f"Estado: :red[{estatus}]")
                    # Buscar quien rechazó en la bitácora
                    df_bitacora = cargar_bitacora(filtro_hash=row['HASH'])
                    rechazos = df_bitacora[df_bitacora['accion'] == 'Rechazado']
                    if not rechazos.empty:
                        st.caption(f"Rechazado por: {rechazos.iloc[-1]['usuario']}")
                elif estatus == 'Publicado':
                    st.markdown(f"Estado: :orange[{estatus}]")
                else:
                    st.markdown(f"Estado: :blue[{estatus}]")
                
                st.write(f"Área: {row['AREA']}")
            
            with col_doc4:
                st.write(f"Creador: {row['CREADOR']}")
                st.write(f"Fecha: {row['FECHA_CREACION'][:10]}")
                
                # Botón para actualizar documento (disponible para todos)
                if row['ESTATUS'] != 'Rechazado':
                    if st.button(" Actualizar", key=f"actualizar_directo_{row['HASH'][:8]}", help="Actualizar documento"):
                        key_update = f'show_update_{row["HASH"]}'
                        st.session_state[key_update] = True
                        st.rerun()
                
                # Botón para ver historial
                if st.button(" Historial", key=f"historial_{row['HASH'][:8]}", help="Ver historial de acciones"):
                    key_historial = f'show_historial_{row["HASH"]}'
                    st.session_state[key_historial] = not st.session_state.get(key_historial, False)
        
        # Mostrar historial si está activado
        key_historial = f'show_historial_{row["HASH"]}'
        if st.session_state.get(key_historial, False):
            with st.expander(" Historial de Acciones", expanded=True):
                mostrar_historial_documento(row['HASH'])
                if st.button("Cerrar Historial", key=f"cerrar_hist_{row['HASH'][:8]}"):
                    st.session_state[key_historial] = False
                    st.rerun()
        
        # Mostrar acciones si están activadas y el documento puede ser procesado
        key_actions = f'show_actions_{row["HASH"]}'
        if (st.session_state.get(key_actions, False) and 
            puede_aprobar_documentos(rol_usuario)):
            
            st.markdown("** Acciones Disponibles:**")
            
            # Primera fila de acciones - Revisar y Ver Blockchain
            col_actions_1 = st.columns([1, 2, 2, 2, 5])
            
            with col_actions_1[1]:
                if st.button(" Ver Blockchain", key=f"blockchain_{row['HASH']}", use_container_width=True):
                    key_blockchain = f'show_blockchain_{row["HASH"]}'
                    st.session_state[key_blockchain] = True
                    st.rerun()
            
            with col_actions_1[2]:
                if st.button(" Revisar", key=f"revisar_{row['HASH']}", use_container_width=True):
                    comentario_rev = st.session_state.get(f"comentario_{row['HASH']}", "")
                    exito, mensaje = revisar_documento(row['HASH'], comentario_rev)
                    if exito:
                        st.success(mensaje)
                        if key_actions in st.session_state:
                            del st.session_state[key_actions]
                        st.rerun()
                    else:
                        st.error(mensaje)
            
            with col_actions_1[3]:
                # Permitir actualizar cualquier documento (excepto rechazados)
                if (row['ESTATUS'] != 'Rechazado' and 
                    verificar_permisos(rol_usuario, st.session_state.get('area', ''), row['AREA'], "actualizar")):
                    if st.button(" Actualizar", key=f"actualizar_{row['HASH']}", use_container_width=True):
                        key_update = f'show_update_{row["HASH"]}'
                        st.session_state[key_update] = True
                        st.rerun()
            
            # Segunda fila - Comentario
            col_actions_2 = st.columns([1, 8, 3])
            with col_actions_2[1]:
                comentario_key = f"comentario_{row['HASH']}"
                comentario = st.text_input(" Comentario para la acción", key=comentario_key, placeholder="Razón de la decisión...")
            
            # Tercera fila - Aprobar/Rechazar (solo si no está procesado)
            if estatus not in ['Vigente', 'Rechazado']:
                col_actions_3 = st.columns([1, 2, 2, 2, 5])
                
                with col_actions_3[1]:
                    if st.button(" Aprobar", key=f"aprobar_{row['HASH']}", use_container_width=True):
                        exito, mensaje = aprobar_documento(row['HASH'], comentario)
                        if exito:
                            st.success(mensaje)
                            if key_actions in st.session_state:
                                del st.session_state[key_actions]
                            st.rerun()
                        else:
                            st.error(mensaje)
                
                with col_actions_3[2]:
                    if st.button(" Rechazar", key=f"rechazar_{row['HASH']}", use_container_width=True):
                        if not comentario.strip():
                            st.warning("Por favor proporciona un comentario para el rechazo.")
                        else:
                            exito, mensaje = rechazar_documento(row['HASH'], comentario)
                            if exito:
                                st.error(mensaje)
                                if key_actions in st.session_state:
                                    del st.session_state[key_actions]
                                st.rerun()
                            else:
                                st.error(mensaje)
                
                with col_actions_3[3]:
                    if st.button(" Cancelar", key=f"cancelar_{row['HASH']}"):
                        if key_actions in st.session_state:
                            del st.session_state[key_actions]
                        st.rerun()
        
        # Mostrar blockchain si está activado
        key_blockchain = f'show_blockchain_{row["HASH"]}'
        if st.session_state.get(key_blockchain, False):
            with st.container():
                st.markdown("---")
                st.markdown(f"##  Blockchain del Documento: {row['NOMBRE']}")
                mostrar_historial_documento(row['HASH'])
                if st.button(" Cerrar Blockchain", key=f"cerrar_blockchain_{row['HASH'][:8]}"):
                    st.session_state[key_blockchain] = False
                    st.rerun()
        
        # Mostrar formulario de actualización si está activado
        key_update = f'show_update_{row["HASH"]}'
        if st.session_state.get(key_update, False):
            with st.container():
                st.markdown("---")
                st.markdown(f"##  Actualizar Documento: {row['NOMBRE']}")
                
                # Información importante sobre la actualización
                st.info(" **Importante:** Al actualizar el documento puedes subir un nuevo archivo. Esto recalculará el hash y creará un nuevo bloque en la blockchain.")
                
                with st.form(f"form_actualizar_{row['HASH']}"):
                    # Sección de archivo
                    st.markdown("###  Archivo del Documento")
                    archivo_nuevo = st.file_uploader(
                        "Seleccionar nuevo archivo (opcional):",
                        type=['pdf', 'doc', 'docx', 'xls', 'xlsx', 'txt', 'jpg', 'png'],
                        help="Si no seleccionas un archivo, se mantendrá el documento actual",
                        key=f"file_uploader_{row['HASH']}"
                    )
                    
                    # Mostrar información del archivo actual
                    col_file_info = st.columns([1, 3])
                    with col_file_info[0]:
                        st.write("**Archivo actual:**")
                    with col_file_info[1]:
                        st.code(f"Hash: {row['HASH'][:32]}...", language="text")
                    
                    # Si hay un archivo nuevo, mostrar su información
                    if archivo_nuevo is not None:
                        st.markdown("** Información del nuevo archivo:**")
                        col_new_file = st.columns(3)
                        with col_new_file[0]:
                            st.metric("Nombre", archivo_nuevo.name)
                        with col_new_file[1]:
                            st.metric("Tamaño", f"{archivo_nuevo.size:,} bytes")
                        with col_new_file[2]:
                            st.metric("Tipo", archivo_nuevo.type)
                        
                        # Calcular hash del nuevo archivo para mostrar (sin afectar el proceso)
                        archivo_bytes_preview = archivo_nuevo.read()
                        nuevo_hash_preview = calcular_hash(archivo_bytes_preview)
                        st.code(f"Nuevo Hash: {nuevo_hash_preview[:32]}...", language="text")
                        # Resetear el puntero del archivo
                        archivo_nuevo.seek(0)
                        
                        if nuevo_hash_preview == row['HASH']:
                            st.warning(" El archivo seleccionado es idéntico al actual (mismo hash)")
                    
                    st.markdown("---")
                    st.markdown("###  Información del Documento")
                    
                    col_upd1, col_upd2 = st.columns(2)
                    
                    with col_upd1:
                        nuevo_nombre = st.text_input("Nombre del Documento", value=row['NOMBRE'])
                        
                        # Opciones de tipo con el tipo actual seleccionado
                        tipos_disponibles = ["Manual", "Contrato", "Política", "Procedimiento", "Reporte", "Formato", "Especificación", "Plan", "Acta", "Presupuesto", "Documento"]
                        try:
                            index_tipo_actual = tipos_disponibles.index(row['TIPO'])
                        except ValueError:
                            index_tipo_actual = 0
                        
                        nuevo_tipo = st.selectbox("Tipo", tipos_disponibles, index=index_tipo_actual)
                        nueva_modificacion = st.text_area("Descripción de Cambios", placeholder="Describe qué cambios estás realizando...")
                        
                        # Mostrar versión actual e información de incremento
                        st.info(f"**Versión actual:** {row['VERSION']}")
                        st.caption("La versión se incrementará automáticamente (ej: v1.0 → v1.1)")
                    
                    with col_upd2:
                        # Campos de auditoría solo para ADMIN y APROBADOR
                        if rol_usuario in ['ADMIN', 'APROBADOR']:
                            nueva_no_conformidad = st.text_area("No Conformidad", value=row['NO_CONFORMIDAD'], help="Campo exclusivo para ADMIN y APROBADOR")
                            nueva_auditoria = st.text_area("Auditoría", value=row['AUDITORIA'], help="Campo exclusivo para ADMIN y APROBADOR")
                        else:
                            nueva_no_conformidad = st.text_area("No Conformidad", value=row['NO_CONFORMIDAD'], disabled=True, help="Solo ADMIN y APROBADOR pueden editar este campo")
                            nueva_auditoria = st.text_area("Auditoría", value=row['AUDITORIA'], disabled=True, help="Solo ADMIN y APROBADOR pueden editar este campo")
                        
                        # Información adicional
                        st.markdown("** Información del proceso:**")
                        st.write("• El estado cambiará a 'Publicado'")
                        st.write("• Se creará un bloque en blockchain")
                        st.write("• Se registrará en bitácora")
                        if archivo_nuevo:
                            st.write("• Se recalculará el hash del documento")
                    
                    st.markdown("---")
                    
                    # Botones de acción
                    col_btn_upd = st.columns([1, 2, 2, 7])
                    
                    with col_btn_upd[1]:
                        submitted_update = st.form_submit_button(" Guardar Cambios", type="primary")
                    
                    with col_btn_upd[2]:
                        if st.form_submit_button(" Cancelar"):
                            st.session_state[key_update] = False
                            st.rerun()
                    
                    # Procesar la actualización
                    if submitted_update:
                        if not nueva_modificacion.strip():
                            st.error("Por favor describe los cambios que estás realizando.")
                        else:
                            # Preparar datos de actualización
                            nuevos_datos = {
                                'NOMBRE': nuevo_nombre,
                                'TIPO': nuevo_tipo,
                                'MODIFICACION': nueva_modificacion
                            }
                            
                            # Solo agregar campos de auditoría si el usuario tiene permisos
                            if rol_usuario in ['ADMIN', 'APROBADOR']:
                                nuevos_datos['NO_CONFORMIDAD'] = nueva_no_conformidad
                                nuevos_datos['AUDITORIA'] = nueva_auditoria
                            
                            # Ejecutar actualización
                            exito, mensaje = actualizar_documento(row['HASH'], nuevos_datos, nueva_modificacion, archivo_nuevo)
                            
                            if exito:
                                st.success(mensaje)
                                st.balloons()
                                st.session_state[key_update] = False
                                st.rerun()
                            else:
                                st.error(mensaje)
        
        st.markdown("---")
    
    # Botón para descargar CSV (solo para ADMIN, APROBADOR y SUPERVISOR)
    if rol_usuario in ['ADMIN', 'APROBADOR', 'SUPERVISOR']:
        csv = df_final.to_csv(index=False)
        st.download_button(
            label="Descargar CSV",
            data=csv,
            file_name=f"registros_documentos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    # Información del sistema con estadísticas blockchain
    st.markdown("---")
    st.markdown("###  Información del Sistema Blockchain")
    
    # Calcular estadísticas blockchain
    total_blockchains = 0
    total_bloques = 0
    blockchains_integras = 0
    
    for _, doc in df_final.iterrows():
        blockchain_path = f"blockchain_{doc['HASH'][:16]}.csv"
        if os.path.exists(blockchain_path):
            total_blockchains += 1
            df_blockchain = cargar_blockchain_documento(doc['HASH'])
            total_bloques += len(df_blockchain)
            
            # Verificar integridad
            integridad_ok, _ = validar_integridad_cadena(doc['HASH'])
            if integridad_ok:
                blockchains_integras += 1
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(" Total Documentos", len(df_final))
    
    with col2:
        st.metric(" Blockchains Activas", total_blockchains)
    
    with col3:
        st.metric(" Total de Bloques", total_bloques)
    
    with col4:
        porcentaje_integridad = (blockchains_integras / total_blockchains * 100) if total_blockchains > 0 else 0
        st.metric(" Integridad", f"{porcentaje_integridad:.1f}%")
    
    # Información técnica adicional
    col_tech1, col_tech2, col_tech3 = st.columns(3)
    
    with col_tech1:
        st.metric(" Algoritmo Hash", "SHA-256")
    
    with col_tech2:
        st.metric(" Almacenamiento", "CSV + Blockchain")
    
    with col_tech3:
        promedio_bloques = (total_bloques / total_blockchains) if total_blockchains > 0 else 0
        st.metric(" Promedio Bloques/Doc", f"{promedio_bloques:.1f}")

def mostrar_aprobaciones_pendientes():
    """Muestra documentos pendientes de aprobación (solo para APROBADOR)"""
    st.title("Aprobaciones Pendientes")
    st.markdown("---")
    
    df_registros = cargar_registros()
    
    if df_registros.empty:
        st.info("No hay documentos registrados.")
        return
    
    # Filtrar documentos pendientes (no aprobados ni rechazados)
    df_pendientes = df_registros[
        (~df_registros['ESTATUS'].isin(['Vigente', 'Rechazado'])) &
        (df_registros['ESTATUS'].isin(['Borrador', 'Publicado', 'Editado']))
    ]
    
    if df_pendientes.empty:
        st.success("No hay documentos pendientes de aprobación.")
        return
    
    st.write(f"**Documentos pendientes de aprobación:** {len(df_pendientes)}")
    
    for idx, row in df_pendientes.iterrows():
        with st.expander(f" {row['NOMBRE']} - {row['TIPO']} (v{row['VERSION']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Creador:** {row['CREADOR']}")
                st.write(f"**Área:** {row['AREA']}")
                st.write(f"**Fecha:** {row['FECHA_CREACION']}")
                st.write(f"**Estatus Actual:** {row['ESTATUS']}")
            
            with col2:
                st.write(f"**Hash:** {row['HASH'][:32]}...")
                st.write(f"**Modificación:** {row['MODIFICACION']}")
                if row['REVISOR']:
                    st.write(f"**Revisor:** {row['REVISOR']}")
            
            # Verificar si ya fue procesado por el usuario actual
            usuario_actual = st.session_state.get('name', '')
            ya_aprobado = row['APROBADOR'] == usuario_actual
            
            # Verificar si ya fue rechazado por el usuario actual
            df_bitacora = cargar_bitacora(filtro_hash=row['HASH'])
            ya_rechazado = not df_bitacora[
                (df_bitacora['usuario'] == usuario_actual) & 
                (df_bitacora['accion'] == 'Rechazado')
            ].empty
            
            if ya_aprobado:
                st.success(f" **Ya aprobaste este documento**")
            elif ya_rechazado:
                st.error(f" **Ya rechazaste este documento**")
            else:
                # Mostrar botones de acción
                st.markdown("**Acciones:**")
                col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 6])
                
                # Campo para comentario
                comentario_aprob = st.text_input(
                    "Comentario para la aprobación/rechazo", 
                    key=f"comentario_aprob_{row['HASH']}", 
                    placeholder="Razón de la decisión..."
                )
                
                with col_btn1:
                    if st.button(" Aprobar", key=f"aprobar_pend_{row['HASH']}", use_container_width=True):
                        exito, mensaje = aprobar_documento(row['HASH'], comentario_aprob)
                        if exito:
                            st.success(mensaje)
                            st.rerun()
                        else:
                            st.error(mensaje)
                
                with col_btn2:
                    if st.button(" Rechazar", key=f"rechazar_pend_{row['HASH']}", use_container_width=True):
                        if not comentario_aprob.strip():
                            st.warning("Por favor proporciona un comentario para el rechazo.")
                        else:
                            exito, mensaje = rechazar_documento(row['HASH'], comentario_aprob)
                            if exito:
                                st.error(mensaje)
                                st.rerun()
                            else:
                                st.error(mensaje)

def mostrar_bitacora(rol_usuario, area_usuario):
    """Muestra la bitácora de auditoría según los permisos del usuario"""
    st.title("Bitácora de Auditoría")
    st.markdown("---")
    
    # Verificar permisos
    if rol_usuario not in ['ADMIN', 'APROBADOR', 'SUPERVISOR']:
        st.error("No tienes permisos para acceder a la bitácora.")
        return
    
    df_bitacora = cargar_bitacora()
    
    if df_bitacora.empty:
        st.info("No hay registros en la bitácora aún.")
        return
    
    # Filtrar según rol
    if rol_usuario == 'SUPERVISOR':
        # Supervisores solo ven la bitácora de su área
        df_registros = cargar_registros()
        hashes_area = df_registros[df_registros['AREA'] == area_usuario]['HASH'].tolist()
        df_filtrado = df_bitacora[df_bitacora['hash'].isin(hashes_area)]
        st.subheader(f"Bitácora del Área: {area_usuario}")
    else:  # ADMIN o APROBADOR
        df_filtrado = df_bitacora
        st.subheader("Bitácora General del Sistema")
    
    if df_filtrado.empty:
        st.info("No hay registros de bitácora para mostrar según tus permisos.")
        return
    
    st.write(f"**Total de registros:** {len(df_filtrado)}")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        filtro_accion = st.selectbox("Filtrar por Acción", ["Todos"] + df_filtrado['accion'].unique().tolist())
    
    with col2:
        filtro_usuario = st.selectbox("Filtrar por Usuario", ["Todos"] + df_filtrado['usuario'].unique().tolist())
    
    with col3:
        filtro_rol = st.selectbox("Filtrar por Rol", ["Todos"] + df_filtrado['rol'].unique().tolist())
    
    # Aplicar filtros
    df_final = df_filtrado.copy()
    
    if filtro_accion != "Todos":
        df_final = df_final[df_final['accion'] == filtro_accion]
    
    if filtro_usuario != "Todos":
        df_final = df_final[df_final['usuario'] == filtro_usuario]
    
    if filtro_rol != "Todos":
        df_final = df_final[df_final['rol'] == filtro_rol]
    
    # Mostrar registros de bitácora
    st.markdown("---")
    
    for idx, row in df_final.iterrows():
        with st.expander(f"{row['fecha_hora']} - {row['accion']} por {row['usuario']} ({row['rol']})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"**Hash del Documento:** {row['hash'][:32]}...")
                st.write(f"**Fecha y Hora:** {row['fecha_hora']}")
                st.write(f"**Usuario:** {row['usuario']}")
            
            with col2:
                st.write(f"**Rol:** {row['rol']}")
                st.write(f"**Acción:** {row['accion']}")
                if row['comentario_opcional']:
                    st.write(f"**Comentario:** {row['comentario_opcional']}")
    
    # Botón para descargar bitácora
    csv_bitacora = df_final.to_csv(index=False)
    st.download_button(
        label="Descargar Bitácora CSV",
        data=csv_bitacora,
        file_name=f"bitacora_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

# ==========================================
# EJECUTAR LA APLICACIÓN
# ==========================================

if __name__ == "__main__":
    main() 