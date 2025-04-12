"""
Chat Agent - Math Tutor con Orquestador y Tracing

Este script implementa un tutor de matemáticas con un flujo de conversación orquestado:
1. Un agente orquestador gestiona la conversación principal
2. Un agente de diagnóstico hace preguntas iniciales específicas
3. Un agente calibrador genera expresiones matemáticas
4. El control regresa al orquestador después de la calibración

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
    math_expressions: List[str] = field(default_factory=list)
    user_feedback: Dict[str, str] = field(default_factory=dict)
    current_flow_state: str = "initial"  # initial -> diagnostic -> calibration -> final
    
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
        
    def set_math_expressions(self, expressions: List[str]):
        self.math_expressions = expressions
        debug_print(f"Expresiones matemáticas establecidas: {expressions}")
        
    def add_user_feedback(self, expression: str, feedback: str):
        self.user_feedback[expression] = feedback
        debug_print(f"Feedback agregado para {expression}: {feedback}")
    
    def advance_flow(self):
        if self.current_flow_state == "initial":
            self.current_flow_state = "diagnostic"
            debug_print("Flujo avanzado a: diagnostic")
        elif self.current_flow_state == "diagnostic":
            self.current_flow_state = "calibration"
            debug_print("Flujo avanzado a: calibration")
        elif self.current_flow_state == "calibration":
            self.current_flow_state = "final"
            debug_print("Flujo avanzado a: final")

# Función dinámica para instrucciones del orquestador
def dynamic_orchestrator_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    flow_state = ctx.context.current_flow_state
    
    if flow_state == "initial":
        return f"""Eres el orquestador principal del tutor de matemáticas.
        
        Tu trabajo es iniciar el flujo y transferir el control al agente de diagnóstico.
        
        IMPORTANTE: En tu primera respuesta, DEBES decir EXACTAMENTE:
        "Hola, soy tu tutor de matemáticas. Te pasaré con mi compañero de diagnóstico."
        
        No añadas nada más, esto es crucial para el flujo correcto.
        """
    elif flow_state == "diagnostic":
        return f"""Eres el orquestador principal del tutor de matemáticas.
        
        Acabas de recibir el control del agente de diagnóstico. Ahora debes transferir
        el control al agente calibrador para evaluar el nivel del estudiante.
        
        IMPORTANTE: En tu respuesta, DEBES decir EXACTAMENTE:
        "Gracias por esa información. Ahora mi compañero te presentará algunas expresiones matemáticas para evaluar tu nivel."
        
        No añadas nada más, esto es crucial para el flujo correcto.
        """
    elif flow_state == "calibration":
        return f"""Eres el orquestador principal del tutor de matemáticas.
        
        Has recibido el control después de la fase de calibración. Ahora debes proporcionar
        una explicación completa sobre el tema matemático.
        
        Historial de la conversación:
        {history}
        
        Tema: {ctx.context.topic if ctx.context.topic else "matemáticas básicas"}
        Nivel: {ctx.context.knowledge_level if ctx.context.knowledge_level else "principiante"}
        
        Basado en las expresiones matemáticas y el feedback del usuario, proporciona una
        explicación detallada y adaptada al nivel del usuario.
        """
    else:
        return f"""Eres el orquestador principal del tutor de matemáticas.
        
        Continúa proporcionando ayuda sobre el tema: {ctx.context.topic if ctx.context.topic else "matemáticas básicas"}
        
        Historial de la conversación:
        {history}
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
    
    if should_transfer:
        # Forzar una respuesta de transferencia
        return """Eres un agente de diagnóstico.
        
        Has completado tus preguntas. Ahora DEBES responder EXACTAMENTE con el siguiente mensaje:
        
        [TRANSFERENCIA_CONTROL]
        
        No agregues NADA más.
        """
    else:
        return f"""Eres un agente de diagnóstico que SOLO puede hacer dos preguntas específicas:
        
        1. "¿En qué tema ocupas ayuda hoy?"
        2. "¿Qué sabes sobre el tema?"
        
        IMPORTANTE: Revisa el historial de la conversación antes de responder:
        
        {history}
        
        No puedes:
        - Enseñar nada
        - Hacer otras preguntas
        - Dar explicaciones
        
        Debes hacer las preguntas en orden, esperando la respuesta del usuario entre cada una.
        """

