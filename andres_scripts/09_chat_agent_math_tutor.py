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
from typing import List, Dict, Any, Tuple
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
    scaffold_exercise: str = ""
    scaffold_solution: str = ""
    scaffold_understood: bool = False
    current_flow_state: str = "initial"  # initial -> diagnostic -> calibration -> scaffolding -> final
    
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
            self.current_flow_state = "scaffolding"
            debug_print("Flujo avanzado a: scaffolding")
        elif self.current_flow_state == "scaffolding":
            self.current_flow_state = "final"
            debug_print("Flujo avanzado a: final")
    
    def set_scaffold_exercise(self, exercise: str, solution: str):
        """Establece el ejercicio y solución generados por el agente de andamiaje."""
        self.scaffold_exercise = exercise
        self.scaffold_solution = solution
        debug_print(f"Ejercicio de andamiaje establecido: {exercise}")
        debug_print(f"Solución de andamiaje establecida: {solution}")

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
        feedback_str = ", ".join([f"{expr}: {fb}" for expr, fb in ctx.context.user_feedback.items()])
        debug_print(f"[DEBUG-CALIBRADOR] Feedback detectado: {feedback_str}. Forzando transferencia al andamiaje.")
        
        return """Eres un agente calibrador.
        
        Has recibido feedback sobre tus expresiones matemáticas. 
        
        INSTRUCCIÓN CRÍTICA: DEBES transferir el control al agente de andamiaje inmediatamente.
        NO debes proponer ningún ejercicio.
        NO debes dar ninguna explicación.
        NO debes hacer ningún comentario.
        NO debes generar ningún contenido adicional.
        
        Tu próxima respuesta DEBE consistir ÚNICAMENTE en el siguiente texto exacto:
        
        [TRANSFERENCIA_CONTROL]
        
        NADA MÁS. Si agregas cualquier otro texto, causarás un error en el sistema.
        """
    else:
        return f"""Eres un agente calibrador que SOLO puede:
        1. Generar 4 expresiones matemáticas relacionadas con el tema {tema}
        2. Esperar la respuesta del usuario indicando cuáles le parecen fáciles y cuáles difíciles
        3. Transferir el control al agente de andamiaje
        
        IMPORTANTE: Tu ÚNICO trabajo es calibrar el nivel del estudiante mediante expresiones.
        NO debes proponer ejercicios.
        NO debes resolver problemas.
        NO debes dar explicaciones sobre los temas.
        
        Revisa el historial de la conversación antes de responder:
        
        {history}
        
        {f"Ya has generado las expresiones: {', '.join(ctx.context.math_expressions)}" if expressions_generated else "Debes generar 4 expresiones matemáticas relacionadas con el tema."}
        
        Espera la respuesta del usuario sobre qué expresiones le parecen fáciles y cuáles difíciles.
        Cuando el usuario dé feedback, responde ÚNICAMENTE con [TRANSFERENCIA_CONTROL].
        """

