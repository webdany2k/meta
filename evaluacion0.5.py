import json
import requests
import os
import re
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import logging
import nltk
from nltk.tokenize import word_tokenize

# Descargar los recursos de NLTK necesarios para tokenizar
nltk.download('punkt')

# Cargar las variables de entorno
load_dotenv()
API_URL = os.getenv('API_URL')

# Ruta del archivo JSON con las noticias
noticias_file_path = './clean/noticias.json'

# Función para leer el archivo JSON
def leer_noticias():
    with open(noticias_file_path, 'r', encoding='utf-8') as file:
        return json.load(file)

# Función para limpiar el contenido HTML
def limpiar_html(contenido):
    return BeautifulSoup(contenido, "html.parser").get_text()

# Función para truncar el contenido de la noticia si es muy largo
def truncar_texto(texto, limite=1500):
    return texto[:limite] + '...' if len(texto) > limite else texto

# Función para crear el prompt simplificado
def crear_prompt(noticia):
    contenido_limpio = limpiar_html(noticia["contenido"])
    contenido_truncado = truncar_texto(contenido_limpio)

    prompt = (
        "System: Este es un análisis de noticias.\n"
        "User: Por favor, analiza la siguiente noticia y proporciona:\n"
        f"{contenido_truncado}\n"
        "Assistant: Proporciona:\n"
        "1. Preguntas que se plantean en el texto.\n"
        "2. Hechos o evidencias que sustentan el texto.\n"
        "3. Conclusiones escritas en la noticia.\n"
        "4. Suposiciones implícitas.\n"
        "5. Palabras clave importantes.\n"
        "6. Palabras clave deducidas.\n"
        "7. Sujetos importantes mencionados.\n"
        "8. Lugares físicos mencionados.\n"
        "9. Medios de información o sitios web mencionados.\n"
    )

    return prompt

# Función para enviar el contenido de la noticia al modelo Llama 3.2 y gestionar respuestas fragmentadas
def enviar_a_nlp(noticia):
    try:
        # Crear el prompt con instrucciones
        prompt = crear_prompt(noticia)
        
        # Payload para enviar a la API
        payload = {
            "model": "llama3.2",  
            "prompt": prompt,
            "max_tokens": 10000
        }

        # Headers para la solicitud
        headers = {
            'Content-Type': 'application/json',
        }

        # Depuración: Imprimir el payload antes de enviar
        print(f"Enviando payload: {payload}")
        
        # Solicitud POST a la API, con stream=True para manejar la respuesta por fragmentos
        response = requests.post(API_URL, headers=headers, json=payload, stream=True)

        # Acumular la respuesta completa de los fragmentos
        full_response = ""
        for line in response.iter_lines():
            if line:
                try:
                    # Decodificar cada fragmento como JSON
                    fragment = json.loads(line)
                    full_response += fragment.get("response", "")
                except json.JSONDecodeError:
                    print(f"Error al decodificar la línea: {line.decode('utf-8')}")

        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            print(f"Respuesta completa recibida:\n{full_response}")
            return full_response
        else:
            print(f"Error en la solicitud: {response.status_code}")
            print(f"Respuesta: {response.text}")
            return None

    except requests.RequestException as e:
        print(f"Error al enviar la noticia: {e}")
        return None

