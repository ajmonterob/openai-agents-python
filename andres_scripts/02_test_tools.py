"""
Objetivo: Exploración de Herramientas (Tools) en el SDK de OpenAI Agents

Este script representa nuestro primer acercamiento a la creación y uso de herramientas personalizadas, donde exploramos:
1. Definición de modelos Pydantic para estructurar datos
2. Creación de herramientas usando el decorador @function_tool
3. Integración de herramientas con agentes
4. Manejo de tipos y validación de datos

Aprendizajes clave:
- Cómo crear modelos de datos usando Pydantic
- Cómo definir y decorar funciones como herramientas
- Cómo integrar herramientas con agentes
- Cómo manejar tipos de datos y validación
- Cómo hacer debug de llamadas a herramientas

Conceptos nuevos respecto al script 01:
- Uso de Pydantic para modelado de datos
- Decoradores para crear herramientas
- Tipado fuerte en Python
- Debug de herramientas
"""

import asyncio
from pydantic import BaseModel
from agents import Agent, Runner, function_tool

# Definir un modelo para la respuesta del clima
class Weather(BaseModel):
    """
    Modelo que define la estructura de datos para información del clima
    
    Attributes:
        city: Nombre de la ciudad
        temperature_range: Rango de temperatura en formato string
        conditions: Descripción de las condiciones climáticas
    """
    city: str
    temperature_range: str
    conditions: str

# Crear una herramienta para obtener el clima
@function_tool
def get_weather(city: str) -> Weather:
    """
    Herramienta que simula obtener el clima para una ciudad
    
    Args:
        city: Nombre de la ciudad para consultar el clima
        
    Returns:
        Weather: Objeto con la información del clima
    """
    print(f"[DEBUG] get_weather llamada para la ciudad: {city}")
    return Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind."
    )

# Crear el agente con la herramienta
agent = Agent(
    name="Weather Agent",
    instructions="""You are a helpful weather assistant. 
    Use the get_weather tool to answer questions about the weather.
    Always mention both the temperature range and conditions in your response.
    Format temperatures clearly with units.
    """,
    tools=[get_weather],
)

async def main():
    print("=== Test de Agente con Herramientas ===")
    print("Probando herramienta get_weather...")
    
    # Probar con una pregunta sobre el clima
    test_city = "Tokyo"
    print(f"\nPrueba: Consulta del clima para {test_city}")
    print(f"Input: 'What's the weather in {test_city}?'")
    
    result = await Runner.run(agent, input=f"What's the weather in {test_city}?")
    print("\nRespuesta del agente:", result.final_output)

if __name__ == "__main__":
    print("\nIniciando prueba de agente con herramientas...")
    asyncio.run(main())
    print("\nPrueba completada.") 