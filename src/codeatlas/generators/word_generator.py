"""Editable Word report generation from deterministic repository analysis."""

from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION_START
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

from codeatlas.exceptions import OutputAlreadyExistsError
from codeatlas.graph import DependencyGraph
from codeatlas.models import ArchitectureNarrative, FileAnalysis, FunctionInfo, RepositoryAnalysis

_BLUE = RGBColor(46, 116, 181)
_DARK_BLUE = RGBColor(31, 77, 120)
_MUTED = RGBColor(89, 89, 89)
_HEADER_FILL = "F2F4F7"


class WordReportGenerator:
    """Create a concise, editable architecture report in DOCX format."""

    def write(
        self,
        analysis: RepositoryAnalysis,
        output_path: Path,
        force: bool = False,
        narrative: ArchitectureNarrative | None = None,
    ) -> Path:
        output = output_path.expanduser().resolve()
        if output.exists() and not force:
            raise OutputAlreadyExistsError(
                f"Output already exists: {output}. Use --force to overwrite it."
            )

        output.parent.mkdir(parents=True, exist_ok=True)
        document = Document()
        self._configure_document(document)
        self._add_cover(document, analysis)
        document.add_page_break()
        self._add_contents(document)
        document.add_section(WD_SECTION_START.NEW_PAGE)
        self._add_footer(document.sections[-1])
        self._add_report(document, analysis, narrative)
        document.save(output)
        return output

    def _configure_document(self, document: Document) -> None:
        section = document.sections[0]
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.75)
        section.left_margin = Inches(0.9)
        section.right_margin = Inches(0.9)

        normal = document.styles["Normal"]
        normal.font.name = "Calibri"
        normal._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
        normal._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
        normal.font.size = Pt(11)
        normal.paragraph_format.space_after = Pt(6)
        normal.paragraph_format.line_spacing = 1.1

        for name, size, color, before, after in (
            ("Heading 1", 16, _BLUE, 16, 8),
            ("Heading 2", 13, _BLUE, 12, 6),
            ("Heading 3", 12, _DARK_BLUE, 8, 4),
        ):
            style = document.styles[name]
            style.font.name = "Calibri"
            style._element.rPr.rFonts.set(qn("w:ascii"), "Calibri")
            style._element.rPr.rFonts.set(qn("w:hAnsi"), "Calibri")
            style.font.size = Pt(size)
            style.font.color.rgb = color
            style.paragraph_format.space_before = Pt(before)
            style.paragraph_format.space_after = Pt(after)

        code_style = document.styles.add_style("CodeAtlas Code", WD_STYLE_TYPE.PARAGRAPH)
        code_style.font.name = "Consolas"
        code_style._element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
        code_style._element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")
        code_style.font.size = Pt(8.5)
        code_style.paragraph_format.space_after = Pt(4)

        for item in document.sections:
            self._add_footer(item)

    def _add_cover(self, document: Document, analysis: RepositoryAnalysis) -> None:
        document.add_paragraph()
        label = document.add_paragraph()
        label.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = label.add_run("CODEATLAS AI")
        run.bold = True
        run.font.size = Pt(12)
        run.font.color.rgb = _BLUE

        title = document.add_paragraph()
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title.paragraph_format.space_before = Pt(75)
        title.paragraph_format.space_after = Pt(10)
        run = title.add_run("Informe de arquitectura")
        run.bold = True
        run.font.size = Pt(30)
        run.font.color.rgb = _DARK_BLUE

        subtitle = document.add_paragraph()
        subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
        subtitle.paragraph_format.space_after = Pt(36)
        run = subtitle.add_run("Análisis estático de repositorio Python")
        run.font.size = Pt(15)
        run.font.color.rgb = _MUTED

        metadata = self._table(document, 3, 2, (Inches(1.6), Inches(4.9)))
        for row, label_text, value in zip(
            metadata.rows,
            ("Proyecto", "Ruta analizada", "Generado"),
            (
                analysis.repository_name,
                analysis.repository_path,
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ),
            strict=True,
        ):
            row.cells[0].text = label_text
            row.cells[1].text = value
            self._shade_cell(row.cells[0], _HEADER_FILL)
            for paragraph in row.cells[0].paragraphs:
                paragraph.runs[0].bold = True

        note = document.add_paragraph()
        note.alignment = WD_ALIGN_PARAGRAPH.CENTER
        note.paragraph_format.space_before = Pt(45)
        note_run = note.add_run(
            "Este informe se genera a partir de la estructura y dependencias detectadas "
            "en el código. No sustituye una revisión humana del dominio de negocio."
        )
        note_run.italic = True
        note_run.font.size = Pt(9.5)
        note_run.font.color.rgb = _MUTED

    def _add_contents(self, document: Document) -> None:
        document.add_heading("Contenido", level=1)
        for item in (
            "1. Como leer este informe",
            "2. Resumen ejecutivo",
            "3. Arquitectura detectada",
            "4. Alcance y evidencia",
            "5. Tecnologias y dependencias externas",
            "6. Recomendaciones iniciales",
            "Anexo tecnico",
        ):
            document.add_paragraph(item)

    def _add_report(
        self,
        document: Document,
        analysis: RepositoryAnalysis,
        narrative: ArchitectureNarrative | None,
    ) -> None:
        document.add_heading("1. Como leer este informe", level=1)
        document.add_paragraph(
            "Los datos detectados proceden del analisis estatico de archivos Python e imports. "
            "Las conclusiones con IA, si existen, se muestran aparte y citan los archivos que las respaldan."
        )
        document.add_heading("2. Resumen ejecutivo", level=1)
        stats = analysis.stats
        document.add_paragraph(
            "CodeAtlas AI revisó la estructura del repositorio y encontró "
            f"{stats.python_files} archivo(s) Python dentro de {stats.files_discovered} archivo(s) "
            "descubierto(s). El resultado sirve como punto de partida para comprender el código, "
            "planear una revisión técnica y detectar zonas que merecen atención."
        )
        summary = self._table(document, 3, 3, (Inches(2.15), Inches(2.15), Inches(2.2)))
        for cell, label, value in zip(
            summary.rows[0].cells,
            ("Estructura", "Código", "Dependencias"),
            (
                f"{stats.files_discovered} archivo(s)",
                f"{stats.classes} clase(s) y {stats.functions} función(es)",
                f"{stats.internal_imports} interna(s) y {stats.external_dependencies} externa(s)",
            ),
            strict=True,
        ):
            cell.text = label
            self._shade_cell(cell, _HEADER_FILL)
            cell.paragraphs[0].runs[0].bold = True
        for cell, value in zip(
            summary.rows[1].cells,
            ("Métodos", "Módulos centrales", "Errores de análisis"),
            strict=True,
        ):
            cell.text = value
            self._shade_cell(cell, "FAFAFA")
            cell.paragraphs[0].runs[0].bold = True
        for cell, value in zip(
            summary.rows[2].cells,
            (
                str(stats.methods),
                str(len(analysis.central_modules)),
                str(stats.files_with_errors),
            ),
            strict=True,
        ):
            cell.text = value

        document.add_heading("3. Arquitectura detectada", level=1)
        self._add_architecture_overview(document, analysis)
        if narrative:
            self._add_ai_narrative(document, narrative)

        document.add_heading("4. Alcance y evidencia", level=1)
        document.add_paragraph(
            "El informe utiliza análisis estático: nombres de archivos y módulos, estructuras Python, "
            "importaciones y relaciones internas. No ejecuta el programa, no inspecciona bases de datos "
            "ni confirma reglas de negocio que no estén expresadas en el código."
        )
        self._add_label_detail_table(
            document,
            (
                ("Repositorio", analysis.repository_name),
                ("Ruta", analysis.repository_path),
                ("Archivos Python", str(stats.python_files)),
                ("Límites", "Solo los archivos que el escáner pudo leer y analizar."),
            ),
        )

        document.add_heading("Arquitectura tecnica y dependencias", level=2)
        if analysis.central_modules:
            document.add_paragraph(
                "Los siguientes módulos son los más conectados dentro del grafo de dependencias. "
                "Conviene revisarlos primero al estudiar el flujo técnico o evaluar cambios:")
            for module in analysis.central_modules:
                document.add_paragraph(module, style="List Bullet")
        else:
            document.add_paragraph(
                "No se detectaron relaciones internas suficientes para identificar módulos centrales."
            )

        if analysis.internal_dependencies:
            table = self._table(document, len(analysis.internal_dependencies) + 1, 3, (Inches(2.15), Inches(2.15), Inches(2.2)))
            self._set_header(table.rows[0].cells, ("Origen", "Destino", "Importación"))
            for row, dependency in zip(table.rows[1:], analysis.internal_dependencies, strict=True):
                row.cells[0].text = dependency.source
                row.cells[1].text = dependency.target
                row.cells[2].text = dependency.imported_module
        else:
            document.add_paragraph("No se detectaron dependencias internas entre los módulos analizados.")

        document.add_heading("5. Tecnologías y dependencias externas", level=1)
        if analysis.external_dependencies:
            document.add_paragraph(
                "Dependencias externas detectadas por los imports. Esta lista no reemplaza un inventario "
                "de paquetes instalado o un archivo de dependencias:")
            for dependency in analysis.external_dependencies:
                document.add_paragraph(dependency, style="List Bullet")
        else:
            document.add_paragraph("No se detectaron dependencias externas en los imports analizados.")

        document.add_heading("6. Recomendaciones iniciales", level=1)
        recommendations = [
            "Validar con el equipo la responsabilidad de los módulos centrales antes de realizar cambios.",
            "Completar docstrings y anotaciones de tipo en las áreas con mayor evolución o riesgo.",
            "Revisar las dependencias externas frente al archivo de paquetes del proyecto.",
            "Usar este informe junto con pruebas y revisión humana; el análisis estático no ejecuta la aplicación.",
        ]
        if analysis.errors:
            recommendations.insert(
                0,
                "Corregir primero los archivos con errores de lectura o sintaxis para obtener una cobertura mayor.",
            )
        for recommendation in recommendations:
            document.add_paragraph(recommendation, style="List Bullet")

        document.add_heading("Anexo técnico", level=1)
        document.add_heading("A. Inventario de archivos", level=2)
        inventory = self._table(document, len(analysis.files) + 1, 5, (Inches(1.6), Inches(1.25), Inches(1.2), Inches(1.2), Inches(1.25)))
        self._set_header(inventory.rows[0].cells, ("Archivo", "Módulo", "Clases", "Funciones", "Estado"))
        for row, file in zip(inventory.rows[1:], analysis.files, strict=True):
            row.cells[0].text = file.path
            row.cells[1].text = file.module_name
            row.cells[2].text = str(len(file.classes))
            row.cells[3].text = str(len(file.functions))
            row.cells[4].text = "Error" if file.syntax_error else "Analizado"

        document.add_heading("B. Detalle de módulos", level=2)
        for file in analysis.files:
            self._add_file_detail(document, file)

        document.add_heading("C. Diagrama ejecutivo Mermaid", level=2)
        document.add_paragraph(
            "Código fuente de una vista reducida: oculta pruebas y archivos de inicialización, agrupa módulos "
            "por carpeta y destaca los nodos más conectados. Puede copiarse a un visor Mermaid para generar una visualización."
        )
        mermaid = DependencyGraph(analysis.files, analysis.internal_dependencies).to_mermaid(
            view="executive", architecture=analysis.architecture
        )
        for line in mermaid.splitlines():
            document.add_paragraph(line, style="CodeAtlas Code")

        document.add_heading("D. Errores y limitaciones", level=2)
        if analysis.errors:
            errors = self._table(document, len(analysis.errors) + 1, 3, (Inches(1.75), Inches(1.3), Inches(3.45)))
            self._set_header(errors.rows[0].cells, ("Archivo", "Tipo", "Detalle"))
            for row, error in zip(errors.rows[1:], analysis.errors, strict=True):
                row.cells[0].text = error.path
                row.cells[1].text = error.kind
                row.cells[2].text = error.message
        else:
            document.add_paragraph("No se registraron errores de lectura ni sintaxis durante el análisis.")
        document.add_paragraph(
            "Limitaciones: el resultado describe el código de forma estática. Las llamadas dinámicas, "
            "configuraciones externas, archivos no Python, comportamiento en ejecución y reglas de negocio "
            "requieren validación adicional."
        )

    def _add_architecture_overview(self, document: Document, analysis: RepositoryAnalysis) -> None:
        document.add_paragraph(
            "Componentes inferidos a partir de rutas, nombres, docstrings, clases y dependencias. "
            "Una relacion A -> B significa que A importa o depende de B."
        )
        components = [item for item in analysis.architecture.components if item.role != "tests"]
        if components:
            table = self._table(
                document, len(components) + 1, 4, (Inches(1.5), Inches(1.0), Inches(1.0), Inches(3.0))
            )
            self._set_header(table.rows[0].cells, ("Componente", "Archivos", "Confianza", "Evidencia"))
            for row, component in zip(table.rows[1:], components, strict=True):
                row.cells[0].text = component.name
                row.cells[1].text = str(len(component.files))
                row.cells[2].text = f"{component.confidence:.0%}"
                row.cells[3].text = "; ".join(component.evidence[:2])
        if analysis.architecture.dependencies:
            document.add_paragraph("Relaciones entre componentes detectadas:")
            for dependency in analysis.architecture.dependencies:
                document.add_paragraph(
                    f"{dependency.source} -> {dependency.target} "
                    f"({dependency.imports_count} import(s); evidencia: "
                    f"{', '.join(dependency.evidence_files)})",
                    style="List Bullet",
                )
        else:
            document.add_paragraph("No se detectaron relaciones entre componentes diferentes.")

    def _add_ai_narrative(
        self, document: Document, narrative: ArchitectureNarrative
    ) -> None:
        document.add_heading("Interpretacion generada por IA (opcional)", level=2)
        document.add_paragraph(
            "Esta seccion es una interpretacion, no un dato comprobado por si sola. "
            "Debe leerse junto con la evidencia indicada."
        )
        document.add_heading("Proposito probable", level=3)
        document.add_paragraph(narrative.purpose)
        if narrative.component_responsibilities:
            document.add_heading("Responsabilidades sugeridas", level=3)
            self._add_label_detail_table(
                document, tuple(sorted(narrative.component_responsibilities.items()))
            )
        for heading, values in (
            ("Flujo principal", narrative.main_flow),
            ("Riesgos iniciales", narrative.risks),
            ("Preguntas abiertas", narrative.open_questions),
        ):
            if values:
                document.add_heading(heading, level=3)
                for value in values:
                    document.add_paragraph(value, style="List Bullet")
        if narrative.evidence:
            document.add_heading("Evidencia citada por la IA", level=3)
            for item in narrative.evidence:
                document.add_paragraph(
                    f"{item.claim} - archivos: {', '.join(item.files)}", style="List Bullet"
                )

    def _add_file_detail(self, document: Document, file: FileAnalysis) -> None:
        document.add_heading(f"Archivo: {file.path}", level=3)
        facts = [
            f"Módulo: {file.module_name}",
            f"Líneas detectadas: {file.line_count}",
            f"Clases: {len(file.classes)}; funciones de módulo: {len(file.functions)}; imports: {len(file.imports)}.",
        ]
        if file.docstring:
            facts.append(f"Descripción declarada: {file.docstring.strip()}")
        if file.syntax_error:
            facts.append(f"Error de sintaxis: {file.syntax_error}")
        for fact in facts:
            document.add_paragraph(fact)

        if file.classes:
            document.add_paragraph("Clases detectadas:")
            for item in file.classes:
                bases = f" ({', '.join(item.bases)})" if item.bases else ""
                document.add_paragraph(f"{item.name}{bases}", style="List Bullet")
                for method in item.methods:
                    document.add_paragraph(
                        self._signature(method), style="List Bullet 2"
                    )
        if file.functions:
            document.add_paragraph("Funciones de módulo detectadas:")
            for function in file.functions:
                document.add_paragraph(self._signature(function), style="List Bullet")
        if file.imports:
            document.add_paragraph("Imports detectados:")
            for item in file.imports:
                names = ", ".join(item.imported_names)
                suffix = f" ({names})" if names else ""
                status = "interna" if item.is_internal else "externa" if item.is_internal is False else "sin resolver"
                document.add_paragraph(f"{item.module}{suffix} - {status}", style="List Bullet")

    def _signature(self, function: FunctionInfo) -> str:
        parameters = []
        for parameter in function.parameters:
            value = parameter.name
            if parameter.annotation:
                value += f": {parameter.annotation}"
            if parameter.default:
                value += f" = {parameter.default}"
            parameters.append(value)
        prefix = "async " if function.is_async else ""
        result = f"{prefix}{function.name}({', '.join(parameters)})"
        if function.return_type:
            result += f" -> {function.return_type}"
        return result

    def _add_label_detail_table(self, document: Document, rows: tuple[tuple[str, str], ...]) -> None:
        table = self._table(document, len(rows), 2, (Inches(1.85), Inches(4.65)))
        for row, (label, value) in zip(table.rows, rows, strict=True):
            row.cells[0].text = label
            row.cells[1].text = value
            self._shade_cell(row.cells[0], _HEADER_FILL)
            row.cells[0].paragraphs[0].runs[0].bold = True

    def _table(self, document: Document, rows: int, columns: int, widths: tuple[Inches, ...]):
        table = document.add_table(rows=rows, cols=columns)
        table.style = "Table Grid"
        table.autofit = False
        for row in table.rows:
            for cell, width in zip(row.cells, widths, strict=True):
                cell.width = width
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
                self._set_cell_margins(cell)
        return table

    def _set_header(self, cells: tuple | list, values: tuple[str, ...]) -> None:
        for cell, value in zip(cells, values, strict=True):
            cell.text = value
            self._shade_cell(cell, _HEADER_FILL)
            cell.paragraphs[0].runs[0].bold = True

    def _shade_cell(self, cell, fill: str) -> None:
        properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:fill"), fill)
        properties.append(shading)

    def _set_cell_margins(self, cell) -> None:
        properties = cell._tc.get_or_add_tcPr()
        margins = properties.first_child_found_in("w:tcMar")
        if margins is None:
            margins = OxmlElement("w:tcMar")
            properties.append(margins)
        for side in ("top", "start", "bottom", "end"):
            node = margins.find(qn(f"w:{side}"))
            if node is None:
                node = OxmlElement(f"w:{side}")
                margins.append(node)
            node.set(qn("w:w"), "80" if side in {"top", "bottom"} else "120")
            node.set(qn("w:type"), "dxa")

    def _add_footer(self, section) -> None:
        footer = section.footer
        paragraph = footer.paragraphs[0]
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run("CodeAtlas AI | Informe generado automáticamente")
        run.font.size = Pt(8)
        run.font.color.rgb = _MUTED
