import streamlit as st
import pandas as pd
import hashlib
import os
from pathlib import Path
from datetime import datetime

# Try to import plotly, set flag if not available
try:
    import plotly.express as px
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False

# ==========================================
# FUNCIONES DE VER
# ==========================================

def limpiar_nombre_archivo(nombre_archivo):
    """Función auxiliar para limpiar nombres de archivo"""
    return Path(nombre_archivo).stem

def cargar_registros():
    """Función auxiliar para cargar registros - implementar según tu sistema"""
    try:
        
        if os.path.exists("registros_documentos.csv"):
            return pd.read_csv("registros_documentos.csv")
        else:
            return pd.DataFrame()
    except Exception:
        return pd.DataFrame()

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
    st.title("🔍 Verificación de Integridad de Documentos")
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
    
    st.header(" Selección de Carpeta")
    
    # Inicializar la ruta en session_state si no existe
    if 'ruta_verificacion' not in st.session_state:
        st.session_state.ruta_verificacion = None
    
    # Mostrar carpeta seleccionada solo si existe una
    if st.session_state.ruta_verificacion:
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.success(f" **Carpeta seleccionada:** {st.session_state.ruta_verificacion}")
        
        with col2:
            if st.button(" **Cambiar**", type="secondary"):
                st.session_state.ruta_verificacion = None
                st.rerun()
    else:
        st.info("Selecciona una carpeta para comenzar la verificación")

    # Explorador de carpetas con botones
    st.markdown("###  Seleccionar Carpeta")
    
    # Rutas comunes predefinidas (sin mostrar las rutas)
    rutas_comunes = {
        " Documentos": os.path.expanduser("~/Documents"),
        " Escritorio": os.path.expanduser("~/Desktop"),
        " Descargas": os.path.expanduser("~/Downloads"),
        "Carpeta del proyecto": os.getcwd(),
    }
    
    # Agregar carpetas del sistema si existen
    carpetas_sistema = {
        " Unidad C": "C:\\",
        "Unidad D": "D:\\",
        "Archivos de programa": "C:\\Program Files",
        "Usuario actual": os.path.expanduser("~"),
    }
    
    # Filtrar solo las que existen
    for nombre, ruta in carpetas_sistema.items():
        if os.path.exists(ruta):
            rutas_comunes[nombre] = ruta
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("** Carpetas Comunes:**")
        for nombre, ruta in list(rutas_comunes.items())[:4]:
            if os.path.exists(ruta):
                if st.button(f"{nombre}", key=f"btn_{nombre}", use_container_width=True):
                    st.session_state.ruta_verificacion = ruta
                    st.rerun()
    
    with col2:
        st.markdown("** Más Ubicaciones:**")
        for nombre, ruta in list(rutas_comunes.items())[4:]:
            if os.path.exists(ruta):
                if st.button(f"{nombre}", key=f"btn_{nombre}", use_container_width=True):
                    st.session_state.ruta_verificacion = ruta
                    st.rerun()
    
    with col3:
        st.markdown("** Opciones Avanzadas:**")
        
        if st.button(" **Explorar Manualmente**", use_container_width=True):
            st.session_state.mostrar_explorador_manual = True
        
        # Solo mostrar el explorador manual si se solicita
        if st.session_state.get('mostrar_explorador_manual', False):
            st.markdown("**Ruta personalizada:**")
            ruta_personalizada = st.text_input(
                "Escribe la ruta:",
                placeholder="C:\\Mi\\Carpeta",
                key="ruta_personalizada"
            )
            
            col_btn1, col_btn2 = st.columns(2)
            
            with col_btn1:
                if st.button(" **Usar**", type="primary", disabled=not ruta_personalizada):
                    if ruta_personalizada and os.path.exists(ruta_personalizada):
                        st.session_state.ruta_verificacion = ruta_personalizada
                        st.session_state.mostrar_explorador_manual = False
                        st.rerun()
                    else:
                        st.error("❌ La ruta no existe")
            
            with col_btn2:
                if st.button("❌ **Cancelar**", type="secondary"):
                    st.session_state.mostrar_explorador_manual = False
                    st.rerun()
    
    st.markdown("---")
    
    # Botón para iniciar verificación con configuración avanzada
    col_btn1, col_btn2 = st.columns([3, 1])
    
    with col_btn1:
        iniciar_verificacion = st.button(
            "🔍 **Iniciar Verificación de Integridad**", 
            type="primary", 
            use_container_width=True,
            disabled=not st.session_state.ruta_verificacion
        )
    
    with col_btn2:
        with st.expander("⚙️ Config"):
            limite_archivos = st.number_input("Máx. archivos", min_value=10, max_value=1000, value=100, help="Límite de archivos a procesar")
            limite_tamaño = st.number_input("Máx. tamaño (MB)", min_value=1, max_value=500, value=50, help="Tamaño máximo por archivo")
    
    if iniciar_verificacion:
        if not st.session_state.ruta_verificacion or not os.path.exists(st.session_state.ruta_verificacion):
            st.error(" Selecciona una carpeta válida primero")
            return
        
        # Mostrar progreso
        with st.spinner("🔄 Escaneando archivos y calculando hashes..."):
            # Escanear archivos con límites configurables
            archivos_fisicos, error = escanear_archivos_carpeta(st.session_state.ruta_verificacion, limite_archivos, limite_tamaño)
            
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
        
        st.success(f"Verificación completada. Se analizaron {len(archivos_fisicos)} archivos.")
        st.markdown("---")
        
        # ==========================================
        # ESTADÍSTICAS GENERALES
        # ==========================================
        
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
        
        # ==========================================
        # GRÁFICOS
        # ==========================================
        
        st.markdown("---")
        st.subheader(" Visualización de Resultados")
        
        col_grafico1, col_grafico2 = st.columns(2)
        
        with col_grafico1:
            # Gráfico de pastel
            datos_grafico = {
                'Estado': ['Íntegros', 'Modificados', 'No Registrados'],
                'Cantidad': [integros, modificados, no_registrados],
                'Color': ['#28a745', '#dc3545', '#ffc107']
            }
            
            if PLOTLY_AVAILABLE:
                import plotly.express as px
                fig_pie = px.pie(
                    values=datos_grafico['Cantidad'], 
                    names=datos_grafico['Estado'],
                    title="Distribución de Estados de Integridad",
                    color_discrete_sequence=datos_grafico['Color']
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
        
        # ==========================================
        # TABLA DETALLADA
        # ==========================================
        
        st.markdown("---")
        st.subheader(" Detalle de Archivos Analizados")
        
        # Filtros para la tabla
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            filtro_estado = st.selectbox(
                "Filtrar por Estado:",
                ["Todos", "Íntegros", " Modificados", " No Registrados"]
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
            df_mostrar.columns = ['Archivo', 'Estado Integridad', 'Documento Registrado', 'Versión', 'Estado', 'Tamaño (bytes)']
            
            st.dataframe(df_mostrar, use_container_width=True, hide_index=True)
            
            # ==========================================
            # DETALLES EXPANDIBLES
            # ==========================================
            
            st.markdown("---")
            st.subheader("🔍 Detalles de Integridad")
            
            # Mostrar detalles de archivos problemáticos
            problemas = [r for r in resultados_filtrados if r['estado_codigo'] != 'integro']
            
            if problemas:
                st.warning(f" Se encontraron {len(problemas)} archivos con problemas:")
                
                for problema in problemas[:10]:  # Mostrar máximo 10
                    with st.expander(f"🔍 {problema['nombre_archivo']} - {problema['estado_integridad']}"):
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.write(f"** Ruta:** {problema['ruta_completa']}")
                            st.write(f"** Tamaño:** {problema['tamaño']:,} bytes")
                            st.write(f"** Hash Físico:** `{problema['hash_fisico'][:32]}...`")
                        
                        with col2:
                            if problema['encontrado_en_registro']:
                                st.write(f"** Documento:** {problema['documento_registrado']}")
                                st.write(f"** Hash Registrado:** `{problema['hash_registrado'][:32]}...`")
                                st.write(f"** Estado:** {problema['estado_registrado']}")
                            else:
                                st.info("Este archivo no está registrado en el sistema")
                
                if len(problemas) > 10:
                    st.info(f"... y {len(problemas) - 10} archivos más con problemas")
            else:
                st.success("🎉 ¡Todos los archivos están íntegros!")
        else:
            st.info("No hay resultados que mostrar con los filtros aplicados")
        
        # ==========================================
        # ACCIONES ADICIONALES
        # ==========================================
        
        st.markdown("---")
        st.subheader("🛠️ Acciones Adicionales")
        
        col_accion1, col_accion2, col_accion3 = st.columns(3)
        
        with col_accion1:
            if st.button(" **Exportar Resultados**", type="secondary"):
                # Crear CSV con resultados
                df_export = pd.DataFrame(resultados)
                csv = df_export.to_csv(index=False)
                
                st.download_button(
                    label="⬇ Descargar CSV",
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

# ==========================================
# INSTRUCCIONES DE INTEGRACIÓN
# ==========================================

"""
INSTRUCCIONES PARA INTEGRAR EN TU APP CLEIN:

1. Copia todas las funciones de este archivo y pégalas en tu clein.py después de las funciones existentes

2. Modifica la función main() en la sección donde defines los menús para agregar "Verificación de Integridad"

3. En la sección donde manejas las opciones del menú, agrega:
   elif menu_option == "Verificación de Integridad":
       mostrar_verificacion_integridad()

4. Asegúrate de que tienes importada la librería pathlib al inicio:
   from pathlib import Path

¡Y listo! La función estará integrada en tu aplicación Clein.
"""
