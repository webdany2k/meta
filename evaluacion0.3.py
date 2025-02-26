import json
import requests
import os
import re  # <--- Asegúrate de importar 're' aquí
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

# Función para crear el prompt simplificado
def crear_prompt(noticia):
    contenido_limpio = limpiar_html(noticia["contenido"])
    contenido_truncado = truncar_texto(contenido_limpio)
    
    # Instrucciones explícitas según el modelo solicitado
    prompt = (
        f"De acuerdo al modelo Questions/Evidences/Conclusions, evalúa el texto con los siguientes parámetros:\n"
        f"1. 'questions': preguntas que se plantean en el texto.\n"
        f"2. 'evidences': hechos o evidencias que sustentan el texto.\n"
        f"3. 'conclusions': las conclusiones escritas en la noticia.\n"
        f"4. 'hiddenConclusions': suposiciones implícitas.\n\n"
        f"Aparte, proporciona:\n"
        f"5. 'keyWords': las palabras clave más importantes del texto.\n"
        f"6. 'deductedKeyWords': palabras clave deducidas de questions, evidences y conclusions.\n"
        f"7. 'subjects': los sujetos importantes mencionados.\n"
        f"8. 'landPlaces': lugares físicos mencionados.\n"
        f"9. 'virtualPlaces': medios de información o sitios web mencionados.\n\n"
        f"Noticia:\n{contenido_truncado}\n"
        f"Evalúa cada parámetro de manera clara y concisa."
    )
    
    return prompt

# Función para enviar el contenido de la noticia al modelo Llama 3.2 y gestionar respuestas fragmentadas
def enviar_a_nlp(noticia):
    try:
        # Crear el prompt con instrucciones
        prompt = crear_prompt(noticia)
        
        # Payload para enviar a la API
        payload = {
            "model": "llama3.2",  # Especificar el modelo correcto
            "prompt": prompt,
            "max_tokens": 10000
        }

        # Headers para la solicitud
        headers = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer tu_token_api',  # Si es necesario
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
def procesar_respuesta(respuesta):
    evaluacion = {
        "questions": extraer_seccion("Questions", respuesta),
        "evidences": extraer_seccion("Evidences", respuesta),
        "conclusions": extraer_seccion("Conclusions", respuesta),
        "hiddenConclusions": extraer_seccion("HiddenConclusions", respuesta),
        "keyWords": extraer_lista_seccion("KeyWords", respuesta),
        "deductedKeyWords": extraer_lista_seccion("DeductedKeyWords", respuesta),
        "subjects": extraer_lista_seccion("Subjects", respuesta),
        "landPlaces": extraer_lista_seccion("LandPlaces", respuesta),
        "virtualPlaces": extraer_lista_seccion("VirtualPlaces", respuesta)
    }

    return evaluacion

# Función para extraer una sección por encabezado usando expresiones regulares
def extraer_seccion(encabezado, texto):
    # Buscar el encabezado en el formato **Encabezado**
    patron = rf"\*\*{encabezado}\*\*:\s*(.*?)(?=\n\*\*|$)"  # Captura hasta el próximo encabezado o el final del texto
    resultado = re.search(patron, texto, re.DOTALL)
    if resultado:
        return resultado.group(1).strip()
    return "No evaluado"

# Función para extraer listas desde la respuesta que son múltiples valores
def extraer_lista_seccion(encabezado, texto):
    seccion = extraer_seccion(encabezado, texto)
    if seccion != "No evaluado":
        return [palabra.strip() for palabra in seccion.split('\n') if palabra.strip()]
    return []

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
                "questions": "No evaluado",
                "evidences": "No evaluado",
                "conclusions": "No evaluado",
                "hiddenConclusions": "No evaluado",
                "keyWords": [],
                "deductedKeyWords": [],
                "subjects": [],
                "landPlaces": [],
                "virtualPlaces": []
            }

    # Guardar el archivo con las noticias procesadas y evaluadas
    with open('./clean/noticias_con_evaluacion.json', 'w', encoding='utf-8') as file:
        json.dump(noticias, file, ensure_ascii=False, indent=4)

    print("Proceso completado. Archivo guardado como noticias_con_evaluacion.json")

# Ejecutar la función principal
if __name__ == '__main__':
    procesar_noticias()