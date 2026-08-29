# Pipeline de análisis de discurso — "AI for the public good"
### GDS / DSIT, enero 2024 – julio 2026 · Corpus congelado v1 (37 documentos)

Este plan operacionaliza el diseño metodológico de `Research_Alignment_Matrix.docx` y
`Document Analysis v1.xlsx`. Dos principios rectores:

1. **El LLM localiza y extrae; Frida interpreta y consolida** (Saldaña 2025:
   codificación provisional guiada por preguntas, no por lista cerrada de códigos).
2. **Los tres objetivos específicos son la restricción dura del pipeline.** Ningún
   componente se construye si no sirve a SO1, SO2 o SO3. Todo output lleva etiqueta
   de objetivo (`so_tags`), y lo que solo valida el método (sin generar hallazgos)
   se marca como QA interno.

---

## Restricción: los tres objetivos y qué componente sirve a cuál

> **Aim.** Analizar cómo el framing de "AI for the public good" funciona como
> imaginario sociotécnico en el discurso del gobierno del Reino Unido sobre IA en
> servicios públicos, anclado en el Government Digital Service.

| Objetivo | Marco teórico (matriz) | Componentes del pipeline que lo sirven |
|---|---|---|
| **SO1.** Examinar el imaginario sociotécnico proyectado bajo la retórica de "AI for the public good" en los textos del GDS. | Jasanoff & Kim (imaginarios); Kaplan (narrativa/trama); Lears (hegemonía) | Codificación de las 7 preguntas (todas aplican a SO1); extractor definicional; comparación cronológica de definiciones; METAPHOR; NARRATIVE_ARC; THREAT_TYPE |
| **SO2.** Rastrear cómo ese imaginario se mueve de declaración de principios a prioridades estratégicas, compromisos de política y reclamaciones de cara al público. | Fairclough (intertextualidad); Jasanoff & Kim; Lears (naturalización) | Red intertextual (familias + referencias + supersession); preguntas MECHANISM, PROJECTED FUTURE, NATURALISED ORDER; atributos Period y AUDIENCE; queries zero-count × Genre; recuperación semántica de la reclamación distributiva; slider temporal de la visualización |
| **SO3.** Analizar la evolución del framing a través de los documentos de partnership entre el departamento y las empresas de IA de frontera. | Hajer (coaliciones discursivas); Lears (naturalización); Fairclough (agent deletion, nominalización, modalidad) | Echo-phrases por familia MoU; AGENCY y MODALITY; comparación intra-familia e inter-familia; preguntas SAFEGUARD, RESPONSIBILITY, ACTANTS; dominios-fuente metafóricos compartidos gobierno↔empresa; query GDS-control × GDSTier |

**Regla de recorte aplicada.** Quedó fuera o degradado todo lo que no mapea:
- **LEGITIMATION (van Leeuwen)** — descartado: amplía el marco teórico más allá de lo
  establecido en la matriz.
- **Detección de comunidades (Leiden) y triangulación por embeddings** — degradados a
  **QA interno**: sirven para verificar que las agrupaciones no son artefacto, pero no
  generan hallazgos propios ni aparecen como resultados.
- "Descubrimiento exploratorio" con embeddings — eliminado como fin en sí mismo; los
  embeddings solo se usan para la recuperación de la reclamación distributiva (SO1/SO2)
  y el QA anterior.

---

## Decisiones ya tomadas

| Decisión | Valor |
|---|---|
| Corpus v1 | Solo filas con decisión tomada en `Official_Document Selection` (antes de la fila "EITHER BRING COHERE..."). Los bloques A/B pendientes NO entran a v1. |
| Fuente de texto | Columna `Link for document` → documento completo. `Exact phrase` solo como verificación cruzada donde exista. |
| LLM | Ollama Cloud. Se evalúan 2–3 modelos sobre una muestra y se elige el mejor (Fase 3). |
| Códigos | Los 7 parent codes de la Tabla 3 + los nodos de la hoja `method`. Nuevos códigos: solo los alineados (ver sección Códigos); Frida decide cuáles entran antes de la corrida. |
| Extensibilidad | Alta incremental de documentos con las reglas de admisión del corpus como filtro (ver Fase 7). |

---

## Estructura del proyecto