# Función para procesar la respuesta del modelo y asignar valores
def procesar_respuesta(nlp_response):
    evaluacion = {
        "preguntas": [],
        "hechos o evidencias": [],
        "conclusiones": [],
        "suposiciones implícitas": [],
        "palabras clave importantes": [],
        "palabras clave deducidas": [],
        "sujetos importantes": [],
        "lugares físicos": [],
        "medios de información o sitios web": [],
        "resumen": ""
    }
    
    # Tokenizar la respuesta
    tokens = word_tokenize(nlp_response)

    # Eliminar caracteres especiales y stopwords
    tokens_limpios = [token.lower() for token in tokens if token.isalpha() and len(token) > 2]

    # Lista de posibles encabezados
    encabezados = [
        "Preguntas que se plantean en el texto",
        "Hechos o evidencias que sustentan el texto",
        "Conclusiones escritas en la noticia",
        "Suposiciones implícitas",
        "Palabras clave importantes",
        "Palabras clave deducidas",
        "Sujetos importantes mencionados",
        "Lugares físicos mencionados",
        "Medios de información o sitios web mencionados",
        "Resumen",
        "Análisis de la Noticia"
    ]
    
    for encabezado in encabezados:
        key = encabezado.lower().replace(" mencionados", "").replace("que se plantean en el texto", "")
        if key in evaluacion:
            if isinstance(evaluacion[key], list):
                evaluacion[key] = extraer_lista_seccion(nlp_response, encabezado)
            else:
                evaluacion[key] = extraer_seccion(nlp_response, encabezado)
    
    # Si no se encontró un resumen, intenta extraer una conclusión general
    if not evaluacion["resumen"]:
        evaluacion["resumen"] = extraer_seccion(nlp_response, "Conclusión") or extraer_seccion(nlp_response, "Análisis de la Noticia")
    
    return evaluacion

def extraer_seccion(texto, encabezado):
    # Busca el encabezado con diferentes formatos posibles
    patrones = [
        rf"\*\*{re.escape(encabezado)}:?\*\*:?\s*(.*?)(?=\n\*\*|\Z)",
        rf"{re.escape(encabezado)}:?\s*(.*?)(?=\n\w+:|\Z)",
        rf"\d+\.\s*{re.escape(encabezado)}:?\s*(.*?)(?=\n\d+\.|\Z)"
    ]
    
    for patron in patrones:
        resultado = re.search(patron, texto, re.DOTALL | re.IGNORECASE)
        if resultado:
            return resultado.group(1).strip()
    
    return "No evaluado"


def extraer_lista_seccion(texto, encabezado):
    seccion = extraer_seccion(texto, encabezado)
    if seccion != "No evaluado":
        # Elimina asteriscos, guiones, números y letras al principio de cada línea
        items = re.findall(r'(?:^|\n)\s*(?:\*|-|\d+\.|[a-z]\)|\(?\d+\)?)\s*(.*?)(?=\n|$)', seccion)
        # Si no se encontraron items con el patrón anterior, divide por líneas
        if not items:
            items = [line.strip() for line in seccion.split('\n') if line.strip()]
        return [item for item in items if item]
    return []

# Función para procesar y etiquetar cada noticia
def procesar_noticias():
    noticias = leer_noticias()
    
    for noticia_actual in noticias:
        logger.info(f"Procesando noticia: {noticia_actual['titulo']}")
        
        try:
            nlp_response = enviar_a_nlp(noticia_actual)
            
            if nlp_response:
                evaluacion = procesar_respuesta(nlp_response)
                noticia_actual["evaluacion"] = evaluacion
                logger.info(f"Noticia procesada exitosamente: {noticia_actual['titulo']}")
                logger.debug(f"Evaluación: {json.dumps(evaluacion, ensure_ascii=False, indent=2)}")
            else:
                logger.warning(f"No se obtuvo respuesta para la noticia: {noticia_actual['titulo']}")
                noticia_actual["evaluacion"] = generar_evaluacion_vacia()
        except Exception as e:
            logger.error(f"Error al procesar la noticia {noticia_actual['titulo']}: {str(e)}", exc_info=True)
            noticia_actual["evaluacion"] = generar_evaluacion_vacia()
    
    try:
        with open('./clean/noticias_con_evaluacion.json', 'w', encoding='utf-8') as file:
            json.dump(noticias, file, ensure_ascii=False, indent=4)
        logger.info("Proceso completado. Archivo guardado como noticias_con_evaluacion.json")
    except Exception as e:
        logger.error(f"Error al guardar el archivo JSON: {str(e)}", exc_info=True)


def generar_evaluacion_vacia():
    return {
        "preguntas": [],
        "hechos o evidencias": [],
        "conclusiones": [],
        "suposiciones implícitas": [],
        "palabras clave importantes": [],
        "palabras clave deducidas": [],
        "sujetos importantes": [],
        "lugares físicos": [],
        "medios de información o sitios web": [],
        "resumen": "No evaluado"
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger()
    
    procesar_noticias()