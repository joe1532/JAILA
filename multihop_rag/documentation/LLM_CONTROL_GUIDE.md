# 🤖 LLM CONTROL GUIDE - Hvor og Hvordan Output Påvirkes

**Komplet oversigt over alle steder hvor LLM er involveret og output kan kontrolleres**

## 🎯 **OVERVIEW: LLM INVOLVERING I MULTIHOP RAG**

LangChain Multihop RAG systemet har **4 primære LLM interaction punkter** plus flere indstillinger der påvirker output:

```
🔄 MULTIHOP PIPELINE
├── 🧠 LLM PUNKT 1: Query Analysis
├── 🔍 RETRIEVAL: Search Engine (konfigurerbar vægtning)
├── 🧠 LLM PUNKT 2: Document Analysis (HOP 1)
├── 🔍 RETRIEVAL: Follow-up Search (baseret på LLM output)
├── 🧠 LLM PUNKT 3: Document Analysis (HOP 2)
├── 🔍 RETRIEVAL: Deep Search (baseret på LLM output)
└── 🧠 LLM PUNKT 4: Final Answer Generation
```

---

## 🧠 **LLM PUNKT 1: QUERY ANALYSIS**

### **Fil:** `juridisk_rag_langchain.py` (linje 125-142)
### **Formål:** Analyser spørgsmål og planlæg multihop strategi

```python
self.query_analysis_template = PromptTemplate.from_template("""
Du er en ekspert i dansk skatteret og query-analyse.

Analyser følgende juridiske spørgsmål og identificér:
1. Hvilke love der er relevante
2. Hvilke paragraffer der nævnes
3. Hvilke juridiske koncepter der skal undersøges
4. Om spørgsmålet kræver multihop reasoning (flere søgninger)

SPØRGSMÅL: {question}

SVAR I JSON FORMAT:
{{
    "laws": ["lov1", "lov2"],
    "paragraphs": ["§ X", "§ Y"],
    "concepts": ["koncept1", "koncept2"],
    "needs_multihop": true/false,
    "reasoning": "forklaring af hvorfor multihop er nødvendig",
    "search_queries": ["query1", "query2", "query3"]
}}
""")
```

### **🎛️ HVOR KAN DU PÅVIRKE OUTPUT:**

1. **Prompt Engineering:**
   - ✏️ **Rediger template** (linje 125-142)
   - 📝 **Tilføj flere instruktioner** til JSON format
   - 🎯 **Specificer juridiske domæner** mere præcist
   - 🔍 **Ændre query generation logik**

2. **Model Indstillinger:**
   ```python
   # I LangChainRAGConfig
   temperature: float = 0.1        # PÅVIRKER: Kreativitet i query analyse
   max_tokens: int = 2000         # PÅVIRKER: Hvor detaljeret analyse
   model: str = "gpt-4o-2024-08-06"  # PÅVIRKER: Intelligens niveau
   ```

---

## 🧠 **LLM PUNKT 2: DOCUMENT ANALYSIS** 

### **Fil:** `juridisk_rag_langchain.py` (linje 144-164)
### **Formål:** Analyser fundne dokumenter og beslut næste søgning

```python
self.doc_analysis_template = PromptTemplate.from_template("""
Du er ekspert i juridisk dokumentanalyse.

Analyser følgende dokumenter og identificér:
1. Nøgleinformation der besvarer spørgsmålet
2. Manglende information der kræver yderligere søgning
3. Referencer til andre paragraffer/love
4. Juridiske koncepter der skal uddybes

SPØRGSMÅL: {question}

DOKUMENTER:
{documents}

SVAR I JSON FORMAT:
{{
    "key_findings": ["finding1", "finding2"],
    "missing_info": ["info1", "info2"],
    "references": ["ref1", "ref2"],
    "needs_more_search": true/false,
    "next_queries": ["query1", "query2"]
}}
""")
```

### **🎛️ HVOR KAN DU PÅVIRKE OUTPUT:**

1. **Prompt Engineering:**
   - ✏️ **Rediger document analysis prompt** (linje 144-164)
   - 🔍 **Ændre kriterier** for "needs_more_search"
   - 📊 **Specificer hvilke referencer** der skal prioriteres
   - 🎯 **Tilføj juridisk domæne-specifik analyse**

