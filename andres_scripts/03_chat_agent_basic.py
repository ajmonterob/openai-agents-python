"""
Chat Agent Básico con Múltiples Idiomas y Herramientas

Este script demuestra un chat interactivo que:
1. Utiliza un sistema de triage para detectar el idioma del usuario
2. Implementa handoffs automáticos entre agentes especializados
3. Proporciona herramientas para clima y cálculos matemáticos
4. Maneja interacciones en español e inglés

Conceptos clave:
- Uso de agentes especializados por idioma
- Sistema de triage para detección de idioma
- Implementación de herramientas funcionales
- Manejo de handoffs entre agentes
"""

import asyncio
from pydantic import BaseModel
from agents import Agent, Runner, function_tool

# Modelos de datos para las herramientas
class Weather(BaseModel):
    """
    Modelo para representar información meteorológica.
    
    Attributes:
        city (str): Nombre de la ciudad consultada
        temperature_range (str): Rango de temperatura en formato '14-20C'
        conditions (str): Descripción de las condiciones climáticas
    """
    city: str
    temperature_range: str
    conditions: str

class CalculatorResult(BaseModel):
    """
    Modelo para representar resultados de cálculos matemáticos.
    
    Attributes:
        operation (str): Operación matemática realizada
        result (float): Resultado del cálculo
    """
    operation: str
    result: float

# Herramienta para obtener el clima
@function_tool
def get_weather(city: str) -> Weather:
    """
    Obtiene información del clima para una ciudad específica.
    
    Args:
        city (str): Nombre de la ciudad para consultar el clima
        
    Returns:
        Weather: Objeto con información del clima incluyendo temperatura y condiciones
    """
    print(f"[DEBUG] Consultando clima para: {city}")
    return Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind."
    )

# Herramienta para cálculos matemáticos
@function_tool
def calculate(operation: str) -> CalculatorResult:
    """
    Realiza cálculos matemáticos basados en una expresión.
    
    Args:
        operation (str): Expresión matemática a evaluar
        
    Returns:
        CalculatorResult: Objeto con la operación y su resultado
    """
    print(f"[DEBUG] Realizando cálculo: {operation}")
    try:
        result = eval(operation)
        return CalculatorResult(operation=operation, result=result)
    except Exception as e:
        print(f"[ERROR] Error en cálculo: {str(e)}")
        return CalculatorResult(operation=operation, result=float('nan'))

# Crear los agentes especializados
spanish_agent = Agent(
    name="Spanish Assistant",
    instructions="""Eres un asistente amigable que habla español.
    Debes responder SIEMPRE en español.
    Puedes:
    - Dar información sobre el clima usando la herramienta get_weather
    - Hacer cálculos matemáticos usando la herramienta calculate
    - Mantener conversaciones amigables
    - Ayudar con preguntas generales
    """,
    tools=[get_weather, calculate],
)

english_agent = Agent(
    name="English Assistant",
    instructions="""You are a friendly assistant that speaks English.
    You must ALWAYS respond in English.
    You can:
    - Provide weather information using the get_weather tool
    - Perform mathematical calculations using the calculate tool
    - Engage in friendly conversations
    - Help with general questions
    """,
    tools=[get_weather, calculate],
)

# Crear el agente triage
triage_agent = Agent(
    name="Triage Assistant",
    instructions="""You are a language detection assistant.
    Your ONLY job is to detect the language and handoff to the appropriate agent.
    
    Rules for language detection:
    1. If the input contains Spanish words or characters (á, é, í, ó, ú, ñ, ¿, ¡), handoff to spanish_agent
    2. If the input contains English words, handoff to english_agent
    3. If both languages are detected, prioritize Spanish
    4. If no language is clearly detected, handoff to english_agent
    
    DO NOT respond to the user directly. ONLY detect the language and handoff.
    """,
    handoffs=[spanish_agent, english_agent],
)

async def chat():
    """
    Función principal que maneja la interacción del chat.
    Permite entrada en español o inglés y gestiona las respuestas
    a través del sistema de triage y agentes especializados.
    """
    print("\n=== Chat Interactivo Multilingüe ===")
    print("🌍 Puedes escribir en español o inglés.")
    print("💡 Prueba preguntar sobre el clima o hacer cálculos.")
    print("🚪 Escribe 'exit' para salir.\n")
    
    while True:
        try:
            user_input = input("👤 Tú: ")
            
            if user_input.lower() == 'exit':
                print("\n👋 ¡Hasta luego! / Goodbye!\n")
                break
                
            print("\n⏳ Procesando...")
            result = await Runner.run(triage_agent, input=user_input)
            print("\n🤖 Asistente:", result.final_output)
            print()
            
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Por favor, intenta de nuevo.\n")

if __name__ == "__main__":
    asyncio.run(chat()) 