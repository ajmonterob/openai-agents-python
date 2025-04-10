import asyncio
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from agents import Agent, Runner, function_tool, RunConfig

@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    response_count: int = 0
    spanish_responses: int = 0
    english_responses: int = 0

    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
        if role == "assistant":
            self.response_count += 1

    def get_history(self) -> str:
        return "\n".join(self.history)

    def can_respond(self) -> bool:
        return self.response_count < 4

    def get_response_phase(self) -> str:
        if self.spanish_responses < 2:
            return "spanish"
        elif self.english_responses < 2:
            return "english"
        return "limit_reached"

    def increment_language_count(self, language: str):
        if language == "spanish":
            self.spanish_responses += 1
        else:
            self.english_responses += 1

# Modelos para las herramientas
class Weather(BaseModel):
    location: str
    temperature: float
    condition: str

class CalculatorResult(BaseModel):
    result: float

# Herramientas
@function_tool
def get_weather(location: str) -> Weather:
    return Weather(location=location, temperature=25.0, condition="sunny")

@function_tool
def calculate(expression: str) -> CalculatorResult:
    return CalculatorResult(result=eval(expression))

def create_spanish_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Asistente Español",
        model="gpt-4-turbo-preview",
        instructions=lambda context_wrapper, agent: f"""Eres un asistente en español. 
        DEBES responder SIEMPRE en español.
        NO PUEDES cambiar al inglés bajo ninguna circunstancia.
        Mantén la coherencia con la historia de la conversación.
        
        Historia de la conversación:
        {context_wrapper.context.get_history()}
        """,
        tools=[get_weather, calculate]
    )

def create_english_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="English Assistant",
        model="gpt-4-turbo-preview",
        instructions=lambda context_wrapper, agent: f"""You are an English assistant.
        You MUST ALWAYS respond in English.
        You CANNOT switch to Spanish under any circumstances.
        Even if the user writes in Spanish, you MUST respond in English.
        If the user asks why you're speaking English, explain that you are the English assistant.
        Maintain conversation history coherence.
        
        Conversation history:
        {context_wrapper.context.get_history()}
        """,
        tools=[get_weather, calculate]
    )

async def chat():
    # Crear agentes
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    
    # Crear contexto compartido
    context = ChatMemoryContext()
    
    print("¡Bienvenido! Puedes escribir en español o inglés.")
    print("El asistente responderá 2 veces en español y 2 veces en inglés.")
    print("Después de 4 respuestas, la conversación ha terminado.")
    print("Escribe 'salir' para terminar la conversación en cualquier momento.\n")
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break
            
        # Agregar mensaje del usuario al historial
        context.add_message("user", user_input)
            
        # Determinar el agente a usar basado en la fase actual
        phase = context.get_response_phase()
        if phase == "limit_reached":
            print("\n¡Hemos alcanzado el límite de 4 respuestas! La conversación ha terminado.")
            break
            
        selected_agent = spanish_agent if phase == "spanish" else english_agent
        print(f"\n[DEBUG] Agente seleccionado: {selected_agent.name}")
        print(f"[DEBUG] Fase actual: {phase}")
        print(f"[DEBUG] Respuestas en español: {context.spanish_responses}")
        print(f"[DEBUG] Respuestas en inglés: {context.english_responses}")
        
        # Ejecutar el agente seleccionado
        result = await Runner.run(
            selected_agent,
            user_input,
            context=context,
            run_config=RunConfig()
        )
        
        # Agregar la respuesta al contexto
        context.add_message("assistant", result.final_output)
        context.increment_language_count(phase)
        print(f"\nAsistente: {result.final_output}")
        
        # Mostrar información sobre el cambio de idioma
        if context.response_count < 4:
            if phase == "spanish":
                print(f"\n[Quedan {2 - context.spanish_responses} respuestas en español]")
            else:
                print(f"\n[Remaining {2 - context.english_responses} responses in English]")

if __name__ == "__main__":
    asyncio.run(chat()) 