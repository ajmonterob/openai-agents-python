"""
Chat Agent con Memoria Unificada [DEBUG]

Este script implementa un sistema de chat multilingüe con memoria unificada,
donde todos los agentes comparten el mismo contexto de conversación.
Esta versión incluye mensajes de debug para analizar el flujo del programa.

Objetivo:
- Demostrar cómo implementar un sistema de memoria compartida entre agentes
- Mantener la coherencia de la conversación independientemente del idioma
- Preservar el contexto durante los handoffs entre agentes

Características Principales:
1. Sistema de Memoria Unificada:
   - Un solo contexto compartido entre todos los agentes
   - Historial de conversación accesible por todos los agentes
   - Coherencia mantenida a través de cambios de idioma

2. Sistema de Handoff con Contexto Compartido:
   - Triage agent para detección de idioma
   - Preservación del contexto durante handoffs
   - Transiciones suaves entre idiomas

3. Instrucciones Dinámicas:
   - Cada agente recibe el historial completo en tiempo real
   - Respuestas coherentes con toda la conversación
   - Mantenimiento de contexto entre idiomas

4. Herramientas y Funcionalidades:
   - Consulta del clima
   - Cálculos matemáticos
   - Conversación multilingüe
   - Memoria persistente

Evolución del Código:
- chat_agent_basic (03): Sin sistema de memoria
- chat_agent_with_memory (04): Memoria segregada por idioma [NO FUNCIONAL]
- chat_agent_with_unified_memory (05): Memoria unificada [ACTUAL]
  * Implementa memoria compartida entre agentes
  * Mantiene coherencia en conversaciones multilingües
  * Preserva contexto durante handoffs

Lecciones Aprendidas:
1. La memoria unificada es más efectiva para conversaciones multilingües
2. El contexto compartido mejora la experiencia del usuario
3. Los handoffs deben preservar el contexto completo
4. Las instrucciones dinámicas son clave para mantener coherencia

Autor: Andres Montero
Fecha: Marzo 2024
"""

import asyncio
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig, HandoffInputData, RunContextWrapper

# Configuración de debug
DEBUG = True

def debug_print(message: str):
    """Imprime mensajes de debug si DEBUG está activado"""
    if DEBUG:
        print(f"[DEBUG] {message}")

@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
        debug_print(f"Mensaje agregado al historial: {role}: {content}")
        debug_print(f"Total de mensajes en historial: {len(self.history)}")
    
    def get_history(self) -> str:
        debug_print(f"Obteniendo historial completo ({len(self.history)} mensajes)")
        return "\n".join(self.history)

class Weather(BaseModel):
    location: str
    temperature: float
    condition: str

class CalculatorResult(BaseModel):
    result: float

@function_tool
def get_weather(location: str) -> Weather:
    """Obtiene el clima actual para una ubicación"""
    debug_print(f"Herramienta get_weather llamada con location={location}")
    return Weather(
        location=location,
        temperature=25.0,
        condition="soleado"
    )

@function_tool
def calculate(expression: str) -> CalculatorResult:
    """Evalúa una expresión matemática"""
    debug_print(f"Herramienta calculate llamada con expression={expression}")
    try:
        result = eval(expression)
        debug_print(f"Resultado del cálculo: {result}")
        return CalculatorResult(result=float(result))
    except Exception as e:
        debug_print(f"Error en cálculo: {str(e)}")
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

def create_spanish_agent() -> Agent[ChatMemoryContext]:
    debug_print("Creando agente en español")
    return Agent[ChatMemoryContext](
        name="Asistente Español",
        model="gpt-4-turbo-preview",
        instructions=dynamic_spanish_instructions,
        tools=[get_weather, calculate]
    )

def create_english_agent() -> Agent[ChatMemoryContext]:
    debug_print("Creando agente en inglés")
    return Agent[ChatMemoryContext](
        name="English Assistant",
        model="gpt-4-turbo-preview",
        instructions=dynamic_english_instructions,
        tools=[get_weather, calculate]
    )

def create_triage_agent(spanish_agent: Agent[ChatMemoryContext], english_agent: Agent[ChatMemoryContext]) -> Agent[ChatMemoryContext]:
    debug_print("Creando agente de triaje")
    return Agent[ChatMemoryContext](
        name="Triage Assistant",
        model="gpt-4-turbo-preview",
        instructions="""Eres un agente de triaje que detecta el idioma del usuario.
        Si detectas español, transfiere la conversación al Asistente Español.
        Si detectas inglés, transfiere la conversación al English Assistant.
        Si detectas ambos idiomas, prioriza el español.
        No respondas directamente, solo transfiere la conversación.
        
        DEBUG - Palabras clave para detección:
        - Español: hola, gracias, como, qué, por favor, bien
        - Inglés: hello, thanks, how, what, please, good""",
        handoffs=[spanish_agent, english_agent]
    )

# Función para preservar el contexto durante los handoffs
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    debug_print(f"Handoff detectado - preservando contexto completo")
    # Simplemente pasamos todos los datos sin modificar
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )

async def chat():
    # Crear el contexto compartido
    debug_print("Iniciando chat con memoria unificada")
    context = ChatMemoryContext()
    
    # Crear los agentes
    debug_print("Inicializando agentes...")
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    triage_agent = create_triage_agent(spanish_agent, english_agent)
    
    # Configurar el Runner para preservar el contexto
    debug_print("Configurando Runner con filtro de handoff")
    run_config = RunConfig(
        handoff_input_filter=memory_handoff_filter
    )
    
    print("¡Bienvenido! Puedes escribir en español o inglés.")
    print("Escribe 'salir' para terminar la conversación.")
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() == "salir":
            debug_print("Usuario solicitó salir")
            print("¡Hasta luego!")
            break
            
        debug_print(f"=== PROCESANDO ENTRADA: '{user_input}' ===")
        
        # Agregar el mensaje del usuario al historial
        context.add_message("Usuario", user_input)
        
        # Ejecutar el chat con el agente de triaje
        debug_print("Enviando mensaje al agente de triaje para detección de idioma")
        result = await Runner.run(
            triage_agent,
            input=user_input,
            context=context,
            run_config=run_config
        )
        
        debug_print(f"=== RESPUESTA RECIBIDA ===")
        debug_print(f"Tipo de respuesta: handoff o respuesta directa")
        
        if hasattr(result, 'thoughts') and result.thoughts:
            debug_print(f"Razonamiento: {result.thoughts}")
        
        # Agregar la respuesta al historial
        debug_print(f"Respuesta final: {result.final_output}")
        context.add_message("Asistente", result.final_output)
        print(f"\nAsistente: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(chat())