2. **Document Formatting:**
   ```python
   # I _format_documents_for_prompt() (linje 481-503)
   formatted.append(f"""
   DOKUMENT {i}:
   Reference: {reference}                    # PÅVIRKER: Hvordan LLM ser dokumenter
   Chunk ID: {metadata.get('chunk_id')[:8]}  # PÅVIRKER: Context for LLM
   Type: {metadata.get('type')}              # PÅVIRKER: Prioritering logik
   
   INDHOLD:
   {doc.page_content[:1000]}                 # PÅVIRKER: Hvor meget tekst LLM ser
   """)
   ```

---

## 🧠 **LLM PUNKT 3: FINAL ANSWER GENERATION**

### **Fil:** `juridisk_rag_langchain.py` (linje 166-195)
### **Formål:** Generer komplet svar baseret på alle dokumenter

```python
self.answer_template = PromptTemplate.from_template("""
Du er en højt specialiseret ekspert i dansk skatteret.

Baseret på dokumenterne fra flere søgninger, giv et komplet svar på spørgsmålet.

VIGTIGE INSTRUKSER:
- Svar UDELUKKENDE baseret på de vedlagte dokumenter
- Citer præcise kilder (paragraf, stykke, nummer, lov)
- Forklar juridiske sammenhænge og referencer mellem dokumenter
- Strukturer svaret logisk
- Angiv hvis information mangler

SPØRGSMÅL: {question}

HOP 1 DOKUMENTER:
{hop1_docs}

HOP 2 DOKUMENTER:
{hop2_docs}

HOP 3 DOKUMENTER:
{hop3_docs}

REASONING PATH:
{reasoning_path}

KOMPLET JURIDISK SVAR:
""")
```

### **🎛️ HVOR KAN DU PÅVIRKE OUTPUT:**

1. **Prompt Engineering:**
   - ✏️ **Rediger instrukser** (linje 173-179)
   - 📝 **Tilføj formatering requirements**
   - 🎯 **Specificer citationsformat**
   - 📊 **Ændre strukturering instruktioner**

2. **Context Preparation:**
   ```python
   # I _generate_multihop_answer() (linje 420-442)
   hop1_text = self._format_documents_for_prompt(all_documents["hop1"])
   hop2_text = self._format_documents_for_prompt(all_documents["hop2"])
   hop3_text = self._format_documents_for_prompt(all_documents["hop3"])
   
   # PÅVIRKER: Hvilke dokumenter LLM ser
   # PÅVIRKER: Rækkefølge af information
   # PÅVIRKER: Context balance mellem hops
   ```

---

## 🧠 **LLM PUNKT 4: SINGLE-HOP FALLBACK**

### **Fil:** `juridisk_rag_langchain.py` (linje 504-533)
### **Formål:** Simpel generation når multihop ikke bruges

```python
simple_prompt = f"""
Du er ekspert i dansk skatteret. Besvar følgende spørgsmål baseret på dokumenterne.

SPØRGSMÅL: {question}

DOKUMENTER:
{docs_text}

SVAR:
"""
```

### **🎛️ HVOR KAN DU PÅVIRKE OUTPUT:**
- ✏️ **Rediger simple prompt** direkte i koden
- 📝 **Tilføj instruktioner** for enkle svar

---

## ⚙️ **KONFIGURATION INDSTILLINGER DER PÅVIRKER OUTPUT**

### **1. LLM CORE SETTINGS**

```python
# I LangChainRAGConfig (langchain_rag_config.py)
class LangChainRAGConfig:
    # === DIREKTE LLM PÅVIRKNING ===
    model: str = "gpt-4o-2024-08-06"     # 🎯 Model intelligens
    temperature: float = 0.1             # 🎲 Kreativitet/randomness
    max_tokens: int = 2000               # 📏 Svar længde
```

**🎛️ PÅVIRKNING:**
- **Temperature 0.0-0.2:** Meget præcise, konsistente svar
- **Temperature 0.2-0.5:** Balanceret kreativitet og præcision  
- **Temperature 0.5-1.0:** Kreative, varierede svar
- **Max Tokens:** Begrænser hvor detaljerede svar kan være

