import os
import json
from datetime import datetime

# Directorios de entrada y salida
carpeta_raw = './raw'
carpeta_clean = './clean'

# Crear la carpeta de salida si no existe
if not os.path.exists(carpeta_clean):
    os.makedirs(carpeta_clean)

# Función para normalizar una noticia
def normalizar_noticia(noticia_original):
    # Obtener la fecha y convertirla al formato ISO8601 si es posible
    fecha = noticia_original.get("pubDate") or noticia_original.get("isoDate", "Fecha no disponible")
    try:
        if fecha != "Fecha no disponible":
            fecha = datetime.strptime(fecha, "%a, %d %b %Y %H:%M:%S %z").isoformat()
    except ValueError:
        fecha = "Fecha no disponible"

    # Normalizar los campos
    return {
        "titulo": noticia_original.get("title", "Título no disponible"),
        "contenido": noticia_original.get("content:encoded") or noticia_original.get("content", "Contenido no disponible"),
        "fuente": noticia_original.get("newsMedia", "Fuente no disponible"),
        "fecha": fecha,
        "pais": "País no disponible",  # Si no tienes esta información, la dejamos como predeterminada
        "tema": noticia_original.get("section") or ', '.join(noticia_original.get("categories", ["Tema no disponible"])),
        "url": noticia_original.get("link", "URL no disponible"),
        "autor": noticia_original.get("creator") or noticia_original.get("author") or "Autor no disponible"
    }

# Procesar todos los archivos JSON en la carpeta 'raw' y combinarlos en uno solo
def procesar_y_combinar_archivos():
    todas_las_noticias = []  # Lista para almacenar todas las noticias

    for archivo in os.listdir(carpeta_raw):
        if archivo.endswith('.json'):
            ruta_archivo = os.path.join(carpeta_raw, archivo)

            # Leer el archivo JSON
            with open(ruta_archivo, 'r', encoding='utf-8') as file:
                try:
                    noticias = json.load(file)
                except json.JSONDecodeError:
                    print(f"Error al procesar {archivo}. No es un JSON válido.")
                    continue

            # Normalizar todas las noticias del archivo y agregarlas a la lista general
            noticias_normalizadas = [normalizar_noticia(noticia) for noticia in noticias]
            todas_las_noticias.extend(noticias_normalizadas)

    # Guardar todas las noticias combinadas en un único archivo JSON en la carpeta 'clean'
    ruta_salida = os.path.join(carpeta_clean, 'noticias_combinadas.json')
    with open(ruta_salida, 'w', encoding='utf-8') as output_file:
        json.dump(todas_las_noticias, output_file, ensure_ascii=False, indent=2)
    
    print(f'Archivo combinado guardado en: {ruta_salida}')

# Ejecutar el proceso
procesar_y_combinar_archivos()
