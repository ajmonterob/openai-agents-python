"""
Chat Agent con Primer Intento de Memoria

Este script representa un primer intento de implementar memoria en el chat,
aunque con limitaciones importantes en la compartición de contexto entre agentes.

Características Principales:
1. Sistema de Memoria (Con Limitaciones):
   - Implementa un contexto (ChatMemoryContext)
   - Intenta mantener historial de conversación
   - ⚠️ La memoria no se comparte efectivamente entre agentes durante handoffs
   - ⚠️ Cada agente pierde contexto al recibir el control

2. Sistema de Handoff Básico:
   - Triage agent para detección de idioma
   - Intento de transferencia de contexto
   - ⚠️ El contexto se pierde durante los handoffs
   - ⚠️ Los agentes no mantienen coherencia entre cambios

3. Sistema de Debugging:
   - Hooks para monitoreo de eventos
   - Trazabilidad de handoffs
   - Ayuda a identificar problemas de memoria
   - Muestra pérdida de contexto entre agentes

4. Limitaciones Identificadas:
   - La memoria no persiste efectivamente entre handoffs
   - Los agentes no pueden acceder al historial completo
   - Las respuestas pierden coherencia entre cambios de idioma
   - El sistema de handoff no preserva el contexto

Evolución del Código:
- chat_agent_basic (03): Sin sistema de memoria
- chat_agent_with_memory (04): Primer intento de memoria [ACTUAL]
  * Introduce el concepto de contexto compartido
  * Identifica problemas de pérdida de memoria
  * Sienta las bases para mejoras futuras
- chat_agent_with_unified_memory (05): Resuelve problemas de memoria
- Versiones posteriores: Mejoran el control y coherencia

Lecciones Aprendidas:
1. La implementación básica de RunConfig no es suficiente
2. Se necesita un sistema más robusto de preservación de contexto
3. Los handoffs deben manejar mejor la transferencia de estado
4. El debugging ayuda a identificar pérdidas de memoria

Autor: Andres Montero
Fecha: Marzo 2024
"""

import asyncio
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig, HandoffInputData, RunContextWrapper, RunHooks, Tool

@dataclass
class ChatMemoryContext:
    """
    Primer intento de sistema de memoria compartida.
    
    ⚠️ Limitaciones Conocidas:
    1. El contexto no se preserva efectivamente durante handoffs
    2. Los agentes pierden acceso al historial previo
    3. No hay verdadera compartición de memoria entre agentes
    
    Esta implementación sirve principalmente para:
    - Identificar problemas de pérdida de contexto
    - Establecer base para futuras mejoras
    - Demostrar necesidad de un sistema más robusto
    
    Attributes:
        conversation_history (List[dict]): Lista de mensajes que intenta
        mantener el historial, pero se pierde durante handoffs
    """
    conversation_history: List[dict] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        """
        Agrega un mensaje al historial.
        Nota: Este historial se perderá durante handoffs.
        """
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def get_history_as_string(self) -> str:
        """
        Obtiene el historial como texto.
        Nota: Solo contiene mensajes desde el último handoff.
        """
        history = []
        for msg in self.conversation_history:
            history.append(f"{msg['role']}: {msg['content']}")
        return "\n".join(history)

# Definir modelos para las herramientas
class Weather(BaseModel):
    city: str
    temperature_range: str
    conditions: str

class CalculatorResult(BaseModel):
    operation: str
    result: float

# Herramienta para obtener el clima
@function_tool
def get_weather(city: str) -> Weather:
    print(f"[debug] get_weather called for {city}")
    return Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind."
    )

# Herramienta para cálculos matemáticos
@function_tool
def calculate(operation: str) -> CalculatorResult:
    print(f"[debug] calculate called for {operation}")
    try:
        result = eval(operation)
        return CalculatorResult(operation=operation, result=result)
    except Exception as e:
        return CalculatorResult(operation=operation, result=float('nan'))

def create_spanish_agent():
    return Agent[ChatMemoryContext](
        name="Spanish Assistant",
        instructions="""Eres un asistente amigable que habla español.
        Debes responder SIEMPRE en español.
        
        IMPORTANTE: Tienes acceso al historial de la conversación en context.conversation_history
        DEBES revisar el historial completo antes de responder para mantener coherencia.
        
        Para cada mensaje en context.conversation_history:
        - El campo 'role' puede ser 'user' o 'assistant'
        - El campo 'content' contiene el mensaje
        
        ANTES de responder:
        1. Lee TODO el historial de la conversación en context.conversation_history
        2. Busca información relevante como nombres, datos o contexto previo
        3. Asegúrate de que tu respuesta sea coherente con toda la conversación anterior
        4. Si te preguntan por algo mencionado antes, DEBES buscarlo en el historial
        
        Puedes:
        - Dar información sobre el clima usando la herramienta get_weather
        - Hacer cálculos matemáticos usando la herramienta calculate
        - Mantener conversaciones amigables
        - Ayudar con preguntas generales
        """,
        tools=[get_weather, calculate],
    )