### **2. MULTIHOP REASONING SETTINGS**

```python
# === MULTIHOP PÅVIRKNING ===
max_documents_per_hop: int = 5           # 📄 Information density per hop
max_hops: int = 3                        # 🔄 Hvor dybt systemet tænker
hop_confidence_threshold: float = 0.4    # 🎯 Hvor sikker før næste hop
max_reasoning_depth: int = 3             # 🧠 Reasoning kompleksitet
enable_multihop: bool = True             # 🔀 On/off switch
```

**🎛️ PÅVIRKNING:**
- **Flere docs per hop:** Mere information, men potentiel noise
- **Flere hops:** Dybere analyse, men langsommere
- **Lavere confidence threshold:** Flere follow-up søgninger
- **Højere reasoning depth:** Mere kompleks LLM reasoning

### **3. CONTEXT SETTINGS**

```python
# === CONTEXT PÅVIRKNING ===
max_context_length: int = 12000          # 📊 Total information til LLM
context_overlap: int = 300               # 🔗 Overlap mellem chunks
include_related_notes: bool = True       # 📝 Inkluder noter/kommentarer
```

**🎛️ PÅVIRKNING:**
- **Større context:** LLM ser mere, men kan blive distrahet
- **Context overlap:** Bedre sammenhæng, men redundans
- **Related notes:** Mere baggrund, men potentiel irrelevans

---

## 🔍 **RETRIEVAL SETTINGS DER PÅVIRKER LLM INPUT**

### **1. SEARCH STRATEGY**

```python
# I SearchStrategy enum
class SearchStrategy(Enum):
    AUTO = "auto"                    # 🤖 Intelligent auto-valg
    PARAGRAPH_FIRST = "paragraph_first"  # ⚖️ Juridiske docs først
    SEMANTIC_FIRST = "semantic_first"    # 🧠 Konceptuel søgning først
    HYBRID = "hybrid"                    # 🔀 Balanceret mix
    MULTIHOP = "multihop"               # 🎯 Optimeret til multihop
```

**🎛️ PÅVIRKNING PÅ LLM:**
- **PARAGRAPH_FIRST:** LLM får præcise juridiske docs → mere akkurate svar
- **SEMANTIC_FIRST:** LLM får konceptuelle docs → mere forklarende svar
- **HYBRID:** LLM får blandet indhold → balancerede svar

### **2. SEARCH ENGINE VÆGTNING**

```python
# I search_engine.py - _search_hybrid() (linje 155-185)
per_method = max(1, limit // 3)

# Prioritering i hybrid søgning:
# 1. Højeste prioritet: paragraf resultater
all_results.extend([(r, 'paragraph') for r in paragraph_results])

# 2. Mellem prioritet: semantisk resultater  
all_results.extend([(r, 'semantic') for r in semantic_results])

# 3. Laveste prioritet: keyword resultater
all_results.extend([(r, 'keyword') for r in keyword_results])
```

**🎛️ HVOR KAN DU ÆNDRE VÆGTNING:**
```python
# Rediger prioritering i _search_hybrid()
per_method = max(1, limit // 2)  # 🎯 Giv mere plads til top metoder

# Ændre vægtning ratio:
paragraph_weight = 0.5  # 50% til paragraffer
semantic_weight = 0.3   # 30% til semantisk  
keyword_weight = 0.2    # 20% til keyword
```

### **3. JURIDISK BOOST**

```python
# I search_engine.py - _search_semantic_with_juridisk_boost() (linje 252-285)
# Først: Søg kun i paragraffer
.with_where({
    "path": ["type"],
    "operator": "Equal", 
    "valueText": "paragraf"     # 🎯 BOOST til juridiske docs
})
.with_limit(limit // 2)         # 📊 50% af resultater fra paragraffer
```

**🎛️ HVOR KAN DU ÆNDRE BOOST:**
```python
# Ændre boost ratio
paragraph_limit = limit * 0.7   # 🎯 70% fra paragraffer i stedet for 50%

# Tilføj andre juridiske boost kriterier
boost_types = ["paragraf", "stykke", "nummer"]  # 📊 Flere juridiske typer
```