```
Tafoya/
├── PLAN.md                       ← este documento
├── data/
│   ├── manifest.csv              ← corpus congelado v1, append-only
│   ├── raw/                      ← PDFs/HTML descargados + snapshot archive.org
│   └── text/                     ← JSON estructurado por documento (secciones jerárquicas)
├── coding/
│   ├── prompts/                  ← un prompt por pregunta, versionados; cada uno declara sus so_tags
│   ├── model_eval/               ← comparación de modelos + decisión documentada
│   ├── round1/                   ← salida cruda del LLM, JSONL por documento
│   ├── validation/               ← muestra codificada a mano + reporte de acuerdo
│   └── guidebook.yaml            ← Ronda 2: sub-códigos consolidados (editado por Frida)
├── analysis/
│   ├── networks/                 ← GraphML + visualización HTML interactiva
│   ├── queries/                  ← las tres queries del plan NVivo (CSV + gráficas)
│   ├── qa/                       ← validaciones internas (no son resultados)
│   └── nvivo/                    ← exports listos para importar a NVivo
└── scripts/
    ├── 01_manifest.py … 07_analyze.py
    └── add_document.py           ← alta incremental con checklist de admisión
```

---

## Fase 0 — Congelar el corpus (manifest)

**Entrada:** hoja `Official_Document Selection`. **Salida:** `data/manifest.csv` con:
`doc_id` (nombre NVivo `YYYY-MM-DD_GENRE_ACTOR_Slug`), `date`, `genre`
(STRAT/MOU/PRGOV/PRCO/BLOG/WMS/REG), `speaker` (valor limpio, columna U), `side`,
`family` (Anthropic/Cohere/OpenAI/DeepMind/ElevenLabs/None), `gds_tier` (T1/T2/T3),
`stage` (1/2), `term_status` (present/variant/absent), `url`, `archive_url`,
`corpus_version` (=1), `is_context` (bool).

Decisiones tomadas (2026-08-29): la fila `CONTEXT_..._AIOpportunitiesActionPlan`
**entra al corpus** codificado con `Speaker = External_adviser`; se crean snapshots
nuevos en archive.org para todo el corpus; repositorio git local con `data/raw/` en
`.gitignore` (originales en disco + archive.org).

Verificaciones (se reportan a Frida, no se resuelven en silencio):
- **Conteo**: confirmar que las filas decididas suman 37; discrepancias se listan.
- `term_status = CHECK` (docs 7, 10): quedan marcados; la Fase 2 los resuelve con el
  texto completo y Frida confirma.
- Links rotos o documentos retirados → `archive_url`.

## Fase 1 — Descarga y archivado

Descarga desde `url`; fallback a web.archive.org donde el documento cambió o fue
retirado (ya ocurrió con el Generative AI Framework); **snapshot nuevo en archive.org
de todo lo que no lo tenga** — protección contra link rot durante la tesis.

Extracción de texto **preservando estructura** (PyMuPDF para PDF con jerarquía de
headings; parsing del DOM para gov.uk/blogs con h1–h4, blockquotes y citas atribuidas).
Cada bloque lleva `structural_position` (title / pillar_name / section_heading / body /
quotation) — el atributo "Phrase position" de la Tabla 4 depende de esto, y la posición
estructural es en sí un hallazgo declarado en la matriz.

## Fase 2 — Segmentación y detección del término *(SO1, SO2)*

Fiel al método declarado: *escaneo completo → codificación detallada de la sección que
contiene el término.*

1. **Lexicón de variantes** versionado (aprobado por Frida): nominal ("public good",
   "the public good", "AI for public good") y distributivo/competidores ("public
   benefit", "public interest", "benefits reach every citizen", "delivers for all",
   "improve people's lives", "working people", "taxpayer") — espejo de los nodos
   `PublicGood_Nominal` / `PublicBenefit_Distributive` y de los 8 nodos de beneficiario.
   Stemming apagado (regla NVivo: no atrapar "goods").
2. Secciones-con-término → cola de codificación detallada. Documentos sin término →
   recuperación semántica (embeddings por párrafo) de la reclamación distributiva, para
   que el conteo-cero venga acompañado de "y en su lugar se dice X" (SO1/SO2). Pasajes
   recuperados por embedding se marcan `retrieval=semantic` (auditable).
3. Embeddings vía Ollama (`nomic-embed-text` o `mxbai-embed-large`; se decide en Fase 3).
   Índice persistente para reuso incremental. **Único uso analítico de embeddings**;
   cualquier otro uso es QA.
