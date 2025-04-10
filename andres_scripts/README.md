# Scripts de Aprendizaje del SDK de OpenAI Agents

Este directorio contiene una serie de scripts desarrollados durante el proceso de aprendizaje del SDK de OpenAI Agents. Los scripts están organizados cronológicamente, mostrando la evolución del aprendizaje desde los conceptos básicos hasta implementaciones más complejas.

## Organización de Scripts y Lecciones Aprendidas

### Fase 1: Primeros Pasos con el SDK

### 1. 01_test_agent.py
**Objetivo:** Primer contacto con el SDK y pruebas iniciales.
- Creación básica de un agente
- Pruebas de comunicación simple
- Entendimiento de la estructura básica del SDK

### 2. 02_test_tools.py
**Objetivo:** Exploración de herramientas y funcionalidades.
- Implementación de herramientas básicas
- Pruebas de integración de herramientas con agentes
- Comprensión del sistema de tools del SDK

### 3. 03_chat_agent_basic.py
**Objetivo:** Primera implementación de un chat funcional.
- Chat básico sin memoria
- Interacción simple usuario-agente
- Base para futuras implementaciones

### Fase 2: Implementaciones Avanzadas

### 4. chat_agent_programmatic.py
**Objetivo:** Implementación básica de un chat agent con control programático.
- Control manual del flujo de la conversación
- Sin sistema de memoria o contexto
- Ejemplo básico de uso del SDK

### 5. chat_agent_sequential_handoff.py
**Objetivo:** Implementación usando el sistema de handoff del SDK.
- Uso del sistema de handoff nativo del SDK
- Agente de triaje que decide el siguiente agente
- Demostración de cómo pasar el control entre agentes

### 6. chat_agent_sequential_programmatic.py
**Objetivo:** Control programático de la secuencia de agentes.
- Control manual de la secuencia de agentes
- Implementación de lógica de cambio de idioma
- Ejemplo de cómo manejar el flujo sin handoffs
- [Ver lecciones aprendidas](lessons/sequential_programmatic_lessons.md)

### Fase 3: Sistemas de Memoria y Contexto

### 7. chat_agent_with_memory.py
**Objetivo:** Implementación de sistema de memoria.
- Introducción de contexto compartido
- Mantenimiento de historia de conversación
- Ejemplo de cómo los agentes pueden acceder al historial

### 8. chat_agent_with_unified_memory.py
**Objetivo:** Sistema de memoria unificado y mejorado.
- Versión mejorada del sistema de memoria
- Mejor manejo del contexto compartido
- Implementación más robusta de la historia de conversación
- [Ver lecciones aprendidas](lessons/unified_memory_lessons.md)

## Documentación de Lecciones

Cada script importante tiene su propio archivo de lecciones aprendidas en la carpeta `lessons/`. Estos archivos contienen:
- Errores encontrados y sus soluciones
- Mejores prácticas descubiertas
- Ejemplos de código antes y después
- Consideraciones de diseño
- Problemas comunes y cómo evitarlos

## Progresión del Aprendizaje

1. **Fase Inicial (Scripts 1-3):**
   - Familiarización con el SDK
   - Pruebas básicas y experimentación
   - Entendimiento de conceptos fundamentales

2. **Fase de Control de Flujo (Scripts 4-6):**
   - Diferentes aproximaciones al control de flujo
   - Handoff vs control programático
   - Manejo de múltiples agentes

3. **Fase de Gestión de Estado (Scripts 7-8):**
   - Implementación de memoria
   - Manejo de contexto
   - Sistemas robustos de estado

## Lecciones Generales Aprendidas

### Control de Flujo
- Comparación entre control programático vs sistema de handoff
- Ventajas y desventajas de cada aproximación
- Cuándo usar cada método

### Manejo de Memoria
- Diferentes aproximaciones al manejo del contexto
- Evolución desde sin memoria hasta memoria unificada
- Mejores prácticas para mantener el estado

### Diseño de Agentes
- Separación de responsabilidades
- Comunicación entre agentes
- Manejo de instrucciones y comportamiento

### Debugging y Monitoreo
- Implementación de sistemas de debug
- Seguimiento del estado del sistema
- Herramientas para diagnóstico

## Uso de los Scripts

Cada script puede ser ejecutado independientemente:
```bash
python andres_scripts/[nombre_del_script].py
```

Requisitos:
- Python 3.9+
- SDK de OpenAI Agents
- Variable de entorno OPENAI_API_KEY configurada

## Notas Adicionales

- Los scripts están ordenados cronológicamente para mostrar la progresión del aprendizaje
- Cada script incluye comentarios explicativos
- Se recomienda revisar los scripts en el orden listado para mejor comprensión
- Los ejemplos incluyen casos de uso prácticos y manejo de errores
- Revisa los archivos de lecciones aprendidas para una comprensión más profunda 