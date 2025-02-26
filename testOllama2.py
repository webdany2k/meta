import requests

# URL de la API (asegúrate de cambiarla por la correcta)
api_url = "https://api.llama.com/v1/completions"

# Definición de la función que vamos a utilizar en la API
function_definitions = [
    {
        "name": "get_user_info",
        "description": "Retrieve details for a specific user by their unique identifier.",
        "parameters": {
            "type": "dict",
            "required": ["user_id"],
            "properties": {
                "user_id": {
                    "type": "integer",
                    "description": "The unique identifier of the user."
                },
                "special": {
                    "type": "string",
                    "description": "Any special information or parameters that need to be considered while fetching user details.",
                    "default": "none"
                }
            }
        }
    }
]

# Prompt del sistema que indica cómo el modelo debe comportarse
system_prompt = """You are an expert in composing functions. You are given a question and a set of possible functions. 
Based on the question, you will need to make one or more function/tool calls to achieve the purpose. 
If none of the function can be used, point it out. If the given question lacks the parameters required by the function,
also point it out. You should only return the function call in tools call sections.
Here is a list of functions in JSON format that you can invoke.\n\n{}""".format(function_definitions)

# Prompt del usuario que hace la solicitud
query = "Can you retrieve the details for the user with the ID 7890, who has black as their special request?"

# Configuramos el payload para la API
payload = {
    "system": system_prompt,
    "user": query
}

# Hacemos la solicitud a la API
response = requests.post(api_url, json=payload)

# Imprimimos la respuesta de la API
print(response.json())