---

## 📊 **CONFIDENCE SCORING DER PÅVIRKER OUTPUT**

### **Fil:** `juridisk_rag_langchain.py` (linje 568-593)

```python
def _calculate_multihop_confidence(self, all_documents: Dict, reasoning_path: List) -> float:
    base_score = 0.5
    
    # Boost for flere dokumenter
    total_docs = sum(len(docs) for docs in all_documents.values())
    if total_docs >= 5:
        base_score += 0.2           # 📊 +20% for mange docs
    elif total_docs >= 3:
        base_score += 0.1           # 📊 +10% for medium docs
    
    # Boost for successful multihop
    successful_hops = len([step for step in reasoning_path if "hop" in step["step"]])
    base_score += successful_hops * 0.1  # 📊 +10% per hop
    
    # Boost for paragraph documents
    paragraph_docs = sum(1 for docs in all_documents.values() for doc in docs 
                        if doc.metadata.get('type') == 'paragraf')
    if paragraph_docs > 0:
        base_score += 0.1           # 📊 +10% for juridiske docs
    
    return min(base_score, 1.0)
```

**🎛️ HVOR KAN DU ÆNDRE CONFIDENCE VÆGTNING:**
```python
# Ændre boost værdier:
document_boost = 0.3        # Øg boost for mange docs
hop_boost = 0.15           # Øg boost per hop
paragraph_boost = 0.2      # Øg boost for juridiske docs

# Tilføj nye boost kriterier:
if any("kildeskatteloven" in doc.metadata.get('title', '') for docs in all_documents.values() for doc in docs):
    base_score += 0.15     # 📊 Extra boost for KSL docs
```

---

## 🎯 **DOCUMENT FILTERING & PRIORITERING**

### **1. WHERE FILTERS (Påvirker hvad LLM ser)**

```python
# I search_engine.py - _build_juridisk_where_filter() (linje 287-322)
def _build_juridisk_where_filter(self, query: str) -> Optional[Dict]:
    # Match § nummer
    if section_match:
        return {
            "path": ["paragraph"],
            "operator": "Like",
            "valueText": f"*§ {section_num}*"  # 🎯 Kun § docs til LLM
        }
    
    # Match lovnavne
    if 'kildeskatteloven' in query.lower():
        return {
            "path": ["title"],
            "operator": "Like", 
            "valueText": "*kildeskattelov*"    # 🎯 Kun KSL docs til LLM
        }
```

**🎛️ HVOR KAN DU ÆNDRE FILTERING:**
```python
# Tilføj flere juridiske mønstre:
juridisk_patterns = [
    '§', 'paragraf', 'stk', 'stykke', 'nr', 'nummer', 
    'kildeskatteloven', 'ligningsloven', 'aktieavancebeskatningsloven',
    'ksl', 'lov nr', 'bekendtgørelse',
    'cirkulære', 'vejledning', 'kommentar'  # 📊 Nye mønstre
]

# Ændre prioritering af lovnavne:
if 'aktieavancebeskatningsloven' in query.lower():
    priority_boost = 0.3  # 🎯 Højere prioritet til ABL
```

### **2. DOCUMENT TYPE PRIORITERING**

```python
# I search_engine.py - _format_search_results() (linje 346-385)
# Chunk vægtning baseret på type
if chunk.get('type') == 'paragraf':
    result['priority_boost'] = 1.5      # 📊 50% boost til paragraffer
elif chunk.get('type') == 'stykke':
    result['priority_boost'] = 1.3      # 📊 30% boost til stykker
elif chunk.get('type') == 'nummer':
    result['priority_boost'] = 1.2      # 📊 20% boost til numre
else:
    result['priority_boost'] = 1.0      # 📊 Standard vægt
```

---

## 🔧 **PRAKTISKE CUSTOMIZATION EKSEMPLER**

### **1. ÆndreTemperature for Forskellige Opgaver**

