# Lecciones Aprendidas: Chat Secuencial con Múltiples Agentes

## 1. Errores de Programación Corregidos

### a) Error en el Manejo del Contexto

**Error Original:**
```python
def create_spanish_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        instructions=lambda context: f"""
        Historia de la conversación:
        {context.get_history()}  # ❌ Error: context es un RunContextWrapper
        """
    )
```

**Solución:**
```python
def create_spanish_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        instructions=lambda context_wrapper, agent: f"""
        Historia de la conversación:
        {context_wrapper.context.get_history()}  # ✅ Correcto: accedemos al contexto real
        """
    )
```

### b) Error en la Función Lambda

**Error Original:**
```python
instructions=lambda context: f"""  # ❌ Error: falta el parámetro agent
    Eres un asistente en español.
    {context.get_history()}
"""
```

**Solución:**
```python
instructions=lambda context_wrapper, agent: f"""  # ✅ Correcto: incluye ambos parámetros
    Eres un asistente en español.
    {context_wrapper.context.get_history()}
"""
```

### c) Error en el Conteo de Respuestas

**Error Original:**
```python
@dataclass
class ChatMemoryContext:
    response_count: int = 0  # ❌ Error: un solo contador no distingue idiomas

    def get_response_phase(self) -> str:
        if self.response_count < 2:
            return "spanish"
        elif self.response_count < 4:
            return "english"
        return "limit_reached"
```

**Solución:**
```python
@dataclass
class ChatMemoryContext:
    spanish_responses: int = 0  # ✅ Correcto: contadores separados
    english_responses: int = 0

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
```

## 2. Aprendizajes sobre el SDK

### a) Manejo del Contexto

**Ejemplo de Implementación Correcta:**
```python
@dataclass
class ChatMemoryContext:
    history: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        self.history.append(f"{role}: {content}")

    def get_history(self) -> str:
        return "\n".join(self.history)

# Uso en el agente
def create_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        instructions=lambda context_wrapper, agent: f"""
        {context_wrapper.context.get_history()}
        """
    )
```

### b) Instrucciones Dinámicas

**Ejemplo de Instrucciones Efectivas:**
```python
def create_english_agent() -> Agent[ChatMemoryContext]:
    return Agent[ChatMemoryContext](
        name="English Assistant",
        instructions=lambda context_wrapper, agent: f"""
        You MUST ALWAYS respond in English.
        You CANNOT switch to Spanish under any circumstances.
        Even if the user writes in Spanish, you MUST respond in English.
        
        Conversation history:
        {context_wrapper.context.get_history()}
        """
    )
```

## 3. Mejoras en la Experiencia de Usuario

### a) Mensajes de Debug

**Implementación de Debug:**
```python
async def chat():
    while True:
        phase = context.get_response_phase()
        selected_agent = spanish_agent if phase == "spanish" else english_agent
        
        print(f"\n[DEBUG] Agente seleccionado: {selected_agent.name}")
        print(f"[DEBUG] Fase actual: {phase}")
        print(f"[DEBUG] Respuestas en español: {context.spanish_responses}")
        print(f"[DEBUG] Respuestas en inglés: {context.english_responses}")
```

### b) Instrucciones Reforzadas

**Evolución de las Instrucciones:**

```python
# Versión 1 (Débil)
instructions = """
You are an English assistant.
Please respond in English.
"""

# Versión 2 (Mejorada)
instructions = """
You are an English assistant.
Always respond in English.
"""

# Versión Final (Robusta)
instructions = """
You are an English assistant.
You MUST ALWAYS respond in English.
You CANNOT switch to Spanish under any circumstances.
Even if the user writes in Spanish, you MUST respond in English.
If the user asks why you're speaking English, explain that you are the English assistant.
"""
```

## 4. Lecciones sobre Diseño

### a) Separación de Responsabilidades

**Estructura Final:**
```python
@dataclass
class ChatMemoryContext:
    # Manejo del estado
    history: List[str] = field(default_factory=list)
    spanish_responses: int = 0
    english_responses: int = 0

def create_spanish_agent():
    # Responsabilidad: respuestas en español
    return Agent[ChatMemoryContext](...)

def create_english_agent():
    # Responsabilidad: respuestas en inglés
    return Agent[ChatMemoryContext](...)

async def chat():
    # Control de flujo principal
    context = ChatMemoryContext()
    while True:
        phase = context.get_response_phase()
        selected_agent = spanish_agent if phase == "spanish" else english_agent
        # ... ejecución del agente
```

## 5. Errores de Diseño Inicial

### Error en el Control de Idioma

**Diseño Original (Problemático):**
```python
# ❌ Error: No hay control estricto del idioma
async def chat():
    while True:
        if response_count < 2:
            # Usar español
            result = await spanish_agent.run(input)
        else:
            # Usar inglés
            result = await english_agent.run(input)
```

**Diseño Final (Robusto):**
```python
# ✅ Correcto: Control preciso del idioma y estado
async def chat():
    context = ChatMemoryContext()
    while True:
        phase = context.get_response_phase()
        if phase == "limit_reached":
            break
            
        selected_agent = spanish_agent if phase == "spanish" else english_agent
        result = await Runner.run(
            selected_agent,
            user_input,
            context=context
        )
        context.increment_language_count(phase)
```

## Conclusiones

1. **Importancia del Tipado y Contexto:**
   - Usar tipos correctos para el contexto
   - Acceder al contexto a través del wrapper adecuado
   - Mantener la coherencia en el manejo del estado

2. **Control de Flujo:**
   - Separar responsabilidades claramente
   - Mantener contadores precisos
   - Implementar lógica de control robusta

3. **Debugging:**
   - Agregar información de debug desde el principio
   - Monitorear el estado del sistema
   - Facilitar la identificación de problemas

4. **Instrucciones Claras:**
   - Ser específico en las instrucciones
   - Reforzar comportamientos críticos
   - Manejar casos edge explícitamente 