4. Actualización automática de `term_status` en el manifest (resuelve los `CHECK`).

## Fase 3 — Evaluación de modelos (Ollama Cloud)

1. Muestra estratificada: ~5 documentos (1 STRAT largo, 1 MoU, 1 PRCO, 1 BLOG, 1 WMS)
   → ~25–40 pasajes.
2. Candidatos: 2–3 modelos grandes del catálogo de Ollama Cloud vigente al correr.
3. Mismo prompt, temperatura 0, JSON forzado, las 7 preguntas por pasaje.
4. Métricas de decisión:
   - **Fidelidad extractiva**: toda cita devuelta existe verbatim en el pasaje
     (verificación automática — el mejor detector de alucinación para esta tarea).
   - Tasa de JSON válido y de "no aplica" correctos.
   - **Acuerdo con Frida** sobre la muestra (o acuerdo inter-modelo + adjudicación de
     Frida en los desacuerdos).
5. Salida: `coding/model_eval/decision.md` — modelo, versión exacta, métricas; texto
   casi directo para el capítulo de métodos.

> Los documentos son públicos: correr en Ollama Cloud no plantea problema de
> confidencialidad; se registra igualmente proveedor, modelo y fecha.

## Fase 4 — Codificación Ronda 1 (LLM)

- **Un prompt por pregunta**, cada uno con: la redacción exacta de la Tabla 3, su fuente
  teórica en una línea, sus `so_tags` según la matriz (BENEFICIARY → SO1/SO2/SO3;
  MECHANISM → SO1/SO2; SAFEGUARD → SO1/SO3; RESPONSIBILITY → SO1/SO3; PROJECTED FUTURE
  → SO1/SO2; ACTANTS → SO1/SO3; NATURALISED ORDER → SO1/SO2), el pasaje y el contexto
  mínimo del documento.
- Salida por pasaje/pregunta: `{doc_id, passage_id, question, so_tags, answer_summary,
  verbatim_quote, applies, confidence, model, prompt_version, run_id, timestamp}`.
- **Extractor definicional** separado (SO1): enunciados donde el documento dice qué
  significa o exige la frase → `definitional_instances.jsonl` con posición estructural.
  El pipeline solo alinea las instancias cronológicamente; la lectura de qué retiene,
  suelta, añade o sustituye cada definición es análisis de Frida (así lo fija la matriz).
- Post-chequeo: toda `verbatim_quote` se valida contra el texto fuente; las que no
  matcheen se marcan y se reintentan o descartan.

**Validación (para el capítulo de métodos):** 15–20% de pasajes, estratificado por
género y familia, doblemente codificado (Frida + LLM); acuerdo por pregunta; los
desacuerdos alimentan máximo una iteración de prompts, luego se congelan.

## Fase 5 — Consolidación Ronda 2 (Frida, con apoyo)

- `06_consolidate.py` agrupa las respuestas por pregunta por similitud semántica y
  presenta cada clúster con sus citas — materia prima para que **Frida nombre los
  sub-códigos** en `guidebook.yaml` (nombre, definición, regla de inclusión/exclusión,
  pasaje ejemplar). Los 8 nodos de beneficiario ya definidos en la hoja `method` entran
  al guidebook tal cual como sub-códigos de BENEFICIARY.
- Pase automático de asignación clúster→sub-código; Frida revisa los casos límite.

## Fase 6 — Análisis: solo salidas mapeadas a objetivos

**A. Red intertextual** *(SO2 — Fairclough)*: nodos = documentos con atributos del
manifest; aristas dirigidas por (i) familia, (ii) referencias explícitas en el texto
(títulos de otros documentos del corpus, enlaces gov.uk entre ellos), (iii) supersession
declarada. Lectura: el trayecto declaración → prioridad → compromiso → reclamación pública.

**B. Echo-phrases** *(SO3 — Hajer)*: n-gramas compartidos (≥6 palabras) entre texto
gubernamental y texto de empresa dentro de cada familia MoU, con quién publicó primero —
evidencia material de préstamo interdiscursivo/coalición. Comparación intra-familia y
entre familias por counterparty, como pide la matriz.

**C. Red temática** *(SO1/SO2)*: bipartita documento↔sub-código, proyectada a
documento–documento ponderada por códigos compartidos, facetada por Period, Speaker,
Family y TermStatus.

