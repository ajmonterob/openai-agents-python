"""
⚠️ IMPORTANTE: Este script necesita correcciones y no está funcionando correctamente.
Problemas conocidos:
1. La memoria no se mantiene correctamente entre agentes
2. La detección de idioma no es precisa
3. Los handoffs no preservan el contexto adecuadamente

Este script es un intento de implementar memoria segregada por agente, pero requiere
una revisión y reestructuración completa para funcionar como se espera.

Autor: Andres Montero
Fecha: Marzo 2024
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
import asyncio
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig, HandoffInputData, RunContextWrapper, RunHooks, Tool, ModelSettings


@dataclass
class AgentMemoryContext:
    """
    Contexto de memoria para un agente específico.
    Mantiene el historial de conversación para un solo idioma.
    """
    conversation_history: List[dict] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({
            "role": role,
            "content": content
        })
        print(f"[debug] Agregando mensaje al historial del agente: {role}: {content}")
        print(f"[debug] Total de mensajes en el historial: {len(self.conversation_history)}")
    
    def get_history_as_string(self) -> str:
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
    print(f"[debug] Consultando el clima para la ciudad: {city}")
    return Weather(
        city=city,
        temperature_range="14-20C",
        conditions="Sunny with wind."
    )

# Herramienta para cálculos matemáticos
@function_tool
def calculate(operation: str) -> CalculatorResult:
    print(f"[debug] Realizando cálculo: {operation}")
    try:
        result = eval(operation)
        print(f"[debug] Resultado del cálculo: {result}")
        return CalculatorResult(operation=operation, result=result)
    except Exception as e:
        print(f"[debug] Error en el cálculo: {str(e)}")
        return CalculatorResult(operation=operation, result=float('nan'))

def create_spanish_agent():
    return Agent[AgentMemoryContext](
        name="Spanish Assistant",
        instructions="""Eres un asistente amigable que habla español.
        Debes responder SIEMPRE en español.
        
        IMPORTANTE: Tienes acceso al historial de conversación en español.
        DEBES revisar el historial antes de responder para mantener coherencia.
        
        Para cada mensaje en el historial:
        - El formato es "role: content"
        - El role puede ser "user" o "assistant"
        
        ANTES de responder:
        1. Lee el historial de la conversación usando context.get_history_as_string()
        2. Busca información relevante como nombres, datos o contexto previo
        3. Asegúrate de que tu respuesta sea coherente con toda la conversación anterior
        4. Si te preguntan por algo mencionado antes, DEBES buscarlo en el historial
        
        Puedes:
        - Dar información sobre el clima usando la herramienta get_weather
        - Hacer cálculos matemáticos usando la herramienta calculate
        - Mantener conversaciones amigables
        - Ayudar con preguntas generales
        - Recordar información mencionada anteriormente en la conversación""",
        tools=[get_weather, calculate]
    )

def create_english_agent():
    return Agent[AgentMemoryContext](
        name="English Assistant",
        instructions="""You are a friendly assistant that speaks English.
        You must ALWAYS respond in English.
        
        IMPORTANT: You have access to the English conversation history.
        You MUST review the history before responding to maintain coherence.
        
        For each message in the history:
        - The format is "role: content"
        - The role can be "user" or "assistant"
        
        BEFORE responding:
        1. Read the conversation history using context.get_history_as_string()
        2. Look for relevant information like names, data, or previous context
        3. Ensure your response is coherent with all previous conversation
        4. If asked about something mentioned before, you MUST look it up in the history
        
        You can:
        - Provide weather information using the get_weather tool
        - Perform mathematical calculations using the calculate tool
        - Engage in friendly conversations
        - Help with general questions
        - Remember information mentioned earlier in the conversation""",
        tools=[get_weather, calculate]
    )

def create_triage_agent(spanish_agent: Agent[AgentMemoryContext], english_agent: Agent[AgentMemoryContext]) -> Agent[AgentMemoryContext]:
    return Agent[AgentMemoryContext](
        name="Triage Assistant",
        instructions="""Eres un agente de triaje que detecta el idioma del usuario.
        Si detectas español, transfiere la conversación al Asistente Español.
        Si detectas inglés, transfiere la conversación al English Assistant.
        Si detectas ambos idiomas, prioriza el español.
        No respondas directamente, solo transfiere la conversación.""",
        handoffs=[spanish_agent, english_agent]
    )

# Hooks para debugging
class ChatHooks(RunHooks[AgentMemoryContext]):
    """
    Sistema de hooks para debugging y monitoreo.
    Monitorea el estado de memoria y el flujo de la conversación.
    """
    async def on_agent_start(self, context: RunContextWrapper[AgentMemoryContext], agent: Agent[AgentMemoryContext]) -> None:
        print(f"\n[debug] Iniciando agente: {agent.name}")
        if context.context:
            print(f"[debug] Historial actual ({len(context.context.conversation_history)} mensajes):")
            print(context.context.get_history_as_string())

    async def on_agent_end(self, context: RunContextWrapper[AgentMemoryContext], agent: Agent[AgentMemoryContext], output: str) -> None:
        print(f"\n[debug] Agente {agent.name} completó su tarea")
        print(f"[debug] Respuesta generada: {output}")

    async def on_handoff(self, context: RunContextWrapper[AgentMemoryContext], from_agent: Agent[AgentMemoryContext], to_agent: Agent[AgentMemoryContext]) -> None:
        print(f"\n[debug] Transferencia de control: {from_agent.name} -> {to_agent.name}")
        if context.context:
            print(f"[debug] Historial actual ({len(context.context.conversation_history)} mensajes):")
            print(context.context.get_history_as_string())

    async def on_tool_start(self, context: RunContextWrapper[AgentMemoryContext], agent: Agent[AgentMemoryContext], tool: Tool) -> None:
        print(f"\n[debug] Agente {agent.name} está usando la herramienta: {tool.name}")

    async def on_tool_end(self, context: RunContextWrapper[AgentMemoryContext], agent: Agent[AgentMemoryContext], tool: Tool, result: str) -> None:
        print(f"\n[debug] Herramienta {tool.name} completada por {agent.name}")
        print(f"[debug] Resultado obtenido: {result}")

# Función para preservar el contexto durante los handoffs
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )

async def chat():
    """
    Función principal del chat con memoria segregada por idioma.
    """
    # Crear los agentes
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    triage_agent = create_triage_agent(spanish_agent, english_agent)
    
    # Crear contextos específicos para cada agente
    spanish_context = AgentMemoryContext()
    english_context = AgentMemoryContext()
    
    # Configurar RunConfig
    run_config = RunConfig(
        model="gpt-4-turbo-preview",
        model_settings=ModelSettings(temperature=0.7)
    )
    
    print("¡Bienvenido! Puedes escribir en español o inglés. Escribe 'exit' para salir.")
    
    while True:
        user_input = input("> ")
        if user_input.lower() == 'exit':
            break
            
        # Determinar el idioma y usar el contexto correspondiente
        is_spanish = any(c in user_input.lower() for c in ['á', 'é', 'í', 'ó', 'ú', 'ñ', '¿', '¡']) or \
                    any(word in user_input.lower() for word in ['hola', 'como', 'estas', 'que', 'cual', 'donde', 'cuando', 'por', 'para'])
        
        if is_spanish:
            context = spanish_context
            agent = spanish_agent
            print("[debug] Usando agente en español")
        else:
            context = english_context
            agent = english_agent
            print("[debug] Usando agente en inglés")
            
        # Agregar el mensaje del usuario al contexto correspondiente
        context.add_message("user", user_input)
            
        # Ejecutar el agente con su contexto específico
        result = await Runner.run(
            agent,
            input=user_input,
            context=context,
            run_config=run_config
        )
        
        # Extraer solo el texto de la respuesta
        response_text = result.final_output if hasattr(result, 'final_output') else str(result)
        
        # Agregar la respuesta al contexto
        context.add_message("assistant", response_text)
        
        # Mostrar la respuesta
        print(response_text)
        
        # Mostrar el historial actual del agente
        print(f"\n[debug] Historial del agente ({len(context.conversation_history)} mensajes):")
        print(context.get_history_as_string())

if __name__ == "__main__":
    asyncio.run(chat()) 