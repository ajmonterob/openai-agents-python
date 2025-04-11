"""
Visualización de Agentes - Math Tutor

Este script genera una representación del flujo de agentes en nuestro tutor de matemáticas,
mostrando la estructura de handoffs entre el orquestador y el agente de diagnóstico.

Intenta generar gráficos con Graphviz si está disponible, o usa ASCII art como fallback.

Autor: Andres Montero
Fecha: Marzo 2024
"""

from dataclasses import dataclass, field
from typing import List
from agents import Agent
import importlib.util
import sys
import os

# Crear directorio para visualizaciones
VISUALIZATION_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "visualizations")
os.makedirs(VISUALIZATION_DIR, exist_ok=True)

# Importar el módulo usando importlib
def import_from_file(module_name, file_path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Ruta al archivo del tutor de matemáticas
tutor_file = os.path.join(os.path.dirname(__file__), "09_chat_agent_math_tutor.py")
math_tutor = import_from_file("math_tutor", tutor_file)

def visualize_agent_flow(output_file="math_tutor_flow", use_graphviz=True):
    """
    Genera una visualización del flujo de agentes, intentando usar Graphviz
    y utilizando ASCII como fallback.
    
    Args:
        output_file (str): Nombre base del archivo (sin extensión)
        use_graphviz (bool): Si es True, intenta usar Graphviz
        
    Returns:
        tuple: (ruta_completa, usado_graphviz)
    """
    # Rutas absolutas para los archivos
    graphviz_file = os.path.join(VISUALIZATION_DIR, f"{output_file}")
    ascii_file = os.path.join(VISUALIZATION_DIR, f"{output_file}.txt")
    
    # Crear agentes
    try:
        orchestrator = math_tutor.create_orchestrator_agent()
        diagnostic = math_tutor.create_diagnostic_agent()
        
        # Configurar los handoffs
        orchestrator.handoffs = [diagnostic]
        diagnostic.handoffs = [orchestrator]
    except Exception as e:
        print(f"Error al crear agentes: {e}")
        orchestrator = None
        diagnostic = None
    
    # Intentar usar Graphviz primero
    if use_graphviz:
        try:
            from graphviz import Digraph
            from agents.extensions.visualization import draw_graph
            
            print("Creando visualización con Graphviz...")
            
            if orchestrator and diagnostic:
                # Método 1: Usar draw_graph de agents.extensions.visualization
                try:
                    print("Intentando generar con draw_graph...")
                    # Modificamos el flujo para evitar recursión
                    # Guardamos el handoff original
                    orig_diagnostic_handoffs = diagnostic.handoffs
                    diagnostic.handoffs = []
                    
                    # Ahora generamos el grafo
                    graph = draw_graph(orchestrator, filename=graphviz_file)
                    
                    # Restauramos el handoff
                    diagnostic.handoffs = orig_diagnostic_handoffs
                    
                    # Guardamos sin intentar view() para evitar error de xdg-open
                    # graph.view(cleanup=True)
                    graph.render(cleanup=True)
                    
                    result_file = f"{graphviz_file}.pdf"
                    print(f"Visualización generada con éxito en: {result_file}")
                    return result_file, True
                except Exception as e:
                    print(f"Error con draw_graph: {e}")
            
            # Método 2: Crear nuestro propio grafo con Digraph
            print("Generando visualización manual con Digraph...")
            dot = Digraph(comment='Math Tutor Agent Flow')
            
            # Configuración global
            dot.attr('node', shape='box', style='filled', color='black')
            dot.attr('graph', rankdir='TB')  # Dirección de arriba a abajo
            
            # Nodos
            dot.node('start', '__start__', shape='diamond', fillcolor='lightgreen')
            dot.node('orchestrator', 'Orchestrator', shape='box', fillcolor='yellow')
            dot.node('diagnostic', 'DiagnosticAgent', shape='box', fillcolor='yellow')
            
            # Handoffs
            dot.edge('start', 'orchestrator')
            dot.edge('orchestrator', 'diagnostic', label='handoff')
            dot.edge('diagnostic', 'orchestrator', label='handoff back')
            
            # Guardar el gráfico sin forzar la visualización
            result_file = dot.render(graphviz_file, view=False, format='png', cleanup=True)
            print(f"Visualización manual generada con éxito en: {result_file}")
            return result_file, True
            
        except Exception as e:
            print(f"No se pudo generar visualización con Graphviz: {e}")
            print("Recurriendo a visualización ASCII...")
    
    # Si Graphviz falló o no se solicitó, usamos ASCII
    ascii_graph = create_agent_ascii_graph()
    
    # Guardar ASCII en archivo
    with open(ascii_file, 'w') as f:
        f.write(ascii_graph)
    
    print(f"Visualización ASCII guardada en: {ascii_file}")
    return ascii_file, False

def create_agent_ascii_graph():
    """
    Genera una representación ASCII del flujo de agentes.
    
    Returns:
        str: Representación ASCII del grafo.
    """
    print("Creando representación ASCII de agentes...")
    
    ascii_graph = """
    === Math Tutor Agent Flow ===
    
         +-------------+
         |  __start__  |
         +------+------+
                |
                ▼
       +------------------+
       |   Orchestrator   |
       +--------+---------+
                |
                | handoff
                ▼
       +------------------+
       |  DiagnosticAgent |
       +--------+---------+
                |
                | handoff back
                ▼
       +------------------+
       |   Orchestrator   |
       +------------------+
    
    === End of Agent Flow ===
    """
    
    print("Representación ASCII de agentes creada.")
    
    return ascii_graph

def create_system_ascii_graph():
    """
    Genera una representación ASCII del sistema completo.
    
    Returns:
        str: Representación ASCII del grafo.
    """
    print("Creando representación ASCII del sistema completo...")
    
    ascii_graph = """
    === Math Tutor System Architecture ===
    
    +----------+     mensaje     +---------------+
    | Usuario  +---------------->| Orquestador   |
    +----------+                 +-------+-------+
        ^                                |
        |                                | handoff
        |                                ▼
        |                        +---------------+
        |                        | Diagnóstico   |
        |                        +-------+-------+
        |                                |
        |  explicación                   | transferencia
        +--------------------------------+
    
    === Componentes del Sistema ===
    
    +---------------+      +-----------------+      +----------------+
    | ChatMemory    |<---->| Orquestador     |<---->| Diagnóstico    |
    | Context       |      | - Explica       |      | - Hace         |
    | - Historial   |      |   conceptos     |      |   preguntas    |
    | - Tema        |      | - Retoma control|      | - Transfiere   |
    | - Nivel       |      +-----------------+      +----------------+
    +-------+-------+
            |
            ▼
    +---------------+
    | Tracing       |
    | - Spans       |
    | - Grupos      |
    | - Metadatos   |
    +---------------+
    
    === End of System Architecture ===
    """
    
    return ascii_graph

def create_conversation_ascii_graph():
    """
    Genera una representación ASCII del flujo de conversación.
    
    Returns:
        str: Representación ASCII del grafo.
    """
    print("Creando representación ASCII del flujo de conversación...")
    
    ascii_graph = """
    === Flujo de Conversación del Tutor de Matemáticas ===
    
    Usuario: "Hola, necesito ayuda con multiplicación"
                          |
                          ▼
    Diagnóstico: "¿En qué tema ocupas ayuda hoy?"
                          |
                          ▼
    Usuario: "Multiplicación"
                          |
                          ▼
    Diagnóstico: "¿Qué sabes sobre el tema?"
                          |
                          ▼
    Usuario: "Solo sé las tablas"
                          |
                          ▼
    Diagnóstico: "He completado el diagnóstico inicial. 
                  Ahora mi colega te ayudará."
                          |
                          ▼
    Orquestador: [Explicación detallada de multiplicación]
                          |
                          ▼
    Usuario: "¿Podrías darme un ejemplo?"
                          |
                          ▼
    Orquestador: [Ejemplo de multiplicación]
    
    === End of Conversation Flow ===
    """
    
    return ascii_graph

def save_to_file(content, filename):
    """
    Guarda el contenido en un archivo.
    
    Args:
        content (str): Contenido a guardar
        filename (str): Nombre del archivo
    
    Returns:
        str: Ruta completa al archivo
    """
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Guardado en: {filename}")
    return os.path.abspath(filename)

if __name__ == "__main__":
    import sys
    import argparse
    
    # Configurar argumentos
    parser = argparse.ArgumentParser(description="Generador de visualizaciones del Tutor de Matemáticas")
    parser.add_argument("--no-graphviz", action="store_true", help="No intentar usar Graphviz, solo ASCII")
    parser.add_argument("--dir", default=VISUALIZATION_DIR, help="Directorio para guardar visualizaciones")
    args = parser.parse_args()
    
    # Configurar directorio
    VISUALIZATION_DIR = args.dir
    os.makedirs(VISUALIZATION_DIR, exist_ok=True)
    
    # Opciones por defecto
    use_graphviz = not args.no_graphviz
    
    print("=== Visualización del Tutor de Matemáticas ===")
    print(f"Usando Graphviz: {use_graphviz}")
    print(f"Directorio de salida: {VISUALIZATION_DIR}")
    print("=" * 45)
    
    # Generar visualizaciones
    agent_flow_file, used_graphviz = visualize_agent_flow("math_tutor_flow", use_graphviz)
    
    # Guardar en archivos las otras representaciones ASCII 
    system_file = os.path.join(VISUALIZATION_DIR, "math_tutor_complete.txt")
    conversation_file = os.path.join(VISUALIZATION_DIR, "math_tutor_conversation.txt")
    
    save_to_file(create_system_ascii_graph(), system_file)
    save_to_file(create_conversation_ascii_graph(), conversation_file)
    
    print("\n=== Visualización completada ===")
    if used_graphviz:
        print("✅ Visualización con Graphviz generada correctamente.")
        print(f"📂 Archivo principal: {agent_flow_file}")
    else:
        print("⚠️ No se pudo usar Graphviz, se usó ASCII como alternativa.")
        print("📝 Para ver visualizaciones gráficas, instalar Graphviz")
        
    print(f"📂 Todos los archivos guardados en: {VISUALIZATION_DIR}")
    print(f"📑 Sistema completo: {system_file}")
    print(f"📑 Flujo de conversación: {conversation_file}") 