**D. Las tres queries del plan NVivo** *(replicadas tal cual)*: zero count × Genre
(SO1/SO2); agencia × Genre — pasiva sin agente vs. agente gubernamental en primera
persona (SO3); PublicGood_Nominal × GDSTier — la query que mata la objeción obvia (SO3).
CSV + gráfica cada una.

**E. Exports NVivo**: pasajes codificados + classification sheet de atributos, en
formato de importación directa.

**F. Reporte de metáforas** *(SO1)*: las expresiones metafóricas más frecuentes del
corpus, y por cada una **una sugerencia de dominio fuente y dominio meta** con su
fórmula `TARGET IS SOURCE` propuesta, tipo L&J tentativo y pasajes de evidencia —
presentado como propuesta para que Frida valide, corrija o renombre los mapeos (la
asignación final de dominios es decisión interpretativa suya, no del pipeline).

**G. Visualización**: HTML interactivo autocontenido; nodos coloreables por
Period/Speaker/Family/TermStatus, aristas por tipo (familia, referencia, eco), slider
temporal ene-2024 → jul-2026 con el corte de julio 2024 marcado.

Vista principal ("mapa de autoría y familias", según referencia visual de Frida
2026-08-29): **color del nodo = actor autor** (GDS / DSIT / DSIT+GDS / CDDO / PMO /
External_adviser / cada empresa — las empresas comparten gama, distinguibles entre sí);
**agrupación espacial = familia** (las 5 familias MoU como clústeres delimitados con
hull/etiqueta, el tronco estrategia GDS/DSIT al centro); **tamaño del nodo = grado de
entrada** (cuántas veces lo referencian otros documentos del corpus — proxy de
autoridad); **grosor de arista = frecuencia de referencia**; dirección de flecha =
quién cita a quién; tipo de línea distingue referencia explícita / familia /
supersession / eco. Tooltip por nodo: doc_id, fecha, genre, term_status.
*Adelanto de calendario*: esta vista se genera en versión preliminar al cierre de
Fase 1 (solo requiere textos + manifest: extracción de referencias explícitas), y se
enriquece en Fase 6 con echo-phrases y códigos compartidos.

**QA interno (no resultados)**: comparación Leiden vs. familias/agrupaciones y matriz
de similitud semántica — viven en `analysis/qa/`, se citan solo si Frida decide usarlos
como verificación de robustez en métodos.

## Fase 7 — Alta incremental de documentos

`add_document.py <url> [--family X --genre Y ...]`:
1. **Checklist de admisión primero** — las reglas de la hoja `method` aplicadas como
   filtro explícito: Rule 1 (supersession/ventana), Rule 3 (speaker, no publisher),
   Rule 4 (frontera funcional del centro digital), Rule 5 (criterio de blogs),
   producer-vs-scrutineer (el escrutinio parlamentario/auditoría es contexto, no corpus)
   y written-vs-spoken (Hansard fuera). El script presenta el checklist evaluado y
   **Frida aprueba la admisión**; nada entra automático.
2. Fila nueva en el manifest con `corpus_version` siguiente — v1 queda intacto: el
   análisis de la tesis siempre puede regenerarse filtrando `corpus_version == 1`.
3. Fases 1–4 solo sobre el documento nuevo, con **prompts, modelo y guidebook
   congelados** en la versión vigente.
4. Respuestas sin sub-código existente → `candidate_code`, acumuladas para revisión de
   Frida; los códigos nuevos nunca nacen sin decisión humana.
5. Fase 6 se regenera completa (es idempotente desde los JSONL).

Cada corrida registra `run_id`, modelo, versión de prompts y de guidebook: cualquier
número de la tesis es trazable a una corrida exacta.

---

## Códigos y atributos

**Se toman tal cual:** los 7 parent codes de la Tabla 3, `PublicGood_Nominal`,
`PublicBenefit_Distributive`, los 8 nodos de beneficiario, y los atributos de la
Tabla 4 (Period, Authorship, Side, Partnership family, Phrase position, Definitional
status) + Genre, GDSTier, Stage, TermStatus del plan NVivo.

**Adiciones propuestas — solo las que caben dentro del marco de la matriz** (Frida
decide antes de la corrida):

