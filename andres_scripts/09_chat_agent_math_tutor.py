"""
Chat Agent - Math Tutor con Orquestador y Tracing

Este script implementa un tutor de matemáticas con un flujo de conversación orquestado:
1. Un agente orquestador gestiona la conversación principal
2. Un agente de diagnóstico hace preguntas iniciales específicas
3. El control regresa al orquestador después del diagnóstico

Características:
- Sistema de memoria unificada
- Handoffs bidireccionales entre agentes
- Tracing avanzado para seguir el flujo de conversación
- Debugging extensivo para análisis detallado
- Instrucciones específicas para cada agente

Autor: Andres Montero
Fecha: Marzo 2024
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any
from agents import Agent, Runner, function_tool, RunConfig, HandoffInputData, RunContextWrapper
from agents.tracing import trace, custom_span

# Configuración de debug
DEBUG = True

def debug_print(message: str):
    if DEBUG:
        print(f"[DEBUG] {message}")

@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    session_id: str = field(default_factory=lambda: f"math_session_{uuid.uuid4().hex[:8]}")
    topic: str = ""
    knowledge_level: str = ""
    
    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
        debug_print(f"Mensaje agregado: {role}. Total mensajes: {len(self.history)}")
    
    def get_history(self) -> str:
        debug_print("Obteniendo historial de mensajes")
        return "\n".join(self.history)
    
    def set_topic(self, topic: str):
        self.topic = topic
        debug_print(f"Tema establecido: {topic}")
    
    def set_knowledge_level(self, level: str):
        self.knowledge_level = level
        debug_print(f"Nivel de conocimiento establecido: {level}")

# Función dinámica para instrucciones del orquestador
def dynamic_orchestrator_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    
    # Verificar si el diagnóstico ha terminado (buscando el mensaje de transferencia)
    diagnostic_complete = False
    if "[TRANSFERENCIA_CONTROL]" in history:
        diagnostic_complete = True
        debug_print("[DEBUG] Diagnóstico completado, orquestador retomando control")
    
    return f"""Eres el orquestador principal del tutor de matemáticas.
    
    Tu trabajo es:
    1. Recibir la consulta inicial del usuario
    2. Transferir el control al agente de diagnóstico
    3. Recuperar el control después del diagnóstico
    4. Explicar conceptos matemáticos en base a las respuestas obtenidas por el diagnóstico
    
    IMPORTANTE: Revisa el historial de la conversación antes de responder:
    
    {history}
    
    {'NOTA: El agente diagnóstico ya ha finalizado su trabajo. AHORA debes ayudar al usuario con su problema matemático. NO sigas transfiriendo el control.' if diagnostic_complete else 'Si no has transferido control todavía al agente de diagnóstico, hazlo ahora.'}
    
    {'Ahora, proporciona explicaciones claras y concisas sobre el tema ' + ctx.context.topic if ctx.context.topic else 'Explica conceptos de matemáticas de manera muy básica'}.
    {'Adapta tu explicación al nivel ' + (ctx.context.knowledge_level if ctx.context.knowledge_level else 'principiante') + ' del usuario.'} 
    
    RECUERDA: Ya NO debes responder con mensajes de transferencia. Eso solo lo usa el otro agente.
    """

# Función dinámica para instrucciones del agente de diagnóstico
def dynamic_diagnostic_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    
    # Verificar si ya hizo las dos preguntas
    questions_asked = 0
    if "¿En qué tema ocupas ayuda hoy?" in history:
        questions_asked += 1
    if "¿Qué sabes sobre el tema?" in history:
        questions_asked += 1
        
    # Si ya hizo las dos preguntas, es hora de transferir
    should_transfer = questions_asked >= 2
    
    debug_print(f"[DEBUG] Diagnóstico - preguntas realizadas: {questions_asked}, transferir: {should_transfer}")
    
    return f"""Eres un agente de diagnóstico que SOLO puede hacer dos preguntas específicas:
    
    1. "¿En qué tema ocupas ayuda hoy?"
    2. "¿Qué sabes sobre el tema?"
    
    IMPORTANTE: Revisa el historial de la conversación antes de responder:
    
    {history}
    
    No puedes:
    - Enseñar nada
    - Hacer otras preguntas
    - Dar explicaciones
    
    {"INSTRUCCIÓN ESPECIAL: Ya has hecho las dos preguntas necesarias. Ahora DEBES transferir el control al orquestador enviando EXACTAMENTE este mensaje: [TRANSFERENCIA_CONTROL]" if should_transfer else "Debes hacer las preguntas en orden, esperando la respuesta del usuario entre cada una."}
    """

def create_orchestrator_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Orchestrator",
        model="gpt-4-turbo-preview",
        instructions=dynamic_orchestrator_instructions
    )

def create_diagnostic_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="DiagnosticAgent",
        model="gpt-4-turbo-preview",
        instructions=dynamic_diagnostic_instructions
    )

# Función para preservar el contexto durante los handoffs
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    debug_print(f"Ejecutando handoff filter. Mensajes: {len(input_data.input_history)}")
    # Pasamos todos los datos sin modificar
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )

# Análisis de mensajes para extraer información
async def analyze_conversation(context: ChatMemoryContext, result: str) -> None:
    with custom_span("analyze_conversation", data={"session_id": context.session_id}):
        # Extraer tema de matemáticas si no está establecido
        if not context.topic and "ayuda" in result.lower() and "?" in result:
            history = context.get_history()
            if "tema" in history.lower() and "?" in history:
                for line in context.history:
                    if line.startswith("Usuario:") and "tema" in history.lower():
                        potential_topic = line.split("Usuario:")[1].strip()
                        if len(potential_topic) > 3:  # Texto significativo
                            context.set_topic(potential_topic)
                            debug_print(f"Tema extraído: {potential_topic}")
        
        # Extraer nivel de conocimiento si no está establecido
        if not context.knowledge_level and "sabes" in result.lower() and "?" in result:
            history = context.get_history()
            if "sabes" in history.lower() and "?" in history:
                for line in context.history:
                    if line.startswith("Usuario:") and "sabes" in history.lower():
                        potential_level = line.split("Usuario:")[1].strip()
                        if "nada" in potential_level.lower():
                            context.set_knowledge_level("principiante")
                        elif "poco" in potential_level.lower():
                            context.set_knowledge_level("intermedio")
                        elif "mucho" in potential_level.lower() or "bastante" in potential_level.lower():
                            context.set_knowledge_level("avanzado")
                        else:
                            context.set_knowledge_level("intermedio")

# Función para identificar qué agente está respondiendo
def identify_agent(response: str) -> str:
    """Identifica qué agente está respondiendo basado en el contenido del mensaje."""
    
    # Detectar agente diagnóstico
    if "[TRANSFERENCIA_CONTROL]" in response:
        return "DiagnosticAgent"
    elif "¿En qué tema ocupas ayuda hoy?" in response or "¿Qué sabes sobre el tema?" in response:
        return "DiagnosticAgent"
    
    # Por defecto es el orquestador
    return "Orchestrator"

# Función para procesar la respuesta antes de mostrarla al usuario
def process_response_for_display(response: str, agent_type: str) -> str:
    """Procesa la respuesta para que sea amigable para el usuario."""
    # Reemplazar el mensaje de transferencia con algo más natural
    if agent_type == "DiagnosticAgent" and "[TRANSFERENCIA_CONTROL]" in response:
        return "He completado el diagnóstico inicial. Ahora mi colega te ayudará con la explicación."
    
    return response

async def chat():
    print("¡Bienvenido al Tutor de Matemáticas!")
    print("Puedes escribir 'exit' para salir en cualquier momento.")
    
    # Crear el contexto compartido
    context = ChatMemoryContext()
    debug_print(f"Sesión iniciada con ID: {context.session_id}")
    
    # Crear los agentes
    orchestrator = create_orchestrator_agent()
    diagnostic = create_diagnostic_agent()
    
    # Configurar los handoffs
    orchestrator.handoffs = [diagnostic]
    diagnostic.handoffs = [orchestrator]
    
    # Variable para rastrear la transferencia de control
    transfer_occurred = False
    
    # Configurar el Runner para preservar el contexto y habilitar tracing
    run_config = RunConfig(
        handoff_input_filter=memory_handoff_filter,
        workflow_name="Math Tutor Session",
        group_id=context.session_id,
        trace_metadata={
            "session_type": "math_tutoring",
            "user_id": f"user_{uuid.uuid4().hex[:6]}"
        }
    )
    
    # Iniciar traza de sesión completa
    with trace(f"Math Tutoring - {context.session_id}", metadata={"session_id": context.session_id}):
        while True:
            user_input = input("\nTú: ")
            
            if user_input.lower() == 'exit':
                print("¡Hasta luego!")
                break
                
            # Iniciar span para este turno de conversación
            with custom_span("conversation_turn", data={"input_length": len(user_input)}):
                debug_print(f"\n[DEBUG] Input del usuario: {user_input}")
                
                # Agregar el mensaje del usuario al historial
                context.add_message("Usuario", user_input)
                
                # Ejecutar el orquestador
                debug_print("[DEBUG] Ejecutando orquestador...")
                result = await Runner.run(
                    orchestrator,
                    input=user_input,
                    context=context,
                    run_config=run_config
                )
                
                # Identificar qué agente está respondiendo
                current_agent = identify_agent(result.final_output)
                debug_print(f"[DEBUG] Agente activo identificado: {current_agent}")
                
                # Verificar si ocurrió una transferencia
                if current_agent == "DiagnosticAgent" and "[TRANSFERENCIA_CONTROL]" in result.final_output:
                    transfer_occurred = True
                    debug_print("[DEBUG] ¡Transferencia de control detectada!")
                
                # Procesar la respuesta para mostrarla al usuario
                display_response = process_response_for_display(result.final_output, current_agent)
                debug_print(f"[DEBUG] Resultado original: {result.final_output}")
                debug_print(f"[DEBUG] Resultado procesado para mostrar: {display_response}")
                
                # Analizar la conversación para extraer información
                await analyze_conversation(context, result.final_output)
                
                # Agregar la respuesta al historial - usamos la respuesta original para el contexto
                context.add_message("Asistente", result.final_output)
                
                # Mostrar información de diagnóstico en el debug
                if context.topic:
                    debug_print(f"[DEBUG] Tema actual: {context.topic}")
                if context.knowledge_level:
                    debug_print(f"[DEBUG] Nivel de conocimiento: {context.knowledge_level}")
                
                # Mostrar el mensaje con el nombre del agente
                agent_display_name = "Diagnóstico" if current_agent == "DiagnosticAgent" else "Orquestador"
                print(f"\nAsistente [{agent_display_name}]: {display_response}")
                
                # Si ocurrió una transferencia, hacer un turno extra para que el orquestador responda
                if transfer_occurred:
                    transfer_occurred = False  # Resetear la bandera
                    debug_print("[DEBUG] Ejecutando turno extra del orquestador después de transferencia...")
                    
                    # Ejecutar el orquestador de nuevo
                    extra_result = await Runner.run(
                        orchestrator,
                        input="Por favor, explica el tema basado en la información recopilada.",
                        context=context,
                        run_config=run_config
                    )
                    
                    # Siempre será el orquestador respondiendo aquí
                    debug_print(f"[DEBUG] Resultado orquestador post-transferencia: {extra_result.final_output}")
                    
                    # Agregar la respuesta al historial
                    context.add_message("Asistente", extra_result.final_output)
                    
                    # Mostrar la respuesta
                    print(f"\nAsistente [Orquestador]: {extra_result.final_output}")

if __name__ == "__main__":
    asyncio.run(chat()) 