def create_english_agent():
    return Agent[ChatMemoryContext](
        name="English Assistant",
        instructions="""You are a friendly assistant that speaks English.
        You must ALWAYS respond in English.
        
        IMPORTANT: You have access to the conversation history in context.conversation_history
        You MUST review the complete history before responding to maintain coherence.
        
        For each message in context.conversation_history:
        - The 'role' field can be 'user' or 'assistant'
        - The 'content' field contains the message
        
        BEFORE responding:
        1. Read ALL the conversation history in context.conversation_history
        2. Look for relevant information like names, data, or previous context
        3. Ensure your response is coherent with all previous conversation
        4. If asked about something mentioned before, you MUST look it up in the history
        
        You can:
        - Provide weather information using the get_weather tool
        - Perform mathematical calculations using the calculate tool
        - Engage in friendly conversations
        - Help with general questions
        """,
        tools=[get_weather, calculate],
    )

def create_triage_agent(spanish_agent: Agent, english_agent: Agent):
    return Agent[ChatMemoryContext](
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

# Hooks para debugging
class ChatHooks(RunHooks[ChatMemoryContext]):
    """
    Sistema de hooks para debugging y monitoreo.
    
    Especialmente útil para:
    - Identificar pérdidas de contexto durante handoffs
    - Monitorear el estado de la memoria
    - Detectar problemas de coherencia
    - Verificar fallos en la transferencia de estado
    """
    async def on_agent_start(self, context: RunContextWrapper[ChatMemoryContext], agent: Agent[ChatMemoryContext]) -> None:
        """Monitorea el inicio de un agente y el estado del contexto"""
        print(f"\n[DEBUG] Starting agent: {agent.name}")
        if context.context and context.context.conversation_history:
            print(f"[DEBUG] Current history size: {len(context.context.conversation_history)} messages")
            print("[DEBUG] Last message:", context.context.conversation_history[-1])

    async def on_agent_end(self, context: RunContextWrapper[ChatMemoryContext], agent: Agent[ChatMemoryContext], output: str) -> None:
        print(f"\n[DEBUG] Agent {agent.name} finished")
        print(f"[DEBUG] Output: {output}")

    async def on_handoff(self, context: RunContextWrapper[ChatMemoryContext], from_agent: Agent[ChatMemoryContext], to_agent: Agent[ChatMemoryContext]) -> None:
        print(f"\n[DEBUG] Handoff from {from_agent.name} to {to_agent.name}")
        if context.context and context.context.conversation_history:
            print(f"[DEBUG] History being passed: {len(context.context.conversation_history)} messages")
            print("[DEBUG] Last message:", context.context.conversation_history[-1])

    async def on_tool_start(self, context: RunContextWrapper[ChatMemoryContext], agent: Agent[ChatMemoryContext], tool: Tool) -> None:
        print(f"\n[DEBUG] Agent {agent.name} starting tool: {tool.name}")

    async def on_tool_end(self, context: RunContextWrapper[ChatMemoryContext], agent: Agent[ChatMemoryContext], tool: Tool, result: str) -> None:
        print(f"\n[DEBUG] Agent {agent.name} finished tool: {tool.name}")
        print(f"[DEBUG] Tool result: {result}")

async def chat():
    """
    Función principal del chat con primer intento de memoria.
    
    ⚠️ Limitaciones Conocidas:
    1. La memoria se pierde entre handoffs
    2. No hay verdadera coherencia entre agentes
    3. El contexto no se preserva completamente
    
    Flujo de Ejecución:
    1. Inicialización:
       - Crea contexto (que se perderá en handoffs)
       - Configura agentes (sin memoria efectiva)
       - Establece sistema básico de handoff
       
    2. Ciclo Principal:
       - Procesa input del usuario
       - Intenta mantener historial
       - Realiza handoffs (perdiendo contexto)
       
    3. Áreas de Mejora Identificadas:
       - Preservación de memoria entre handoffs
       - Coherencia entre cambios de idioma
       - Sistema de contexto más robusto
    """
    print("\n¡Bienvenido al Chat Interactivo con Memoria!")
    print("Puedes escribir en español o inglés.")
    print("El chat recordará la conversación anterior.")
    print("Escribe 'exit' para salir.\n")
    
    # Crear el contexto compartido
    context = ChatMemoryContext()
    
    # Crear los agentes
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    triage_agent = create_triage_agent(spanish_agent, english_agent)
    
    # Configurar el RunConfig para mantener el contexto
    def handoff_filter(handoff_input_data: HandoffInputData) -> HandoffInputData:
        return HandoffInputData(
            input_history=handoff_input_data.input_history,
            pre_handoff_items=[],  # No necesitamos items anteriores
            new_items=[]  # No necesitamos nuevos items
        )
    
    # Crear los hooks de debugging
    hooks = ChatHooks()
    
    run_config = RunConfig(
        workflow_name="chat_with_memory",
        handoff_input_filter=handoff_filter
    )
    
    while True:
        user_input = input("Tú: ")
        
        if user_input.lower() == 'exit':
            print("\n¡Hasta luego! 👋")
            break
        
        # Agregar el mensaje del usuario al historial
        context.add_message("user", user_input)
        
        # Ejecutar el agente con el contexto y los hooks
        result = await Runner.run(
            triage_agent,
            input=user_input,
            context=context,
            run_config=run_config,
            hooks=hooks
        )
        
        # Agregar la respuesta del asistente al historial
        context.add_message("assistant", result.final_output)
        
        print("\nAsistente:", result.final_output)
        print()

if __name__ == "__main__":
    asyncio.run(chat()) 