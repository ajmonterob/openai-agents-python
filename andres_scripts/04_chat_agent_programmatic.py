import asyncio
import re
from dataclasses import dataclass, field
from typing import List, Tuple
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig, RunContextWrapper

@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
    
    def get_history(self) -> str:
        return "\n".join(self.history)

class Weather(BaseModel):
    location: str
    temperature: float
    condition: str

class CalculatorResult(BaseModel):
    result: float

class LanguageDetection(BaseModel):
    language: str
    confidence: float

@function_tool
def get_weather(location: str) -> Weather:
    """Obtiene el clima actual para una ubicación"""
    return Weather(
        location=location,
        temperature=25.0,
        condition="soleado"
    )

@function_tool
def calculate(expression: str) -> CalculatorResult:
    """Evalúa una expresión matemática"""
    try:
        result = eval(expression)
        return CalculatorResult(result=float(result))
    except Exception as e:
        return CalculatorResult(result=0.0)

# Función dinámica para instrucciones en español
def dynamic_spanish_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    return f"""Eres un asistente en español. 
    Siempre responde en español.
    
    IMPORTANTE: Revisa el historial de la conversación antes de responder:
    
    {history}
    
    Mantén la coherencia con los mensajes anteriores. Si el usuario menciona algo 
    que se habló antes, debes tenerlo en cuenta en tu respuesta.
    
    Tienes acceso a las siguientes herramientas:
    - get_weather: Para obtener el clima
    - calculate: Para hacer cálculos matemáticos"""

# Función dinámica para instrucciones en inglés
def dynamic_english_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    return f"""You are an English assistant.
    Always respond in English.
    
    IMPORTANT: Review the conversation history before responding:
    
    {history}
    
    Maintain coherence with previous messages. If the user refers to something 
    that was discussed earlier, you should take it into account in your response.
    
    You have access to the following tools:
    - get_weather: To get weather information
    - calculate: To perform mathematical calculations"""

# Función para el agente detector de idioma
def create_language_detector() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Language Detector",
        model="gpt-4-turbo-preview",
        instructions="""Eres un agente cuya única función es detectar el idioma del texto.
        NO respondas en ese idioma ni entables conversación.
        SOLO devuelve: 
        - "spanish" si el texto está en español
        - "english" si el texto está en inglés
        
        Si el texto contiene ambos idiomas, elige el que predomina.""",
        output_type=str
    )

def create_spanish_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Asistente Español",
        model="gpt-4-turbo-preview",
        instructions=dynamic_spanish_instructions,
        tools=[get_weather, calculate]
    )

def create_english_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="English Assistant",
        model="gpt-4-turbo-preview",
        instructions=dynamic_english_instructions,
        tools=[get_weather, calculate]
    )

def detect_language(text: str) -> str:
    """Detección rápida del idioma basada en patrones simples"""
    # Palabras y caracteres específicos del español
    spanish_patterns = ['ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü', '¿', '¡', 
                        'como', 'qué', 'cómo', 'hola', 'buenos', 'gracias', 
                        'por favor', 'adios', 'día']
    
    # Palabras comunes en inglés
    english_patterns = ['hello', 'the', 'hi', 'thanks', 'what', 'where', 
                        'when', 'who', 'why', 'how', 'please', 'good']
    
    text = text.lower()
    
    # Contar coincidencias
    spanish_count = sum(1 for pattern in spanish_patterns if pattern in text)
    english_count = sum(1 for pattern in english_patterns if pattern in text)
    
    # Si hay una diferencia clara, determinar el idioma
    if spanish_count > english_count:
        return "spanish"
    else:
        return "english"

async def chat():
    # Crear el contexto compartido
    context = ChatMemoryContext()
    
    # Crear los agentes
    language_detector = create_language_detector()
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    
    # Configurar el Runner
    run_config = RunConfig()
    
    print("¡Bienvenido! Puedes escribir en español o inglés.")
    print("Escribe 'salir' para terminar la conversación.")
    
    # Mantener el último idioma utilizado para eficiencia
    last_language = None
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() == "salir":
            break
            
        # Agregar el mensaje del usuario al historial
        context.add_message("Usuario", user_input)
        
        # Paso 1: Determinar el idioma usando nuestra propia lógica primero para eficiencia
        language = detect_language(user_input)
        
        # Si el último mensaje fue en el mismo idioma, no necesitamos consultar al LLM
        if last_language is None or last_language != language:
            # Doble verificación con el LLM si es necesario para casos ambiguos
            if len(user_input.split()) > 3:  # Solo para mensajes con más de 3 palabras
                try:
                    # Utilizamos el agente detector de idioma
                    language_result = await Runner.run(
                        language_detector,
                        input=user_input,
                        context=context,
                        run_config=run_config
                    )
                    detected_language = language_result.final_output.strip().lower()
                    
                    # Validar que la respuesta sea válida
                    if detected_language in ["spanish", "english"]:
                        language = detected_language
                except Exception as e:
                    print(f"Error detectando idioma: {e}")
                    # Continuamos con la detección simple
        
        last_language = language
            
        # Paso 2: Seleccionar el agente apropiado basado en el idioma
        selected_agent = spanish_agent if language == "spanish" else english_agent
        
        print(f"[DEBUG]: Idioma detectado: {language}, usando {selected_agent.name}")
        
        # Paso 3: Ejecutar el agente seleccionado
        result = await Runner.run(
            selected_agent,
            input=user_input,
            context=context,
            run_config=run_config
        )
        
        # Agregar la respuesta al historial
        context.add_message("Asistente", result.final_output)
        print(f"\nAsistente: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(chat()) 