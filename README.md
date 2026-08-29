# AI for the public good — corpus y pipeline de análisis
### Análisis de discurso · GDS/DSIT, Reino Unido · enero 2024 – julio 2026

Pipeline de apoyo a la disertación de Frida sobre "AI for the public good" como
imaginario sociotécnico en el discurso del gobierno del Reino Unido sobre IA en
servicios públicos, anclado en el Government Digital Service.

**Principio rector: el LLM localiza y extrae; Frida interpreta y consolida.**
Ningún resultado interpretativo es final hasta su validación (ver checkpoints).

- **Diseño completo y restricciones (SO1/SO2/SO3):** [PLAN.md](PLAN.md)
- **Guía de interpretación de cada entregable y supuestos:** [interpretacion.html](interpretacion.html)
- **Hub consolidado (corpus + entregables + alta de documentos):** [index.html](index.html)

## Arranque rápido

```bash
# hub local con alta incremental de documentos (formulario "Agregar documento")
.venv/bin/python scripts/serve_site.py
# → http://localhost:8765
```

Requisitos: Python 3.14 (venv en `.venv/`, ya provisionado), [Ollama](https://ollama.com)
corriendo en `localhost:11434` con sesión de Ollama Cloud (modelo LLM) y
`embeddinggemma` local (embeddings).

## Estructura

```
data/manifest.csv        corpus congelado v1 (35 docs) + atributos; append-only (v2+ = altas)
data/raw/                originales descargados + meta por doc (fuera de git; snapshots en archive.org)
data/text/               texto estructurado por doc (bloques: title/pillar/heading/body/quotation)
coding/lexicon_v1.yaml   variantes del término (nominal / variante / distributivo) — versionado
coding/units.jsonl       53 unidades de codificación (retrieval: lexicon | semantic | full_short_doc)
coding/prompts/          prompts de las 11 preguntas + perfil de documento, versionados
coding/model_eval/       evaluación de modelos Ollama y decisión documentada
coding/round1/           salida cruda de la Ronda 1 (JSONL por doc, con run metadata)
coding/validation/       muestra para doble codificación de Frida + acuerdo
coding/guidebook_draft.yaml  clusters candidatos de sub-códigos (DRAFT hasta que Frida los nombre)
analysis/networks/       red intertextual v0 (JSON con evidencia) + mapa interactivo
analysis/queries/        conteos del término, queries (zero-count, GDS-tier), ecos por familia
analysis/metaphors_report.md  metáforas más frecuentes con sugerencia fuente/meta (a validar)
```

## Scripts (en orden de pipeline)

| Script | Fase | Qué hace |
|---|---|---|
| `01_manifest.py` | 0 | Excel de selección → `data/manifest.csv` |
| `02a/02b_fetch_*.py` | 1 | Descarga y extracción estructurada (gov / empresas) |
| `02c_archive_snapshots.py` | 1 | Snapshots en web.archive.org |
| `03_qa_merge.py` | 1 | QA de extracción + fusión de metadatos al manifest |
| `04_segment.py` | 2 | Unidades de codificación + término/variantes + recuperación semántica |
| `05_code.py` | 4 | Ronda 1 con Ollama (11 preguntas × unidad; `--doc` para uno solo) |
| `06_consolidate.py` | 5 | Agrupación de respuestas → borrador de guidebook |
| `06_network_v0.py` | 6 | Red de referencias explícitas (alias de título + regla MoU) |
| `07_echo.py` / `07b_queries.py` | 6 | Echo-phrases por familia MoU + queries |
| `08_build_site.py` | — | Regenera `index.html` desde los datos |
| `add_document.py` | 7 | Alta incremental: checklist de admisión → fetch → recálculo |
| `serve_site.py` | — | Hub en localhost:8765 con el formulario de alta |

Todo corre con `.venv/bin/python scripts/<script>.py`.

## Checkpoints de Frida (decisiones humanas, no delegables)

1. Lexicón de variantes (`coding/lexicon_v1.yaml`) — aprobar/ampliar.
2. `gds_tier` — la asignación actual es automática provisional (columna `gds_tier_source`).
3. Muestra de validación (`coding/validation/sample_for_frida.csv`) — doble codificación
   y reporte de acuerdo antes de dar por buena la Ronda 1.
4. Guidebook (`coding/guidebook_draft.yaml`) — nombrar/fusionar/rechazar sub-códigos.
5. Metáforas (`analysis/metaphors_report.md`) — validar dominios fuente/meta sugeridos.
6. Altas de documentos (Fase 7) — confirmar el checklist de admisión de cada URL nueva.

## Decisiones registradas

- Corpus v1 = 35 documentos (el rango decidido del Excel contiene una fila vacía; corte
  en la fila 38, marcador "EITHER BRING"). El doc `CONTEXT_` (AI Opportunities Action
  Plan) **entra al corpus** con `Speaker=External_adviser` (decisión 2026-08-29).
- LEGITIMATION (van Leeuwen) descartado: excede el marco teórico de la matriz.
- `data/raw/` fuera de git; permanencia vía copias locales + archive.org (33/35).
- METAPHOR anclado en Lakoff & Johnson (1980) + MIP; los dominios que produce el
  pipeline son sugerencias.
