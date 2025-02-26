import json
import requests
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup

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

# Función para crear el prompt con instrucciones explícitas
def crear_prompt(noticia):
    contenido_limpio = limpiar_html(noticia["contenido"])
    contenido_truncado = truncar_texto(contenido_limpio)
    
    # Instrucciones explícitas para la evaluación
    prompt = (
        f"Analiza la siguiente noticia y proporciona una evaluación con los siguientes puntos:\n"
        f"1. Orientación política (izquierda, centro, derecha)\n"
        f"2. Sentimiento (positivo, negativo, neutral)\n"
        f"3. Estado o país mencionado\n"
        f"4. Nivel de agresividad (baja, media, alta)\n"
        f"5. Violencia (sí, no)\n"
        f"6. Controversia (alta, media, baja)\n\n"
        f"Noticia:\n{contenido_truncado}\n"
        f"Por favor, evalúa cada aspecto de manera clara y concisa y regresa la respuesta en una sola palabra de cada una de las 6 evaluaciones, omite cualquier detalle, solo da una palabra de respuesta y NUNCA incluyas caracteres especiales."
    )
    
    return prompt

# Función para enviar el contenido de la noticia al modelo Llama 3.2
def enviar_a_nlp(noticia):
    try:
        # Crear el prompt con instrucciones
        prompt = crear_prompt(noticia)
        
        # Payload para enviar a la API
        payload = {
            "model": "llama3.2",  # Especificar el modelo correcto
            "prompt": prompt,
            "max_tokens": 1000
        }

        # Headers para la solicitud
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer tu_token_api',  # Si es necesario
        }

        # Depuración: Imprimir el payload antes de enviar
        print(f"Enviando payload: {payload}")
        
        # Solicitud POST a la API
        response = requests.post(API_URL, headers=headers, json=payload)

        # Verificar si la solicitud fue exitosa
        if response.status_code == 200:
            # Acumular toda la respuesta
            full_response = ""
            for line in response.iter_lines():
                if line:
                    try:
                        # Decodificar cada fragmento como JSON y acumular la respuesta
                        data = json.loads(line)
                        full_response += data.get("response", "")
                    except json.JSONDecodeError:
                        print(f"Error al decodificar la línea: {line.decode('utf-8')}")
            
            # Imprimir la respuesta completa para depuración
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
def procesar_respuesta(respuesta):
    # Parsear la respuesta y asignar los valores a cada etiqueta
    evaluacion = {
        "orientacion_politica": "Desconocida",
        "sentimiento": "Neutral",
        "estado_pais": "No disponible",
        "agresividad": "Baja",
        "violencia": "No",
        "controversia": "No"
    }

    # Extraer los valores de la respuesta y asignar a las claves correspondientes
    if "orientación política" in respuesta.lower():
        evaluacion["orientacion_politica"] = extraer_valor("orientación política", respuesta)
    if "sentimiento" in respuesta.lower():
        evaluacion["sentimiento"] = extraer_valor("sentimiento", respuesta)
    if "estado o país mencionado" in respuesta.lower():
        evaluacion["estado_pais"] = extraer_valor("estado o país mencionado", respuesta)
    if "nivel de agresividad" in respuesta.lower():
        evaluacion["agresividad"] = extraer_valor("nivel de agresividad", respuesta)
    if "violencia" in respuesta.lower():
        evaluacion["violencia"] = extraer_valor("violencia", respuesta)
    if "controversia" in respuesta.lower():
        evaluacion["controversia"] = extraer_valor("controversia", respuesta)
    
    return evaluacion

# Función para extraer valores desde la respuesta usando etiquetas
def extraer_valor(etiqueta, texto):
    try:
        inicio = texto.lower().index(etiqueta.lower()) + len(etiqueta) + 1
        fin = texto.index("\n", inicio)
        return texto[inicio:fin].strip()
    except ValueError:
        return "No evaluado"

# Función para procesar y etiquetar cada noticia
def procesar_noticias():
    noticias = leer_noticias()

    # Iterar sobre cada noticia
    for noticia in noticias:
        print(f"Procesando noticia: {noticia['titulo']}")

        # Enviar noticia al modelo Llama 3.2
        nlp_response = enviar_a_nlp(noticia)

        # Si la respuesta es exitosa, interpretar las etiquetas generadas
        if nlp_response:
            # Procesar la respuesta para extraer etiquetas
            evaluacion = procesar_respuesta(nlp_response)

            # Asignar los valores procesados a la noticia
            noticia["evaluacion"] = evaluacion
        
        else:
            # Si hay un error en la respuesta, asignar valores predeterminados
            noticia["evaluacion"] = {
                "orientacion_politica": "No evaluada",
                "sentimiento": "No evaluada",
                "estado_pais": "No evaluada",
                "agresividad": "No evaluada",
                "violencia": "No evaluada",
                "controversia": "No evaluada"
            }

    # Guardar el archivo con las noticias procesadas y evaluadas
    with open('./clean/noticias_con_evaluacion.json', 'w', encoding='utf-8') as file:
        json.dump(noticias, file, ensure_ascii=False, indent=4)

    print("Proceso completado. Archivo guardado como noticias_con_evaluacion.json")

# Ejecutar la función principal
if __name__ == '__main__':
    procesar_noticias()