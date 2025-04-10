import asyncio
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig, HandoffInputData, RunContextWrapper

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

def create_triage_agent(spanish_agent: Agent[ChatMemoryContext], english_agent: Agent[ChatMemoryContext]) -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Triage Assistant",
        model="gpt-4-turbo-preview",
        instructions="""Eres un agente de triaje que detecta el idioma del usuario.
        Si detectas español, transfiere la conversación al Asistente Español.
        Si detectas inglés, transfiere la conversación al English Assistant.
        Si detectas ambos idiomas, prioriza el español.
        No respondas directamente, solo transfiere la conversación.""",
        handoffs=[spanish_agent, english_agent]
    )

# Función para preservar el contexto durante los handoffs
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    # Simplemente pasamos todos los datos sin modificar
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )

async def chat():
    # Crear el contexto compartido
    context = ChatMemoryContext()
    
    # Crear los agentes
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    triage_agent = create_triage_agent(spanish_agent, english_agent)
    
    # Configurar el Runner para preservar el contexto
    run_config = RunConfig(
        handoff_input_filter=memory_handoff_filter
    )
    
    print("¡Bienvenido! Puedes escribir en español o inglés.")
    print("Escribe 'salir' para terminar la conversación.")
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() == "salir":
            break
            
        # Agregar el mensaje del usuario al historial
        context.add_message("Usuario", user_input)
        
        # Ejecutar el chat con el agente de triaje
        result = await Runner.run(
            triage_agent,
            input=user_input,
            context=context,
            run_config=run_config
        )
        
        # Agregar la respuesta al historial
        context.add_message("Asistente", result.final_output)
        print(f"\nAsistente: {result.final_output}")

if __name__ == "__main__":
    asyncio.run(chat())
