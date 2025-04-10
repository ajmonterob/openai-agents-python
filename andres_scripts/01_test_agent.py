"""
Objetivo: Primer contacto con el SDK de OpenAI Agents

Este script representa nuestro primer acercamiento al SDK, donde exploramos:
1. Creación básica de agentes con instrucciones simples
2. Concepto de "handoff" entre agentes
3. Uso básico del Runner para ejecutar agentes

Aprendizajes clave:
- Cómo crear agentes con instrucciones básicas
- Cómo configurar handoffs entre agentes
- Cómo usar el Runner para ejecutar agentes
- Estructura básica de un script con agentes

Test simple:
- Envía un mensaje en español y otro en inglés
- Verifica que el triage_agent dirija cada mensaje al agente correcto
"""

import asyncio
from agents import Agent, Runner


# Crear el agente en español
spanish_agent = Agent(
    name="Spanish agent",
    instructions="You only speak Spanish.",  # Instrucción simple: solo responder en español
)

# Crear el agente en inglés
english_agent = Agent(
    name="English agent",
    instructions="You only speak English",  # Instrucción simple: solo responder en inglés
)

# Crear el agente triage que decide a qué agente transferir
triage_agent = Agent(
    name="Triage agent",
    instructions="Handoff to the appropriate agent based on the language of the request.",  # Instrucción para decidir el idioma
    handoffs=[spanish_agent, english_agent],  # Lista de agentes a los que puede transferir
)

async def main():
    print("=== Test de Agentes Multilenguaje ===")
    print("Probando handoff basado en idioma...")
    
    # Probar con una pregunta en español
    print("\nPrueba 1: Mensaje en español")
    result = await Runner.run(triage_agent, input="Hola, ¿cómo estás?")
    print("Input: 'Hola, ¿cómo estás?'")
    print("Respuesta:", result.final_output)
    
    # Probar con una pregunta en inglés
    print("\nPrueba 2: Mensaje en inglés")
    result = await Runner.run(triage_agent, input="Hello, how are you?")
    print("Input: 'Hello, how are you?'")
    print("Respuesta:", result.final_output)

if __name__ == "__main__":
    print("\nIniciando pruebas de agentes...")
    asyncio.run(main())
    print("\nPruebas completadas.") 