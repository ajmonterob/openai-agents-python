# Memoria Compartida entre Agentes

Este documento explica en detalle cómo implementar un sistema de chat con múltiples agentes que comparten memoria, permitiendo una conversación coherente incluso cuando se cambia de agente.

## Visión General

Cuando desarrollamos sistemas multi-agente con OpenAI Agents SDK, un desafío común es mantener el contexto de la conversación cuando ocurren handoffs entre agentes. En un flujo típico:

1. El usuario envía un mensaje
2. Un agente de triaje detecta el idioma
3. El agente de triaje transfiere (handoff) al agente especializado
4. El agente especializado responde

El problema es que, por defecto, cuando ocurre un handoff, cada agente no tiene acceso completo al contexto histórico de una manera que pueda procesar fácilmente.

## Solución Implementada

Nuestra solución utiliza tres componentes clave del SDK:

1. **Contexto compartido**: Un objeto de contexto personalizado que almacena el historial de la conversación
2. **Instrucciones dinámicas**: Funciones que generan instrucciones con el historial incorporado
3. **Filtros de handoff**: Para mantener el contexto durante las transferencias entre agentes

### 1. Contexto Compartido

Definimos una clase personalizada `ChatMemoryContext` para almacenar y gestionar el historial de la conversación:

```python
@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")
    
    def get_history(self) -> str:
        return "\n".join(self.history)
```

Características principales:
- Almacenamiento simple de mensajes con rol y contenido
- Método para recuperar todo el historial como una cadena de texto formateada

### 2. Instrucciones Dinámicas

El SDK permite proveer funciones dinámicas para generar instrucciones en tiempo de ejecución, que reciben el contexto actual:

```python
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
```

Esta función:
- Accede al historial completo desde el contexto
- Incorpora ese historial directamente en las instrucciones del sistema
- Incluye instrucciones explícitas para revisar el historial y mantener coherencia

### 3. Creación de Agentes con Tipado Genérico

Los agentes se crean indicando explícitamente el tipo de contexto que utilizarán:

```python
def create_spanish_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="Asistente Español",
        model="gpt-4-turbo-preview",
        instructions=dynamic_spanish_instructions,
        tools=[get_weather, calculate]
    )
```

Aspectos clave:
- El agente está tipado con `Agent[ChatMemoryContext]`
- Las instrucciones son dinámicas y reciben el contexto en tiempo de ejecución

### 4. Filtro de Handoff

Cuando ocurre un handoff, necesitamos asegurar que el contexto se preserve. Usando `HandoffInputData`:

```python
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    # Simplemente pasamos todos los datos sin modificar
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )
```

Este filtro asegura que todos los datos se mantengan intactos durante los handoffs.

### 5. Configuración del Runner

El componente final es la configuración correcta del `Runner`:

```python
run_config = RunConfig(
    handoff_input_filter=memory_handoff_filter
)

# En el loop principal
result = await Runner.run(
    triage_agent,
    input=user_input,
    context=context,  # Pasamos el contexto compartido
    run_config=run_config
)
```

Puntos importantes:
- Configuramos el `handoff_input_filter` en el `RunConfig`
- Pasamos el objeto de contexto compartido al método `Runner.run()`
- Actualizamos el historial después de cada interacción

## Gestión del Ciclo de Vida del Mensaje

Para cada interacción, actualizamos el historial:

1. **Antes** de procesar: Añadimos el mensaje del usuario al historial
   ```python
   context.add_message("Usuario", user_input)
   ```

2. **Después** de procesar: Añadimos la respuesta del asistente
   ```python
   context.add_message("Asistente", result.final_output)
   ```

## Ventajas de Este Enfoque

1. **Memoria Persistente**: La información se mantiene durante toda la conversación
2. **Coherencia entre Handoffs**: Los agentes pueden referirse a información anterior
3. **Tipo Seguro**: El sistema utiliza tipos genéricos para garantizar consistencia
4. **Fácil de Mantener**: Estructura modular con separación clara de responsabilidades

## Casos de Uso

Este patrón es especialmente útil para:

1. **Chats multilingües**: Como en nuestro ejemplo, donde el idioma puede cambiar
2. **Servicios especializados**: Donde diferentes agentes manejan diferentes dominios
3. **Conversaciones con crecimiento contextual**: Donde la información se acumula con el tiempo

## Consideraciones

1. **Tamaño del Contexto**: A medida que la conversación crece, el historial puede volverse demasiado grande
2. **Memoria Selectiva**: Puedes implementar lógica para filtrar qué elementos incluir en las instrucciones
3. **Eficiencia**: Para conversaciones largas, considera resumir o truncar el historial

## Implementación Completa

Para ver la implementación completa, revisa el archivo `chat_agent_with_unified_memory.py` que demuestra todos estos conceptos en acción.

```python
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
    
    # Loop principal
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
```

Con esta implementación, has logrado crear un sistema robusto de chat multi-agente con memoria compartida que mantiene la coherencia incluso cuando se cambia entre agentes. 