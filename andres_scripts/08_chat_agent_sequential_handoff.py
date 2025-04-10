import asyncio
from dataclasses import dataclass, field
from typing import List
from pydantic import BaseModel
from src.agents import Agent, Runner, RunConfig

@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    spanish_responses: int = 0
    english_responses: int = 0

    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
        if role == "assistant":
            if self.spanish_responses < 2:
                self.spanish_responses += 1
            else:
                self.english_responses += 1

    def get_history(self) -> str:
        return "\n".join(self.history)

    def can_respond(self) -> bool:
        return (self.spanish_responses + self.english_responses) < 4

# Modelos para las herramientas
class Weather(BaseModel):
    location: str
    temperature: float
    condition: str

class CalculatorResult(BaseModel):
    result: float

# Herramientas
def get_weather(location: str) -> Weather:
    return Weather(
        location=location,
        temperature=25.0,
        condition="soleado"
    )

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
        
        Conversation history:
        {context_wrapper.context.get_history()}
        """,
        tools=[get_weather, calculate]
    )

def create_triage_agent(spanish_agent: Agent[ChatMemoryContext], english_agent: Agent[ChatMemoryContext]) -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Triage Agent",
        model="gpt-4-turbo-preview",
        instructions=lambda context_wrapper, agent: f"""Eres un agente de triaje que determina qué agente debe responder.
        Si el contexto tiene menos de 2 respuestas en español, pasa al agente español.
        Si ya hay 2 respuestas en español, pasa al agente inglés.
        Si ya hay 2 respuestas en cada idioma, termina la conversación.
        
        Historia de la conversación:
        {context_wrapper.context.get_history()}
        """,
        handoffs=[
            {
                "name": "spanish_handoff",
                "description": "Pasa al agente español",
                "agent": spanish_agent,
                "input_filter": lambda input_data: input_data.items
            },
            {
                "name": "english_handoff",
                "description": "Pasa al agente inglés",
                "agent": english_agent,
                "input_filter": lambda input_data: input_data.items
            }
        ]
    )

async def chat():
    # Crear agentes
    spanish_agent = create_spanish_agent()
    english_agent = create_english_agent()
    triage_agent = create_triage_agent(spanish_agent, english_agent)
    
    # Crear contexto compartido
    context = ChatMemoryContext()
    
    print("¡Bienvenido! Puedes escribir en español o inglés.")
    print("El asistente responderá 2 veces en español y 2 veces en inglés.")
    print("Después de 4 respuestas, la conversación terminará.")
    print("Escribe 'salir' para terminar la conversación en cualquier momento.\n")
    
    while True:
        user_input = input("\nTú: ")
        if user_input.lower() in ["salir", "exit", "quit"]:
            break
            
        # Agregar mensaje del usuario al historial
        context.add_message("user", user_input)
        
        # Verificar si podemos seguir respondiendo
        if not context.can_respond():
            print("\n¡Hemos alcanzado el límite de 4 respuestas! La conversación ha terminado.")
            break
        
        # Ejecutar el agente de triaje
        result = await Runner.run(
            triage_agent,
            user_input,
            context=context,
            run_config=RunConfig()
        )
        
        # Agregar la respuesta al contexto
        context.add_message("assistant", result.final_output)
        print(f"\nAsistente: {result.final_output}")
        
        # Mostrar información sobre el cambio de idioma
        if context.can_respond():
            if context.spanish_responses < 2:
                print(f"\n[Quedan {2 - context.spanish_responses} respuestas en español]")
            else:
                print(f"\n[Remaining {2 - context.english_responses} responses in English]")

if __name__ == "__main__":
    asyncio.run(chat()) 