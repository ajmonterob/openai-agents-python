# Orquestramiento de Agentes en el SDK OpenAI Agents

El orquestramiento de agentes se refiere a cómo varios agentes pueden trabajar juntos, coordinarse y transferir el control entre ellos para resolver tareas complejas. El SDK de OpenAI Agents proporciona mecanismos sofisticados para este orquestramiento, que puedes implementar siguiendo dos enfoques principales.

## Enfoques de Orquestramiento

El SDK soporta dos paradigmas fundamentales de orquestramiento:

### 1. Orquestramiento dirigido por IA (LLM)

En este enfoque, el propio modelo de lenguaje (LLM) toma decisiones sobre qué agente debe manejar una solicitud determinada. Es un orquestramiento "inteligente" donde el LLM:

- Analiza el contenido de la solicitud del usuario
- Decide qué agente especializado es más adecuado
- Transfiere el control mediante un mecanismo llamado "handoff"

**Ejemplo**: Un agente de triaje que decide si una consulta debe ir al agente de español o inglés:

```python
triage_agent = Agent(
    name="Triage Assistant",
    instructions="Detecta el idioma y transfiere al agente apropiado",
    handoffs=[spanish_agent, english_agent]
)
```

### 2. Orquestramiento programático

Aquí, tú como desarrollador defines explícitamente el flujo de control mediante código. Puedes:

- Encadenar agentes secuencialmente
- Ejecutar agentes en paralelo
- Implementar lógica condicional para determinar qué agente se ejecuta a continuación

**Ejemplo**: Encadenamiento secuencial de agentes:

```python
# Primer agente genera un esquema
outline_result = await Runner.run(outline_agent, "Escribe sobre IA")
# Segundo agente escribe contenido basado en el esquema
content_result = await Runner.run(content_agent, outline_result.final_output)
```

## Mecanismos de Orquestramiento

El SDK proporciona varios mecanismos clave para implementar estos enfoques:

### 1. Sistema de Handoffs

El mecanismo de "handoff" es fundamental en el orquestramiento dirigido por IA:

1. **Definición de agentes**: Creas varios agentes especializados
2. **Configuración de handoffs**: Declaras qué agentes pueden recibir handoffs
3. **Toma de decisiones**: El LLM decide cuándo hacer un handoff basado en sus instrucciones
4. **Transferencia de control**: El control pasa al agente seleccionado, junto con el contexto relevante

La magia ocurre en la clase `Runner`, que implementa un bucle:

```python
# Pseudocódigo del bucle interno del Runner
while not final_output and turns < max_turns:
    output = await call_llm(current_agent, current_input)
    
    if output.has_handoff():
        next_agent = resolve_handoff_agent(output.handoff)
        current_agent = next_agent
        # Preservar contexto durante el handoff
        current_input = apply_handoff_filter(output, next_agent)
        continue
        
    if output.has_tool_calls():
        tool_results = await execute_tools(output.tool_calls)
        current_input = current_input + tool_results
        continue
        
    final_output = output
```

### 2. Filtros de Handoff

Los filtros de handoff te permiten controlar qué información se transfiere durante un handoff:

```python
def memory_handoff_filter(input_data: HandoffInputData) -> HandoffInputData:
    # Personaliza qué información se transfiere al siguiente agente
    return HandoffInputData(
        input_history=input_data.input_history,
        pre_handoff_items=input_data.pre_handoff_items,
        new_items=input_data.new_items
    )
```

### 3. Contexto Compartido

El sistema de contexto facilita compartir estado entre agentes:

```python
# Creas un contexto compartido
context = ChatMemoryContext()

# Lo pasas al Runner.run() para que esté disponible para todos los agentes en la cadena
result = await Runner.run(
    triage_agent,
    input=user_input,
    context=context,  # Disponible para todos los agentes en la cadena
    run_config=run_config
)
```

## El Ciclo de Vida de una Ejecución

El ciclo de vida completo de una ejecución orquestada funciona así:

1. **Inicialización**: 
   - Creas los agentes especializados
   - Configuras quién puede hacer handoffs a quién
   - Preparas el contexto compartido

2. **Ejecución**:
   - Llamas a `Runner.run()` con el agente inicial
   - El Runner inicia el bucle de ejecución del agente

3. **Bucle del agente**:
   - El LLM analiza la entrada y genera una respuesta
   - Si decide usar una herramienta, el Runner ejecuta la herramienta y le devuelve los resultados al LLM
   - Si decide hacer un handoff, el Runner transfiere el control al nuevo agente
   - Si genera una respuesta final, el bucle termina

4. **Handoffs**:
   - Cuando ocurre un handoff, el contexto se transfiere al nuevo agente
   - Los filtros de handoff permiten personalizar qué información se transfiere
   - El nuevo agente retoma desde donde el anterior lo dejó

5. **Finalización**:
   - Después de completar todas las interacciones, el Runner devuelve un `RunResult`
   - El resultado contiene la salida final y toda la información sobre la ejecución

## Patrones de Orquestramiento Avanzados

El SDK soporta patrones avanzados como:

### Orquestramiento jerárquico

Un agente principal que delega a sub-agentes especializados, que a su vez pueden delegar a otros agentes más especializados.

```
Agente Principal
├── Sub-Agente A
│   ├── Agente Especializado 1
│   └── Agente Especializado 2
└── Sub-Agente B
```

### Orquestramiento con retroalimentación

Un agente genera contenido, otro lo evalúa, y si no cumple los criterios, se devuelve al primero para mejorarlo.

```python
while True:
    content = await Runner.run(content_agent, prompt)
    evaluation = await Runner.run(evaluator_agent, content.final_output)
    if evaluation.final_output == "APPROVED":
        break
    prompt = f"Mejora esto: {content.final_output}. Feedback: {evaluation.final_output}"
```

### Orquestramiento paralelo

Ejecutar múltiples agentes simultáneamente y combinar sus resultados.

```python
tasks = [
    Runner.run(research_agent, query),
    Runner.run(facts_agent, query),
    Runner.run(creativity_agent, query)
]
results = await asyncio.gather(*tasks)
```

## Ventajas del Orquestramiento en el SDK

Este enfoque de orquestramiento ofrece varias ventajas:

1. **Especialización**: Cada agente puede optimizarse para una tarea específica
2. **Modularidad**: Fácil añadir, quitar o reemplazar agentes
3. **Escalabilidad**: Sistemas complejos pueden construirse a partir de agentes simples
4. **Mantenibilidad**: Cada agente tiene un propósito claro y acotado
5. **Flexibilidad**: Combina enfoques dirigidos por IA y programáticos según necesites

## Consideraciones de Diseño

Al diseñar un sistema orquestado de agentes, considera:

1. **Granularidad**: ¿Qué tan especializados deben ser tus agentes?
2. **Control vs. Autonomía**: ¿Cuánto control programático necesitas vs. permitir que el LLM decida?
3. **Estado compartido**: ¿Qué información deben compartir los agentes entre sí?
4. **Ciclos de decisión**: ¿Quién decide cuándo termina una tarea y comienza otra?
5. **Manejo de errores**: ¿Cómo manejar casos donde un agente falla o no puede completar su tarea?

El SDK de OpenAI Agents proporciona las herramientas para implementar estos patrones de orquestramiento de manera elegante y eficiente, permitiéndote construir sistemas complejos de agentes que trabajan juntos sin problemas. 