# Función dinámica para instrucciones del agente calibrador
def dynamic_calibrator_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    
    # Verificar si ya generó las expresiones
    expressions_generated = len(ctx.context.math_expressions) > 0
    
    # Verificar si ya recibió feedback
    feedback_received = len(ctx.context.user_feedback) > 0
    
    # Si no hay tema, usar un tema genérico
    tema = ctx.context.topic if ctx.context.topic else "matemáticas básicas"
    
    if feedback_received:
        # Forzar transferencia cuando ya hay feedback
        return """Eres un agente calibrador.
        
        Has recibido feedback sobre tus expresiones matemáticas. Ahora DEBES responder EXACTAMENTE con el siguiente mensaje:
        
        [TRANSFERENCIA_CONTROL]
        
        No agregues NADA más.
        """
    else:
        return f"""Eres un agente calibrador que SOLO puede:
        1. Generar 4 expresiones matemáticas relacionadas con el tema {tema}
        2. Esperar la respuesta del usuario indicando cuáles le parecen fáciles y cuáles difíciles
        3. Transferir el control al orquestador
        
        IMPORTANTE: Revisa el historial de la conversación antes de responder:
        
        {history}
        
        {f"Ya has generado las expresiones: {', '.join(ctx.context.math_expressions)}" if expressions_generated else "Debes generar 4 expresiones matemáticas relacionadas con el tema."}
        
        Espera la respuesta del usuario sobre qué expresiones le parecen fáciles y cuáles difíciles.
        
        No puedes:
        - Enseñar nada
        - Hacer otras preguntas
        - Dar explicaciones
        - Generar más de 4 expresiones
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

def create_calibrator_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="CalibratorAgent",
        model="gpt-4-turbo-preview",
        instructions=dynamic_calibrator_instructions
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
        # Extraer tema de matemáticas
        if not context.topic and "tema" in result.lower() and "?" in result:
            history = context.get_history()
            for line in context.history:
                if line.startswith("Usuario:") and len(context.history) >= 3:  # Al menos una interacción completa
                    potential_topic = line.split("Usuario:")[1].strip()
                    if (len(potential_topic) > 3 and 
                        "hola" not in potential_topic.lower() and 
                        "nombre" not in potential_topic.lower()):
                        context.set_topic(potential_topic)
                        debug_print(f"Tema extraído: {potential_topic}")
        
        # Extraer nivel de conocimiento
        if not context.knowledge_level and "sabes" in result.lower() and "?" in result:
            history = context.get_history()
            for line in context.history:
                if line.startswith("Usuario:") and "sabes" in history.lower():
                    potential_level = line.split("Usuario:")[1].strip().lower()
                    if "nada" in potential_level:
                        context.set_knowledge_level("principiante")
                    elif "poco" in potential_level:
                        context.set_knowledge_level("intermedio")
                    elif "mucho" in potential_level or "bastante" in potential_level:
                        context.set_knowledge_level("avanzado")
                    else:
                        context.set_knowledge_level("intermedio")
                            
        # Extraer expresiones matemáticas
        if not context.math_expressions and "expresión" in result.lower():
            expressions = []
            for line in result.split('\n'):
                if any(char in line for char in ['+', '-', '*', '/', '=', '^']):
                    expressions.append(line.strip())
            if len(expressions) >= 4:
                context.set_math_expressions(expressions[:4])
                
        # Extraer feedback del usuario
        if context.math_expressions and not context.user_feedback:
            for line in context.history:
                if line.startswith("Usuario:"):
                    user_response = line.split("Usuario:")[1].strip().lower()
                    for expr in context.math_expressions:
                        if expr.lower() in user_response:
                            if "fácil" in user_response or "sencillo" in user_response:
                                context.add_user_feedback(expr, "fácil")
                            elif "difícil" in user_response or "complejo" in user_response:
                                context.add_user_feedback(expr, "difícil")
                    
        # Detectar cambios de estado del flujo
        if "[TRANSFERENCIA_CONTROL]" in result:
            if context.current_flow_state == "diagnostic":
                context.advance_flow()  # diagnostic -> calibration
            elif context.current_flow_state == "calibration":
                context.advance_flow()  # calibration -> final

# Función para procesar la respuesta antes de mostrarla al usuario
def process_response_for_display(response: str) -> str:
    """Procesa la respuesta para que sea amigable para el usuario."""
    # Reemplazar el mensaje de transferencia con algo más natural
    if "[TRANSFERENCIA_CONTROL]" in response:
        return "He completado mi parte. Ahora pasaré el control a mi colega."
    
    return response

# Función auxiliar para mostrar mensajes de agente con formato correcto
def display_agent_message(agent_name: str, message: str):
    """Muestra un mensaje del agente con el formato correcto."""
    print(f"\nAsistente [{agent_name}]: {message}")
    debug_print(f"[DEBUG] Mostrando mensaje de {agent_name}")

async def chat():
    print("¡Bienvenido al Tutor de Matemáticas!")
    print("Puedes escribir 'exit' para salir en cualquier momento.")
    
    # Crear el contexto compartido
    context = ChatMemoryContext()
    debug_print(f"Sesión iniciada con ID: {context.session_id}")
    
    # Crear los agentes
    orchestrator = create_orchestrator_agent()
    diagnostic = create_diagnostic_agent()
    calibrator = create_calibrator_agent()
    
    # Configurar los handoffs en el orden correcto
    orchestrator.handoffs = [diagnostic, calibrator]  # Orquestador puede transferir a ambos
    diagnostic.handoffs = [orchestrator]  # Diagnóstico regresa al orquestador
    calibrator.handoffs = [orchestrator]  # Calibrador regresa al orquestador
    
    # Configurar el Runner
    run_config = RunConfig(
        handoff_input_filter=memory_handoff_filter,
        workflow_name="Math Tutor Session",
        group_id=context.session_id,
        trace_metadata={
            "session_type": "math_tutoring",
            "user_id": f"user_{uuid.uuid4().hex[:6]}"
        }
    )
    
    # Iniciar la sesión
    with trace(f"Math Tutoring - {context.session_id}", metadata={"session_id": context.session_id}):
        # Primera interacción - comienza con el diagnóstico directamente
        result = await Runner.run(
            diagnostic,
            input="Hola, quiero aprender matemáticas",
            context=context,
            run_config=run_config
        )
        
        # Procesar y mostrar el primer mensaje
        response_text = process_response_for_display(result.final_output)
        context.add_message("Asistente", result.final_output)
        display_agent_message("Diagnóstico", response_text)
        context.current_flow_state = "diagnostic"
        
        # Bucle principal de chat
        while True:
            user_input = input("\nTú: ")
            
            if user_input.lower() == 'exit':
                print("¡Hasta luego!")
                break
                
            # Registrar input del usuario
            debug_print(f"\n[DEBUG] Input del usuario: {user_input}")
            context.add_message("Usuario", user_input)
            
            # Analizar el input para extraer feedback sobre expresiones si estamos en el estado de calibración
            if context.current_flow_state == "calibration" and context.math_expressions and not context.user_feedback:
                # Verificar si el input contiene feedback sobre expresiones
                has_feedback = False
                for expr in context.math_expressions:
                    if expr.lower() in user_input.lower():
                        if "fácil" in user_input.lower() or "sencillo" in user_input.lower():
                            context.add_user_feedback(expr, "fácil")
                            has_feedback = True
                        elif "difícil" in user_input.lower() or "complejo" in user_input.lower():
                            context.add_user_feedback(expr, "difícil")
                            has_feedback = True
                
                # Si se detectó feedback y tenemos al menos una expresión con feedback, forzar la transferencia
                if has_feedback and len(context.user_feedback) > 0:
                    debug_print("[DEBUG] Feedback detectado, forzando transferencia al orquestador")
                    
                    # Ejecutar el calibrador para generar una respuesta de transferencia
                    extra_result = await Runner.run(
                        calibrator,
                        input="He recibido feedback sobre las expresiones",
                        context=context,
                        run_config=run_config
                    )
                    
                    response_text = extra_result.final_output
                    
                    # Debe contener [TRANSFERENCIA_CONTROL] debido a las instrucciones
                    if "[TRANSFERENCIA_CONTROL]" in response_text:
                        # Cambiar al orquestador final
                        context.current_flow_state = "final"
                        debug_print("[DEBUG] Avanzando flujo a: final")
                        
                        # Procesar mensaje de transferencia
                        display_text = process_response_for_display(response_text)
                        context.add_message("Asistente", response_text)
                        display_agent_message("Calibrador", display_text)
                        
                        # Ejecutar turno extra del orquestador
                        extra_input = "Dame una explicación sobre el tema"
                        extra_final_result = await Runner.run(
                            orchestrator,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del orquestador
                        extra_response = extra_final_result.final_output
                        debug_print(f"[DEBUG] Respuesta del orquestador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        display_agent_message("Orquestador", extra_response)
                        continue  # Saltar al siguiente turno de usuario
            
            # Determinar qué agente usar basado en el estado actual
            if context.current_flow_state == "diagnostic":
                current_agent = diagnostic
                agent_name = "Diagnóstico"
            elif context.current_flow_state == "calibration":
                current_agent = calibrator
                agent_name = "Calibrador"
            else:
                current_agent = orchestrator
                agent_name = "Orquestador"
            
            debug_print(f"[DEBUG] Estado actual: {context.current_flow_state}, Agente: {agent_name}")
            
            # Ejecutar el agente correspondiente
            with custom_span("conversation_turn", data={"agent": current_agent.name}):
                result = await Runner.run(
                    current_agent,
                    input=user_input,
                    context=context,
                    run_config=run_config
                )
                
                # Procesar respuesta y detectar transferencias
                response_text = result.final_output
                debug_print(f"[DEBUG] Respuesta original: {response_text}")
                
                # Verificar si el diagnóstico debe transferir después de la segunda respuesta
                if context.current_flow_state == "diagnostic":
                    questions_asked = 0
                    if "¿En qué tema ocupas ayuda hoy?" in context.get_history():
                        questions_asked += 1
                    if "¿Qué sabes sobre el tema?" in context.get_history():
                        questions_asked += 1
                        
                    # Verificar si ya respondió 2 preguntas y debe transferir
                    if questions_asked >= 2 and "?" not in response_text:
                        debug_print("[DEBUG] Diagnóstico completado, forzando transferencia al calibrador")
                        
                        # Forzar transferencia al calibrador
                        context.current_flow_state = "calibration"
                        debug_print("[DEBUG] Avanzando flujo a: calibration")
                        
                        # Agregar mensaje de despedida del diagnóstico
                        if "[TRANSFERENCIA_CONTROL]" not in response_text:
                            display_text = "He completado mi diagnóstico. Ahora mi colega te presentará algunas expresiones matemáticas."
                        else:
                            display_text = process_response_for_display(response_text)
                        
                        context.add_message("Asistente", display_text)
                        display_agent_message("Diagnóstico", display_text)
                        
                        # Ejecutar turno extra del calibrador inmediatamente
                        extra_input = "Necesito expresiones matemáticas para evaluar"
                        extra_result = await Runner.run(
                            calibrator,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del calibrador
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del calibrador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        display_agent_message("Calibrador", extra_response)
                        
                        # Analizar para extraer expresiones
                        await analyze_conversation(context, extra_response)
                        continue  # Saltar al siguiente turno de usuario
                
                # Detectar transferencia explícita
                if "[TRANSFERENCIA_CONTROL]" in response_text:
                    debug_print(f"[DEBUG] Transferencia explícita detectada desde {agent_name}")
                    
                    if context.current_flow_state == "diagnostic":
                        # Cambiar al calibrador después del diagnóstico
                        context.current_flow_state = "calibration"
                        debug_print("[DEBUG] Avanzando flujo a: calibration")
                        
                        # Procesar mensaje de transferencia
                        display_text = process_response_for_display(response_text)
                        context.add_message("Asistente", display_text)
                        display_agent_message("Diagnóstico", display_text)
                        
                        # Ejecutar turno extra del calibrador
                        extra_input = "Necesito expresiones matemáticas para evaluar"
                        extra_result = await Runner.run(
                            calibrator,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del calibrador
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del calibrador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        display_agent_message("Calibrador", extra_response)
                        
                        # Analizar para extraer expresiones
                        await analyze_conversation(context, extra_response)
                        continue  # Saltar al siguiente turno de usuario
                        
                    elif context.current_flow_state == "calibration":
                        # Cambiar al orquestador final
                        context.current_flow_state = "final"
                        debug_print("[DEBUG] Avanzando flujo a: final")
                        
                        # Procesar mensaje de transferencia
                        display_text = process_response_for_display(response_text)
                        context.add_message("Asistente", display_text)
                        display_agent_message("Calibrador", display_text)
                        
                        # Ejecutar turno extra del orquestador
                        extra_input = "Dame una explicación sobre el tema"
                        extra_result = await Runner.run(
                            orchestrator,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del orquestador
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del orquestador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        display_agent_message("Orquestador", extra_response)
                        continue  # Saltar al siguiente turno de usuario
                
                # Si no hay transferencia, procesar normalmente
                display_text = process_response_for_display(response_text)
                context.add_message("Asistente", response_text)
                display_agent_message(agent_name, display_text)
                
                # Analizar la conversación
                await analyze_conversation(context, response_text)

if __name__ == "__main__":
    asyncio.run(chat()) 