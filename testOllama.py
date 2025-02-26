import os
import requests
import random
import json
import textwrap
from dotenv import load_dotenv

# Cargar variables de entorno del archivo .env
load_dotenv()

# Obtener la URL de la API desde el archivo .env
api_url = os.getenv("API_URL")

# Función para obtener la pregunta del usuario
def obtener_pregunta_usuario():
    return input("Escribe una pregunta para el modelo: ")

# Función para formatear la respuesta
def formatear_respuesta(texto):
    parrafos = texto.split('\n')  # Separar párrafos
    texto_formateado = "\n".join([textwrap.fill(parrafo, width=80) for parrafo in parrafos])
    return texto_formateado

# Función para guardar la respuesta en un archivo
def guardar_respuesta(pregunta, respuesta):
    with open("respuesta_ollama.txt", "a", encoding="utf-8") as f:
        f.write(f"Pregunta: {pregunta}\n")
        f.write(f"Respuesta:\n{respuesta}\n")
        f.write("="*80 + "\n")  # Separador entre respuestas

# Función para estructurar el prompt usando los roles recomendados
def estructurar_prompt(pregunta):
    system_prompt = """<|start_header_id|>system<|end_header_id|>
Tu trabajo es contestar las preguntas lo mas asertivamente posible.
Tienes acceso a un conjunto de funciones que puedes usar para recuperar información cuando la necesites.
Si una pregunta es ambigua o no tienes suficiente información, debes pedir una aclaración.\n"""
    
    user_prompt = f"<|start_header_id|>user<|end_header_id|>\n{pregunta}\n"
    
    assistant_prompt = "<|start_header_id|>assistant<|end_header_id|>\n"
    
    prompt_completo = system_prompt + user_prompt + assistant_prompt
    return prompt_completo

# Función para hacer la solicitud a la API con el prompt estructurado
def hacer_solicitud_api():
    try:
        pregunta = obtener_pregunta_usuario()
        
        # Estructurar el prompt usando los roles
        prompt = estructurar_prompt(pregunta)

        # Crear el payload para la consulta a la API
        payload = {
            "model": "llama3.2",
            "prompt": prompt,
            "max_tokens": 10000  # Ajusta el límite de tokens si es necesario
        }

        # Hacer la solicitud POST a la API con timeout de 10 segundos
        response = requests.post(api_url, json=payload, timeout=10)

        # Verificar si la solicitud fue exitosa (status code 200)
        response.raise_for_status()  # Esto lanzará un error si el código no es 200

        respuesta_completa = ""  # Aquí almacenamos la respuesta completa

        # Procesar cada línea de la respuesta en streaming
        for line in response.iter_lines():
            if line:
                try:
                    # Decodificar la línea como JSON usando el módulo json estándar
                    json_line = line.decode('utf-8')
                    data = json.loads(json_line)  # Convertir a JSON usando el módulo correcto
                    respuesta_completa += data["response"]  # Acumular respuesta

                    # Si done es True, terminamos de recibir la respuesta
                    if data.get("done", False):
                        break
                except json.JSONDecodeError as e:
                    print(f"Error procesando línea JSON: {e}")
                    return  # Salir en caso de error

        # Formatear la respuesta recibida
        respuesta_formateada = formatear_respuesta(respuesta_completa)

        # Mostrar pregunta y respuesta formateada
        print(f"Pregunta: {pregunta}")
        print(f"Respuesta:\n{respuesta_formateada}")

        # Guardar la respuesta en un archivo
        guardar_respuesta(pregunta, respuesta_formateada)

    except requests.exceptions.HTTPError as http_err:
        print(f"Error HTTP en la solicitud: {http_err}")
    except requests.exceptions.ConnectionError:
        print("Error de conexión. Verifica tu conexión a Internet o la URL de la API.")
    except requests.exceptions.Timeout:
        print("Error: La solicitud ha excedido el tiempo de espera.")
    except requests.exceptions.RequestException as err:
        print(f"Error en la solicitud: {err}")
    except Exception as e:
        print(f"Error inesperado: {e}")

# Ejecutar la función para hacer la solicitud a la API
hacer_solicitud_api()