# Función dinámica para instrucciones del agente de andamiaje
def dynamic_scaffolding_instructions(ctx: RunContextWrapper[ChatMemoryContext], agent: Agent) -> str:
    history = ctx.context.get_history()
    
    # Verificar si ya generó un ejercicio
    exercise_generated = ctx.context.scaffold_exercise != ""
    
    # Verificar si el alumno ha confirmado entendimiento
    understanding_confirmed = ctx.context.scaffold_understood
    
    # Obtener información sobre el tema y nivel
    tema = ctx.context.topic if ctx.context.topic else "matemáticas básicas"
    nivel = ctx.context.knowledge_level if ctx.context.knowledge_level else "principiante"
    
    # Obtener información sobre las expresiones y feedback
    expresiones = ctx.context.math_expressions
    feedback = ctx.context.user_feedback
    
    # Determinar qué expresiones se consideraron difíciles y fáciles
    difficult_expressions = [expr for expr, level in feedback.items() if level == "difícil"]
    easy_expressions = [expr for expr, level in feedback.items() if level == "fácil"]
    
    if understanding_confirmed:
        # Si el alumno ya entendió, transferir el control
        return """Eres un agente de andamiaje.
        
        El alumno ha confirmado que entiende el ejercicio. Ahora DEBES responder EXACTAMENTE con el siguiente mensaje:
        
        [TRANSFERENCIA_CONTROL]
        
        No agregues NADA más.
        """
    elif exercise_generated:
        # Ya generó el ejercicio, ahora debe guiar al alumno MOSTRANDO la solución paso a paso
        return f"""Eres un agente de andamiaje que enseña {tema}.

        Has presentado el siguiente ejercicio al alumno:
        {ctx.context.scaffold_exercise}
        
        IMPORTANTE: TU trabajo es MOSTRAR la solución paso a paso, NO pedir al alumno que lo resuelva.
        
        Debes:
        1. Explicar cómo resolver el ejercicio dividiendo la solución en pasos claros y sencillos
        2. Mostrar cada paso de la resolución con explicaciones detalladas
        3. Usar un lenguaje adaptado al nivel {nivel} del estudiante
        4. Verificar la comprensión del alumno al final
        
        NO pidas al alumno que resuelva el problema.
        NO esperes a que el alumno te dé una respuesta antes de continuar.
        SÍ explica todos los pasos de la solución de manera clara y detallada.
        
        Si el alumno indica explícitamente que ha entendido con frases como "entendí", "comprendo", "tiene sentido", etc.,
        debes responder confirmando y luego transferir el control.
        
        Historial de la conversación:
        {history}
        """
    else:
        # Aún no ha generado un ejercicio, debe crearlo siguiendo el concepto de ZDP
        return f"""Eres un agente de andamiaje especializado en matemáticas que utiliza el concepto de Zona de Desarrollo Próximo (ZDP).
        
        PRIMERO, analiza cuidadosamente la siguiente información recolectada sobre el estudiante:
        - Tema: {tema}
        - Nivel declarado: {nivel}
        - Expresiones que el alumno considera fáciles: {easy_expressions if easy_expressions else "Ninguna específica"}
        - Expresiones que el alumno considera difíciles: {difficult_expressions if difficult_expressions else "Ninguna específica"}
        
        PRINCIPIOS DE ZONA DE DESARROLLO PRÓXIMO (ZDP) A APLICAR:
        1. Identifica lo que el estudiante ya sabe hacer con facilidad (ejercicios fáciles)
        2. Identifica lo que aún no puede hacer sin ayuda (ejercicios difíciles)
        3. Diseña un ejercicio que esté CLARAMENTE por encima de su nivel actual, pero no tan complejo 
           como los que encuentra muy difíciles
        4. El ejercicio DEBE ser más desafiante que lo que ya domina - NO del mismo nivel que ya maneja
        
        REGLAS ESPECÍFICAS PARA LA GENERACIÓN DEL EJERCICIO:
        1. Identifica claramente la diferencia entre lo que considera fácil y difícil
        2. Crea un ejercicio que introduzca UN NUEVO CONCEPTO o complejidad que no esté presente en los ejercicios fáciles
        3. Aplica estas pautas específicas dependiendo del feedback:
           - Si las ecuaciones lineales simples son fáciles, usa lineales más complejas con paréntesis o coeficientes fraccionales
           - Si las ecuaciones cuadráticas son difíciles, no las incluyas aún, pero puedes acercarte con ejercicios que incluyan multiplicación de paréntesis
           - Si las fracciones son difíciles, introduce una fracción simple en un contexto que ya domina
           - Si los ejercicios fáciles tienen un solo paso, diseña uno con 3-4 pasos claros
        4. NUNCA generes un ejercicio que sea esencialmente igual a los que ya domina con solo números diferentes
        5. El ejercicio DEBE representar un claro paso adelante en complejidad y aprendizaje
        
        EJEMPLOS DE PROGRESIÓN ADECUADA:
        - Si domina: 2x + 3 = 7 → Siguiente nivel: 2(x + 3) - 4 = 10
        - Si domina: 5x - 2 = 3x + 4 → Siguiente nivel: 3x/2 - 4 = x + 2
        - Si domina: Ecuaciones de un paso → Siguiente nivel: Ecuaciones con variables en ambos lados y paréntesis
        
        ESTRUCTURA DE TU RESPUESTA:
        - "Aquí tienes un ejercicio de [tema] diseñado para avanzar tu nivel actual:"
        - [Presenta el ejercicio más avanzado]
        - "Vamos a resolverlo paso a paso:"
        - [Paso 1 con explicación detallada]
        - [Paso 2 con explicación detallada]
        - [Continuar con los pasos necesarios]
        - "¿Has entendido la explicación?"
        
        Historial de la conversación:
        {history}
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

def create_scaffolding_agent() -> Agent[ChatMemoryContext]:
    """Crea el agente de andamiaje."""
    debug_print("Creando agente de andamiaje")
    
    return Agent[ChatMemoryContext](
        name="ScaffoldingAgent",
        model="gpt-4-turbo-preview",
        instructions=dynamic_scaffolding_instructions
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
async def analyze_conversation(context: ChatMemoryContext, agent_name: str, response_content: str, flow_state: str, exercise_generated: bool, student_confirmed_understanding: bool):
    """Analiza la conversación para determinar flujo y extraer información relevante.
    
    Args:
        context: El contexto compartido de la conversación
        agent_name: Nombre del agente que envió la respuesta
        response_content: Contenido de la respuesta
        flow_state: Estado actual del flujo
        exercise_generated: Si ya se generó un ejercicio
        student_confirmed_understanding: Si el estudiante confirmó entendimiento
    """
    debug_print(f"[DEBUG] Analizando respuesta de {agent_name} en estado {flow_state}")
    
    # Variables para guardar información extraída
    new_flow_state = flow_state  # Inicializar con el estado actual
    
    # Comprobar si hay un mensaje de transferencia de control
    if "[TRANSFERENCIA_CONTROL]" in response_content:
        # Determinar a qué agente se transferirá según el estado actual
        if flow_state == "diagnóstico":
            new_flow_state = "calibración"
            debug_print(f"[TRANSICIÓN] ⚠️ Cambio de agente: {agent_name} → Calibrador")
        elif flow_state == "calibración":
            new_flow_state = "andamiaje"
            debug_print(f"[TRANSICIÓN] ⚠️ Cambio de agente: {agent_name} → Andamiaje")
        elif flow_state == "andamiaje":
            new_flow_state = "diagnóstico"
            debug_print(f"[TRANSICIÓN] ⚠️ Cambio de agente: {agent_name} → Diagnóstico")
            
        debug_print(f"[CONTROL] Transferencia de control detectada: {flow_state} → {new_flow_state}")
        
        # Eliminar el mensaje de transferencia de control antes de mostrarlo al usuario
        response_content = response_content.replace("[TRANSFERENCIA_CONTROL]", "").strip()
    
    # Extraer tema de matemáticas
    if not context.topic and "tema" in response_content.lower() and "?" in response_content:
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
    if not context.knowledge_level and "sabes" in response_content.lower() and "?" in response_content:
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
    if not context.math_expressions and "expresión" in response_content.lower():
        expressions = []
        for line in response_content.split('\n'):
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
    if "[TRANSFERENCIA_CONTROL]" in response_content:
        transfer_detected = True
        old_state = context.current_flow_state
        
        if context.current_flow_state == "diagnostic":
            context.advance_flow()  # diagnostic -> calibration
            debug_print(f"[FLUJO] ⚠️ TRANSFERENCIA DETECTADA: {old_state} -> {context.current_flow_state}")
        elif context.current_flow_state == "calibration":
            context.advance_flow()  # calibration -> scaffolding
            debug_print(f"[FLUJO] ⚠️ TRANSFERENCIA DETECTADA: {old_state} -> {context.current_flow_state}")
            debug_print(f"[FLUJO] 🏗️ Control transferido al agente de andamiaje")
        elif context.current_flow_state == "scaffolding":
            context.advance_flow()  # scaffolding -> final
            debug_print(f"[FLUJO] ⚠️ TRANSFERENCIA DETECTADA: {old_state} -> {context.current_flow_state}")
    else:
        # Si estamos en fase de calibración y hay feedback pero no se detectó transferencia
        if context.current_flow_state == "calibration" and len(context.user_feedback) > 0:
            debug_print(f"[ERROR] ⚠️ El calibrador tiene feedback ({len(context.user_feedback)} items) pero no envió [TRANSFERENCIA_CONTROL]")
            debug_print(f"[ERROR] ⚠️ Respuesta del calibrador: {response_content[:100]}...")
            
            # Forzar la transferencia
            debug_print(f"[FLUJO] ⚠️ Forzando transferencia manual: calibration -> scaffolding")
            context.advance_flow()  # calibration -> scaffolding
    
    return new_flow_state, exercise_generated, student_confirmed_understanding, None, None

# Función auxiliar para mostrar mensajes de agente con formato correcto
def display_agent_message(agent_name: str, message: str):
    """
    Muestra un mensaje de un agente con un indicador visual claro.
    
    Args:
        agent_name: Nombre del agente que envía el mensaje
        message: Contenido del mensaje a mostrar
    """
    # Indicadores visuales para cada agente
    agent_indicators = {
        "Diagnóstico": "🔍",
        "Orquestador": "🎭",
        "Andamiaje": "🏗️",
        "Calibrador": "🎯"
    }
    
    # Obtener el indicador para este agente (o usar un valor predeterminado)
    indicator = agent_indicators.get(agent_name, "🤖")
    
    # Imprimir información de depuración
    debug_print(f"[DEBUG] Mensaje del agente '{agent_name}': {message[:50]}...")
    
    # Mostrar el mensaje con el indicador visual
    print(f"\n{indicator} [{agent_name}]: {message}\n")

# Función para procesar la respuesta antes de mostrarla al usuario
def process_response_for_display(response: str) -> str:
    """Procesa la respuesta para que sea amigable para el usuario."""
    # Reemplazar el mensaje de transferencia con mensaje vacío (no se mostrará)
    if "[TRANSFERENCIA_CONTROL]" in response:
        return ""  # Mensaje vacío, no se mostrará al usuario
    
    return response

# Verificar si el mensaje del usuario indica entendimiento
def check_understanding(message: str) -> bool:
    """Verifica si el mensaje del usuario indica entendimiento del ejercicio."""
    understanding_phrases = [
        "entendí", "comprendo", "entiendo", "tiene sentido", "ya entendí", 
        "lo tengo", "quedó claro", "ahora sí", "me quedó claro", "comprendo",
        "lo he entendido", "ya lo entendí", "ya comprendí", "claro", "entendido"
    ]
    
    message_lower = message.lower()
    for phrase in understanding_phrases:
        if phrase in message_lower:
            debug_print(f"Detectada frase de entendimiento: '{phrase}'")
            return True
    
    return False

def handle_agent_chain(user_input, flow_state, exercise_generated, student_confirmed_understanding):
    debug_print(f"[DEBUG] Estado actual: {flow_state}")
    debug_print(f"[DEBUG] Entrada del usuario: {user_input}")
    
    # Token de control para transferencia entre agentes
    CONTROL_TOKEN = "[TRANSFERENCIA_CONTROL]"
    
    # Función auxiliar para eliminar tokens de control
    def remove_control_tokens(text):
        # Eliminar todas las instancias de tokens de control
        cleaned_text = text.replace(CONTROL_TOKEN, "")
        # Eliminar comandos de control específicos
        for state in ["diagnóstico", "orquestador", "andamiaje"]:
            cleaned_text = cleaned_text.replace(f"{CONTROL_TOKEN}:{state}", "")
        return cleaned_text.strip()
    
    # Iniciar con el agente correcto según el estado actual
    if flow_state == "diagnóstico":
        debug_print("[DEBUG] Invocando agente de diagnóstico")
        response = diagnostic_agent.invoke(user_input)
        response_text = response.content
        
        # Analizar respuesta para determinar el siguiente agente
        if f"{CONTROL_TOKEN}:orquestador" in response_text:
            debug_print("[DEBUG] Transferencia detectada: diagnóstico -> orquestador")
            flow_state = "orquestador"
        
        # Mostrar mensaje limpio
        display_agent_message("Diagnóstico", remove_control_tokens(response_text))
        
    elif flow_state == "orquestador":
        debug_print("[DEBUG] Invocando agente orquestador")
        response = orchestrator_agent.invoke(user_input)
        response_text = response.content
        
        # Analizar respuesta para determinar el siguiente agente
        if f"{CONTROL_TOKEN}:diagnóstico" in response_text:
            debug_print("[DEBUG] Transferencia detectada: orquestador -> diagnóstico")
            flow_state = "diagnóstico"
        elif f"{CONTROL_TOKEN}:andamiaje" in response_text:
            debug_print("[DEBUG] Transferencia detectada: orquestador -> andamiaje")
            flow_state = "andamiaje"
            
        # Verificar si se ha generado un ejercicio
        if "Aquí tienes un ejercicio" in response_text:
            exercise_generated = True
            
        # Mostrar mensaje limpio
        display_agent_message("Orquestador", remove_control_tokens(response_text))
        
    elif flow_state == "andamiaje":
        debug_print("[DEBUG] Invocando agente de andamiaje")
        response = scaffolding_agent.invoke(user_input)
        response_text = response.content
        
        # Analizar respuesta para determinar el siguiente agente
        if f"{CONTROL_TOKEN}:orquestador" in response_text:
            debug_print("[DEBUG] Transferencia detectada: andamiaje -> orquestador")
            flow_state = "orquestador"
            
        # Comprobar comprensión del estudiante
        if "entiendo" in user_input.lower() or "comprendo" in user_input.lower():
            student_confirmed_understanding = True
            
        # Mostrar mensaje limpio
        display_agent_message("Andamiaje", remove_control_tokens(response_text))
    
    return flow_state, exercise_generated, student_confirmed_understanding

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
    scaffolding = create_scaffolding_agent()  # Nuevo agente de andamiaje
    
    # Configurar los handoffs en el orden correcto
    orchestrator.handoffs = [diagnostic]  # Orquestador -> Diagnóstico
    diagnostic.handoffs = [orchestrator]  # Diagnóstico -> Orquestador (que irá a Calibrador)
    orchestrator.handoffs.append(calibrator)  # Orquestador también puede ir a Calibrador
    calibrator.handoffs = [scaffolding]  # Calibrador -> Andamiaje
    scaffolding.handoffs = [orchestrator]  # Andamiaje -> Orquestador (final)
    
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
        
        # Solo mostrar si hay un mensaje válido (no transferencia)
        if response_text:
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
            
            # Verificar entendimiento si estamos en fase de andamiaje
            if context.current_flow_state == "scaffolding" and check_understanding(user_input):
                context.scaffold_understood = True
                debug_print("[DEBUG] Usuario ha confirmado entendimiento del ejercicio")
            
            # Analizar el input para el calibrador
            if context.current_flow_state == "calibration" and context.math_expressions and not context.user_feedback:
                # Verificar si el input contiene feedback sobre expresiones
                has_feedback = False
                debug_print(f"[DEBUG] Analizando posible feedback en: {user_input}")
                
                # Método 1: Buscar referencias a números de las expresiones
                if any(str(num) in user_input.lower() for num in range(1, 5)):
                    debug_print("[DEBUG] Detectada posible referencia a números de las expresiones")
                    if "fácil" in user_input.lower() or "facil" in user_input.lower() or "sencill" in user_input.lower():
                        debug_print("[DEBUG] Detectada mención de expresiones fáciles")
                        # Si menciona "1" o "uno", considera la primera expresión como fácil
                        if "1" in user_input or "uno" in user_input or "primer" in user_input:
                            context.add_user_feedback(context.math_expressions[0], "fácil")
                            has_feedback = True
                        if "2" in user_input or "dos" in user_input or "segund" in user_input:
                            context.add_user_feedback(context.math_expressions[1], "fácil")
                            has_feedback = True
                        if "3" in user_input or "tres" in user_input or "tercer" in user_input:
                            context.add_user_feedback(context.math_expressions[2], "fácil")
                            has_feedback = True
                        if "4" in user_input or "cuatro" in user_input or "cuart" in user_input:
                            context.add_user_feedback(context.math_expressions[3], "fácil")
                            has_feedback = True
                            
                    if "difícil" in user_input.lower() or "dificil" in user_input.lower() or "complic" in user_input.lower() or "complex" in user_input.lower():
                        debug_print("[DEBUG] Detectada mención de expresiones difíciles")
                        # Si menciona "1" o "uno", considera la primera expresión como difícil
                        if "1" in user_input or "uno" in user_input or "primer" in user_input:
                            context.add_user_feedback(context.math_expressions[0], "difícil")
                            has_feedback = True
                        if "2" in user_input or "dos" in user_input or "segund" in user_input:
                            context.add_user_feedback(context.math_expressions[1], "difícil")
                            has_feedback = True
                        if "3" in user_input or "tres" in user_input or "tercer" in user_input:
                            context.add_user_feedback(context.math_expressions[2], "difícil")
                            has_feedback = True
                        if "4" in user_input or "cuatro" in user_input or "cuart" in user_input:
                            context.add_user_feedback(context.math_expressions[3], "difícil")
                            has_feedback = True
                
                # Método 2: Buscar expresiones específicas (menos confiable)
                if not has_feedback:
                    for i, expr in enumerate(context.math_expressions):
                        expr_normalized = expr.lower().replace('\\', '').replace(' ', '')
                        user_input_normalized = user_input.lower().replace(' ', '')
                        
                        # Buscar fragmentos de la expresión
                        for fragment in expr_normalized.split('+'):
                            if fragment and len(fragment) > 2 and fragment in user_input_normalized:
                                debug_print(f"[DEBUG] Encontrado fragmento de expresión: {fragment}")
                                if "fácil" in user_input.lower() or "facil" in user_input.lower() or "sencill" in user_input.lower():
                                    context.add_user_feedback(expr, "fácil")
                                    has_feedback = True
                                elif "difícil" in user_input.lower() or "dificil" in user_input.lower() or "complic" in user_input.lower():
                                    context.add_user_feedback(expr, "difícil")
                                    has_feedback = True
                
                # Si se detectó feedback y tenemos al menos una expresión con feedback, forzar la transferencia
                if has_feedback or len(context.user_feedback) > 0:
                    debug_print(f"[DEBUG] Feedback detectado: {context.user_feedback}, forzando transferencia al andamiaje")
                    
                    # Agregar mensaje del usuario al contexto
                    # Ejecutar el calibrador para generar una respuesta de transferencia (que no se mostrará al usuario)
                    with custom_span("execute_calibrator_transfer", data={"agent": "calibrator", "action": "transfer"}):
                        cal_response = f"Gracias por tu feedback. Veo que las expresiones {', '.join([str(i+1) for i, expr in enumerate(context.math_expressions) if context.user_feedback.get(expr) == 'fácil'])} te resultan fáciles, mientras que las expresiones {', '.join([str(i+1) for i, expr in enumerate(context.math_expressions) if context.user_feedback.get(expr) == 'difícil'])} te parecen difíciles. [TRANSFERENCIA_CONTROL]"
                    
                    # Cambiar a la fase de andamiaje
                    context.current_flow_state = "scaffolding"
                    debug_print("[DEBUG] Avanzando flujo a: scaffolding")
                    
                    # Agregar al historial pero no mostrar el mensaje de transferencia
                    context.add_message("Asistente", process_response_for_display(cal_response))
                    
                    # Ejecutar turno extra del andamiaje
                    extra_input = "Necesito generar un ejercicio apropiado y comenzar a explicarlo paso a paso inmediatamente, sin esperar respuesta del alumno"
                    with custom_span("execute_scaffolding_first", data={"agent": "scaffolding", "action": "first_interaction"}):
                        debug_print("[DEBUG] Ejecutando agente de andamiaje con instrucción: " + extra_input)
                        
                        # Ejecutar el agente de andamiaje para generar el ejercicio
                        extra_scaffold_result = await Runner.run(
                            scaffolding,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del andamiaje
                        extra_scaffold_response = extra_scaffold_result.final_output
                        debug_print(f"[DEBUG] Respuesta del andamiaje: {extra_scaffold_response[:100]}...")
                        context.add_message("Asistente", extra_scaffold_response)
                        display_agent_message("Andamiaje", extra_scaffold_response)
                        continue  # Saltar al siguiente turno de usuario
            
            # Determinar qué agente usar basado en el estado actual
            if context.current_flow_state == "diagnostic":
                current_agent = diagnostic
                agent_name = "Diagnóstico"
            elif context.current_flow_state == "calibration":
                current_agent = calibrator
                agent_name = "Calibrador"
            elif context.current_flow_state == "scaffolding":
                current_agent = scaffolding
                agent_name = "Andamiaje"
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
                        
                        # Agregar mensaje de transferencia al historial, pero no mostrar al usuario
                        if "[TRANSFERENCIA_CONTROL]" not in response_text:
                            transfer_message = "He completado mi diagnóstico. Ahora pasaré el control a mi colega."
                        else:
                            transfer_message = process_response_for_display(response_text)
                        
                        # Solo agregar al historial, no mostrar
                        context.add_message("Asistente", transfer_message)
                        
                        # Ejecutar turno extra del calibrador inmediatamente
                        extra_input = "Necesito generar un ejercicio apropiado y comenzar a explicarlo paso a paso inmediatamente, sin esperar respuesta del alumno"
                        extra_result = await Runner.run(
                            calibrator,
                            input="Necesito expresiones matemáticas para evaluar",
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del calibrador
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del calibrador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        
                        # Mostrar directamente la respuesta del calibrador, sin indicar cambio de agente
                        display_agent_message("Calibrador", extra_response)
                        
                        # Analizar para extraer expresiones
                        await analyze_conversation(context, agent_name, extra_response, context.current_flow_state, context.scaffold_exercise != "", context.scaffold_understood)
                        continue  # Saltar al siguiente turno de usuario
                
                # Detectar transferencia explícita
                if "[TRANSFERENCIA_CONTROL]" in response_text:
                    debug_print(f"[DEBUG] Transferencia explícita detectada desde {agent_name}")
                    
                    if context.current_flow_state == "diagnostic":
                        # Cambiar al calibrador después del diagnóstico
                        context.current_flow_state = "calibration"
                        debug_print("[DEBUG] Avanzando flujo a: calibration")
                        
                        # No mostrar el mensaje de transferencia, solo agregar al historial
                        context.add_message("Asistente", process_response_for_display(response_text))
                        
                        # Ejecutar turno extra del calibrador
                        extra_input = "Necesito generar un ejercicio apropiado y comenzar a explicarlo paso a paso inmediatamente, sin esperar respuesta del alumno"
                        extra_result = await Runner.run(
                            calibrator,
                            input="Necesito expresiones matemáticas para evaluar",
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del calibrador
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del calibrador: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        
                        # Mostrar directamente la respuesta del calibrador
                        display_agent_message("Calibrador", extra_response)
                        
                        # Analizar para extraer expresiones
                        await analyze_conversation(context, agent_name, extra_response, context.current_flow_state, context.scaffold_exercise != "", context.scaffold_understood)
                        continue  # Saltar al siguiente turno de usuario
                        
                    elif context.current_flow_state == "calibration":
                        # Cambiar al andamiaje después de la calibración
                        context.current_flow_state = "scaffolding"
                        debug_print("[DEBUG] Avanzando flujo a: scaffolding")
                        
                        # No mostrar el mensaje de transferencia, solo agregar al historial
                        context.add_message("Asistente", process_response_for_display(response_text))
                        
                        # Ejecutar turno extra del andamiaje
                        extra_input = "Necesito generar un ejercicio apropiado y comenzar a explicarlo paso a paso inmediatamente, sin esperar respuesta del alumno"
                        extra_result = await Runner.run(
                            scaffolding,
                            input=extra_input,
                            context=context,
                            run_config=run_config
                        )
                        
                        # Procesar y mostrar respuesta del andamiaje
                        extra_response = extra_result.final_output
                        debug_print(f"[DEBUG] Respuesta del andamiaje: {extra_response}")
                        context.add_message("Asistente", extra_response)
                        
                        # Mostrar directamente la respuesta del andamiaje
                        display_agent_message("Andamiaje", extra_response)
                        
                        # Analizar para extraer expresiones
                        await analyze_conversation(context, "Andamiaje", extra_response, context.current_flow_state, context.scaffold_exercise != "", context.scaffold_understood)
                        continue  # Saltar al siguiente turno de usuario
                    
                    elif context.current_flow_state == "scaffolding":
                        # Cambiar al orquestador final
                        context.current_flow_state = "final"
                        debug_print("[DEBUG] Avanzando flujo a: final")
                        
                        # No mostrar el mensaje de transferencia, solo agregar al historial
                        context.add_message("Asistente", process_response_for_display(response_text))
                        
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
                        
                        # Mostrar directamente la respuesta del orquestador
                        display_agent_message("Orquestador", extra_response)
                        continue  # Saltar al siguiente turno de usuario
                
                # Si no hay transferencia, procesar normalmente
                display_text = process_response_for_display(response_text)
                
                # Solo mostrar si hay un mensaje válido (no transferencia)
                if display_text:
                    context.add_message("Asistente", response_text)
                    display_agent_message(agent_name, display_text)
                
                # Analizar la conversación
                await analyze_conversation(context, agent_name, response_text, context.current_flow_state, context.scaffold_exercise != "", context.scaffold_understood)

if __name__ == "__main__":
    asyncio.run(chat()) 