1. **AGENCY** *(SO3; extensible al corpus completo)* — Fairclough 2003, ya declarado en
   la matriz para SO3: `agente_explícito / pasiva_sin_agente / nominalización`. Su
   aplicación corpus-completo está sancionada por la query 2 del propio plan NVivo
   (agencia × Genre).
2. **MODALITY** *(SO3)* — Fairclough, explícito en la matriz: `deóntica`
   (must/should/commit) vs. `epistémica/predictiva` (will/could/expected). Cruza con la
   pregunta de "force" de la Tabla 2: distingue compromiso de profecía.
3. **NARRATIVE_ARC** *(SO1; atributo por documento)* — Kaplan 2020 (beginnings, middles,
   ends), ya implícito en los memos ("ARC POSITION 1"); formalizarlo lo vuelve consultable.
4. **THREAT_TYPE** *(SO1/SO3; sub-dimensión de ACTANTS)* — Kaplan: `riesgo_tecnológico /
   rezago_geopolítico / statu_quo_burocrático / desconfianza_pública`. La migración de
   la amenaza a lo largo del período es un hallazgo probable (el memo del doc 1 ya la
   detecta: "AI is the risk").
5. **METAPHOR** *(SO1, alimenta NATURALISED ORDER de SO1/SO2)* — Lakoff & Johnson 1980;
   procedimiento MIP/MIPVU (Pragglejaz 2007; Steen et al. 2010); puente opcional con
   Fairclough: Charteris-Black 2004. Por instancia: expresión verbatim → dominio fuente
   → dominio meta → fórmula `TARGET IS SOURCE` (p. ej. "turbocharge" → EL GOBIERNO ES
   UNA MÁQUINA; "frontier AI" → EL DESARROLLO DE IA ES EXPLORACIÓN TERRITORIAL;
   "harness" → LA IA ES UNA FUERZA QUE SE DOMA) → tipo L&J (estructural / orientacional /
   ontológica / personificación) → **qué ilumina / qué esconde**. El campo
   "esconde" es el mecanismo léxico de la naturalización (Lears) y alimenta directo la
   pregunta 7. Agregados habilitados, todos dentro de los SO: dominios fuente por
   speaker (SO1), dominios compartidos gobierno↔empresa por familia (SO3, complementa
   ECHO), migración temporal de dominios (SO2). *Única adición que suma citas al marco:
   requiere incorporar L&J (+ MIP) al capítulo teórico.*
6. **ECHO** *(SO3)* — generado computacionalmente en Fase 6B (Hajer); no se codifica a mano.
7. **AUDIENCE** *(SO2; atributo por documento)* — `parlamento / practitioners /
   público_general / industria`; ya se registra como prosa en el memo de función
   (Tabla 2); como valor cerrado habilita el cruce "¿ante qué audiencia aparece el
   término y ante cuál desaparece?", que es el corazón de SO2.

**Descartado por la restricción de alineación:** LEGITIMATION (van Leeuwen 2007) —
ampliaba el marco teórico más allá de lo establecido en la matriz sin necesidad para
ningún SO.

---

## Orden de ejecución y puntos de control humano

| Paso | Hace | Sirve a | Control de Frida |
|---|---|---|---|
| 0 | Manifest desde el Excel | base | Confirmar conteo 37 y casos marcados |
| 1 | Descarga + archivado + texto estructurado | base | Revisar reporte de links rotos |
| 2 | Segmentación + término/variantes + embeddings | SO1/SO2 | Confirmar `CHECK`; aprobar lexicón |
| 3 | Evaluación de modelos | base | Codificar muestra; aprobar modelo |
| — | — | — | **Decidir qué códigos propuestos entran** |
| 4 | Codificación Ronda 1 | SO1/SO2/SO3 | Validación 15–20% + reporte de acuerdo |
| 5 | Agrupación para consolidación | SO1/SO2/SO3 | **Nombrar sub-códigos (guidebook)** |
| 6 | Redes, queries, exports, viz | SO1/SO2/SO3 | Lectura analítica — aquí empieza la interpretación |
| 7 | Alta incremental | según doc | Aprobar admisión (checklist) y `candidate_codes` |

Stack: Python (venv del proyecto), PyMuPDF, requests/BeautifulSoup, Ollama API (cloud
para LLM; embeddings locales o cloud), networkx + python-igraph, visualización HTML
autocontenida. Datos intermedios en archivos planos (CSV/JSONL/YAML) versionables.