```python
# Meget præcise juridiske opslag
precise_config = LangChainRAGConfig(temperature=0.01)

# Kreative juridiske analyser  
creative_config = LangChainRAGConfig(temperature=0.3)

# Balanceret juridisk rådgivning
balanced_config = LangChainRAGConfig(temperature=0.15)
```

### **2. Custom Prompt for Specifik Juridisk Analyse**

```python
# I juridisk_rag_langchain.py - tilføj specialiseret template
self.tax_comparison_template = PromptTemplate.from_template("""
Du er ekspert i sammenligning af skattelovgivning.

Analyser UDELUKKENDE forskelle og ligheder mellem:
- Specifikke paragraffer
- Juridiske begreber  
- Praktisk anvendelse
- Historisk udvikling

SAMMENLIGN: {question}

DOKUMENTER:
{documents}

FORMAT SVAR SOM:
LIGHEDER: [...]
FORSKELLE: [...]
PRAKTISK BETYDNING: [...]
""")
```

### **3. Ændre Document Vægtning for Specialiserede Emner**

```python
# Boost til specifikke love
def custom_law_boost(self, result: Dict) -> float:
    title = result.get('title', '').lower()
    boost = 1.0
    
    if 'kildeskatteloven' in title:
        boost *= 1.8    # 🎯 80% boost til KSL
    elif 'ligningsloven' in title:
        boost *= 1.5    # 🎯 50% boost til LL
    elif 'aktieavancebeskatningsloven' in title:
        boost *= 1.3    # 🎯 30% boost til ABL
    
    return boost
```

### **4. Custom Confidence Beregning**

```python
def custom_confidence_calculation(self, all_documents: Dict, query: str) -> float:
    base_score = 0.3
    
    # Juridisk specifik confidence
    if any('§' in query for query in [query]):
        base_score += 0.3  # 🎯 Paragraf spørgsmål er mere sikre
    
    # Lovnavn boost
    law_mentions = sum(1 for doc in all_documents.values() 
                      if any(law in doc.metadata.get('title', '') 
                            for law in ['kildeskatteloven', 'ligningsloven']))
    base_score += law_mentions * 0.1
    
    return min(base_score, 1.0)
```

---

## 📋 **FULD CHECKLIST: ALLE OUTPUT KONTROL PUNKTER**

### **🧠 LLM Prompt Templates (4 steder)**
- [ ] Query Analysis Template (linje 125-142)
- [ ] Document Analysis Template (linje 144-164)  
- [ ] Final Answer Template (linje 166-195)
- [ ] Single-hop Prompt (linje 504-533)

### **⚙️ LLM Model Settings (3 steder)**
- [ ] Temperature (kreativitet)
- [ ] Max Tokens (svar længde)
- [ ] Model choice (intelligens niveau)

### **🔄 Multihop Logic (5 steder)**
- [ ] Max hops (dybde)
- [ ] Docs per hop (information density)
- [ ] Confidence threshold (følsomhed)
- [ ] Reasoning depth (kompleksitet)
- [ ] Enable/disable multihop

### **📊 Context Preparation (3 steder)**
- [ ] Max context length
- [ ] Context overlap
- [ ] Document formatting for LLM

### **🔍 Search & Retrieval (6 steder)**
- [ ] Search strategy choice
- [ ] Hybrid vægtning
- [ ] Juridisk boost ratio
- [ ] Where filters
- [ ] Document type prioritering  
- [ ] Confidence scoring

### **🎯 Document Selection (4 steder)**
- [ ] Search limit per hop
- [ ] Document type filtering
- [ ] Law name prioritering
- [ ] Chunk vægtning

---

## 🚀 **KONKLUSION**

Du har nu **komplet kontrol** over alle aspekter af LLM output i Multihop RAG systemet:

- **4 LLM interaction punkter** med custom prompts
- **12+ konfiguration parametre** der påvirker LLM behavior  
- **6 retrieval settings** der styrer hvad LLM ser
- **8 document vægtning mekanismer** der prioriterer information
- **Custom confidence scoring** til at vurdere svar kvalitet

**🎯 Ved at justere disse parametre kan du fine-tune systemet til specifikke juridiske domæner, opgavetyper, og kvalitets krav!** 