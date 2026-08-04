# CodeAtlas AI

Backend open source para analizar repositorios Python y generar una representación técnica verificable de su estructura y dependencias.

## Estado actual

MVP actual: análisis estático local, arquitectura por componentes, grafo Mermaid y exportación Word editable. La interpretación con OpenAI es opcional y se activa solo cuando el usuario lo solicita.

## Comandos disponibles

```powershell
codeatlas inspect .\mi-proyecto
codeatlas analyze .\mi-proyecto --output .\analysis.json
codeatlas dependencies .\mi-proyecto --output .\dependencies-por-paquete.mmd
codeatlas dependencies .\mi-proyecto --package src/graph --output .\graph-dependencias.mmd
codeatlas dependencies .\mi-proyecto --level file --package src/graph --output .\graph-archivos.mmd
codeatlas classes .\mi-proyecto --package src/graph --output .\graph-clases.mmd
codeatlas classes .\mi-proyecto --focus NombreDeClase --output .\clase-detalle.mmd
codeatlas report .\mi-proyecto --output .\informe.docx
codeatlas report .\mi-proyecto --ai --output .\informe-con-ia.docx
```

`dependencies` genera por defecto un resumen técnico de imports por paquete y oculta pruebas. Usa `--package` para explorar una zona del repositorio y `--level file` para sus archivos. En la vista por archivo, `--package` agrupa visualmente quién usa el área, el área seleccionada y sus dependencias directas; los nombres se acortan para reducir cruces. `classes` admite `--package`, `--focus` y `--limit` para evitar diagramas imposibles de leer. El comando histórico `graph` conserva la salida técnica por archivo; no debe usarse como diagrama de arquitectura.

`report` concentra su lectura principal en código de producción: resume pruebas e inicializadores, limita el detalle por módulo y distingue imports de biblioteca estándar, terceros e internos sin resolver. `report --ai` lee exclusivamente `OPENAI_API_KEY` desde el entorno. Sin esa opción, CodeAtlas no envía archivos ni código fuera del equipo. El análisis de IA recibe evidencia seleccionada y fragmentos limitados de módulos relevantes; no utiliza agentes múltiples.

```powershell
$env:OPENAI_API_KEY = "tu-clave"
# Opcional: cambia el modelo sin guardar la clave en un archivo.
$env:CODEATLAS_OPENAI_MODEL = "gpt-5.6-terra"
```

## Desarrollo local

Requiere Python 3.12 o superior.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
pytest
ruff check .
mypy src
```

## Arquitectura

```text
CLI → Application Service → Scanner → AST Parser → Dependency Resolver → Graph / JSON
```
