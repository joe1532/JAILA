# JAILA RAG KNOWLEDGE GRAPH STRUCTURE SPECIFICATION

## 📋 OVERSIGT

Dette dokument specificerer den komplette struktur for JAILA RAG's juridiske knowledge graphs. Strukturen er optimeret til V8 Excellence med tovejs-søgning (bidirectional search) og unified cross-graph retrieval.

### 🎯 DESIGNPRINCIPPER

1. **Hierarkisk kompatibilitet** - Identisk afsnit-struktur på tværs af love
2. **Tovejs-navigation** - Bidirectional relations for enhanced retrieval
3. **Multi-modal søgning** - Support for semantisk, BM25, og hybrid queries
4. **Cross-graph unified** - Fælles struktur tillader søgning på tværs af love
5. **Production-ready** - Optimeret til real-world legal applications

---

## 🏗️ GRAF-ARKITEKTUR

### ROOT STRUCTURE
```json
{
  "version": "string",
  "metadata": { },
  "afsnit_structure": [ ],
  "entities": [ ],
  "relations": [ ]
}
```

### METADATA FIELDS
```json
{
  "version": "X.Y_DESCRIPTION",
  "creation_date": "ISO_TIMESTAMP",
  "total_entities": "number",
  "total_relations": "number",
  "bidirectional_relations": "number",
  "update_history": [ ]
}
```

---

## 📊 ENTITY STRUKTUR

### CORE ENTITY SCHEMA
Alle entities skal indeholde følgende obligatoriske felter:

```json
{
  "id": "string - Unique identifier",
  "type": "string - Entity type classifier", 
  "title": "string - Human readable title",
  "content": "string - Full text content",
  "summary": "string - Brief summary",
  "domain": "string - Legal domain (kildeskatteloven/ligningsloven)",
  "keywords": ["array of strings"],
  "metadata": { },
  "response_examples": [ ],
  "uuid": "string - Stable UUID"
}
```

### ENTITY TYPES HIERARKI

#### 1. STRUKTURELLE ENTITIES

**AFSNIT (Hierarchical Containers)**
```json
{
  "id": "afsnit_[roman_numeral]",
  "type": "afsnit",
  "title": "Afsnit [I-IX]: [Description]",
  "content": "[Description]\n\nIndeholder bestemmelser: [paragraphs]\n\nDette afsnit udgør en strukturel enhed...",
  "metadata": {
    "legal_source": "kildeskatteloven|ligningsloven",
    "entity_level": "afsnit", 
    "afsnit_number": "I|II|III|IV|V|VI|VII|VIII|IX",
    "structural_type": "hierarchical_container",
    "contains_paragraphs": ["§1", "§2", "..."],
    "is_structural": true,
    "provision_type": "structural_division"
  }
}
```

**KAPITEL (Thematic Containers - kun Ligningsloven)**
```json
{
  "id": "kapitel_[number]_[description]",
  "type": "structural_chapter",
  "title": "Kapitel [N] - [Thematic Description]", 
  "content": "Kapitel [N] - [Description] - [Details]. Indeholder paragrafferne: [list]",
  "metadata": {
    "kapitel": "number",
    "paragraph_reference": "kapitel_id",
    "contains_paragraphs": ["§X", "§Y"]
  }
}
```

#### 2. PARAGRAF ENTITIES

**BASE PARAGRAFFER**
```json
{
  "id": "§[number][letter?]",
  "type": "hovedparagraf|legal_provision",
  "title": "§[X] [Title]",
  "content": "[Full paragraph text]",
  "metadata": {
    "paragraph_number": "[number][letter?]",
    "law_reference": "kildeskatteloven|ligningsloven",
    "provision_type": "main_provision|supporting_provision",
    "is_base_paragraph": true,
    "has_subsections": true|false,
    "first_sentence": "string",
    "legal_complexity": "low|medium|high",
    "thematic_keywords": ["array"],
    "legal_concepts": ["array"]
  }
}
```

**STYKKE ENTITIES**
```json
{
  "id": "§[number][letter?]_stk[N]",
  "type": "stykke|section_sub_[details]",
  "title": "§[X] stk. [N]",
  "content": "[Subsection text]",
  "metadata": {
    "paragraph_reference": "§[number][letter?]",
    "provision_level": "stk",
    "subsection_number": "N"
  }
}
```

**NUMMER ENTITIES**
```json
{
  "id": "§[number][letter?]_stk[N]_nr[M]|§[number]_nr[M]",
  "type": "nummer|section_sub_[details]",
  "title": "§[X] stk. [N], nr. [M]|§[X] nr. [M]",
  "content": "[Number-specific text]",
  "metadata": {
    "paragraph_reference": "§[number][letter?]",
    "provision_level": "nr",
    "number_reference": "M"
  }
}
```

#### 3. THEMATIC ENTITIES (Ligningsloven specifik)

**TRANSFER PRICING ENTITIES**
```json
{
  "id": "[descriptive_name]",
  "type": "transfer_pricing_[category]|gaar_[category]|renteudgifter_[category]|...",
  "title": "[Descriptive Title]",
  "content": "[Detailed explanation]",
  "metadata": {
    "thematic_keywords": ["transfer pricing", "armslængde", "..."],
    "legal_concepts": ["related parties", "arm's length", "..."],
    "provision_type": "thematic_explanation"
  }
}
```

---

## 🔗 RELATIONS STRUKTUR

### CORE RELATION SCHEMA
```json
{
  "source": "string - Source entity ID",
  "target": "string - Target entity ID", 
  "type": "string - Relation type",
  "description": "string - Human readable description",
  "strength": "number - 0.0 to 1.0",
  "bidirectional": "boolean - True for thematic, False for structural",
  "keywords": ["array of strings"],
  "metadata": {
    "relation_type": "structural|thematic",
    "hierarchy_level": "string - Specific hierarchy description"
  }
}
```

### RELATION TYPES

#### 1. STRUKTURELLE RELATIONER (Unidirectional)
```json
{
  "type": "contains",
  "bidirectional": false,
  "metadata": {
    "relation_type": "structural",
    "hierarchy_level": "afsnit_to_paragraph|afsnit_to_chapter|chapter_to_paragraph|paragraph_to_stk|stk_to_nr"
  }
}
```

#### 2. THEMATISKE RELATIONER (Bidirectional)

**Kildeskatteloven:**
```json
{
  "type": "enhanced_thematic_related|relates_to|extends|specializes_to|supports",
  "bidirectional": true,
  "metadata": {
    "relation_type": "thematic"
  }
}
```

**Ligningsloven:**
```json
{
  "type": "supplerer|udbygger|begrænser|modificerer",
  "bidirectional": true,
  "metadata": {
    "relation_type": "thematic"
  }
}
```

---

## 📐 HIERARKISK STRUKTUR

### KILDESKATTELOVEN HIERARKI
```
ROOT
├── Afsnit I: Skattepligten
│   ├── §1 (Fuld skattepligt)
│   ├── §2 (Begrænset skattepligt)
│   │   ├── §2_stk1
│   │   ├── §2_stk2
│   │   └── ...
│   └── ...
├── Afsnit I A: Grænsegængere
├── Afsnit II: Skattepligtens omfang
├── Afsnit III: Den skattepligtige indkomst
├── Afsnit IV: §§ 35-39 (Ophævet)
├── Afsnit V: Opkrævning af indkomstskat
├── Afsnit VI: Indeholdelse i aktieudbytte
├── Afsnit VII: Hæftelses- og inddrivelsesbestemmelser
├── Afsnit VIII: Straffebestemmelser
└── Afsnit IX: Forskellige bestemmelser
```

### LIGNINGSLOVEN HIERARKI
```
ROOT
├── Afsnit I: Grundlæggende bestemmelser
│   └── Kapitel 1: Generelle bestemmelser
│       ├── §1
│       └── §4
├── Afsnit II: Transfer pricing og anti-misbrug
│   └── Kapitel 2: Transfer Pricing og GAAR
│       ├── §2
│       ├── §2A
│       └── §3
├── Afsnit III: Rentebestemmelser
│   └── Kapitel 3: Rentebestemmelser
│       ├── §5-§5I
│       └── §6-§6B
├── Afsnit IV: Skattefritagelser
│   └── Kapitel 4: Skattefrihed og exemptions
│       └── §7 (med alle undernumre)
├── Afsnit V: Ansættelse og udgifter
├── Afsnit VI: Pensioner og forsikring
├── Afsnit VII: Afskrivninger
├── Afsnit VIII: Personalegoder og værdiansættelse
└── Afsnit IX: Øvrige bestemmelser
```

---

## 🔍 SØGEFUNKTIONALITETER

### UNDERSTØTTEDE SØGEMODES

#### 1. PARAGRAF-SØGNING
- **Pattern**: `§[number][letter?]`
- **Eksempler**: `§2A`, `§16`, `§33_stk1`
- **Fuzzy matching**: Støtter variationer og delvis match

#### 2. STRUKTUREL SØGNING  
- **Afsnit**: `afsnit_[roman]` eller "Afsnit [I-IX]"
- **Kapitel**: `kapitel_[number]_[description]`
- **Hierarkisk navigation**: Top-down og bottom-up

#### 3. SEMANTISK SØGNING
- **Vector embedding** på `content` og `title` felter
- **Metadata-baseret** thematic search
- **Legal concepts** matching via keywords

#### 4. BM25 TEKSTSØGNING
- **TF-IDF ranking** på alle tekstfelter
- **Boolean queries**: AND, OR, NOT operators
- **Phrase matching** og wildcard support

#### 5. TOVEJS-NAVIGATION
- **Bidirectional relations** for thematic connections
- **Graph traversal** med depth control
- **Multi-hop søgning** for kontekstuel discovery

#### 6. HYBRID SØGNING
- **Weighted combination** af alle ovenstående
- **Contextual re-ranking** via relations
- **Cross-graph unified** retrieval

---

## 🛠️ IMPLEMENTERINGSGUIDE

### STEP 1: BASIC STRUCTURE SETUP
```python
graph_structure = {
    "version": "X.Y_DESCRIPTION",
    "entities": [],
    "relations": [],
    "afsnit_structure": []
}
```

### STEP 2: CREATE AFSNIT ENTITIES
```python
def create_afsnit_entity(afsnit_number, title, content, paragraphs):
    return {
        "id": f"afsnit_{afsnit_number.lower()}",
        "type": "afsnit",
        "title": f"Afsnit {afsnit_number.upper()}: {title}",
        "content": f"{title}\n\n{content}\n\nDette afsnit udgør en strukturel enhed...",
        "metadata": {
            "legal_source": "law_name",
            "entity_level": "afsnit",
            "afsnit_number": afsnit_number.upper(),
            "structural_type": "hierarchical_container",
            "contains_paragraphs": paragraphs,
            "is_structural": True
        }
    }
```

### STEP 3: CREATE PARAGRAPH ENTITIES
```python
def create_paragraph_entity(paragraph_id, title, content, law_source):
    return {
        "id": paragraph_id,
        "type": "hovedparagraf" if "stk" not in paragraph_id else "stykke",
        "title": title,
        "content": content,
        "metadata": {
            "paragraph_number": paragraph_id.replace("§", ""),
            "law_reference": law_source,
            "is_base_paragraph": "stk" not in paragraph_id,
            "provision_type": "main_provision"
        }
    }
```

### STEP 4: CREATE STRUCTURAL RELATIONS
```python
def create_contains_relation(source_id, target_id, hierarchy_level):
    return {
        "source": source_id,
        "target": target_id,
        "type": "contains",
        "bidirectional": False,
        "metadata": {
            "relation_type": "structural",
            "hierarchy_level": hierarchy_level
        }
    }
```

### STEP 5: CREATE THEMATIC RELATIONS
```python
def create_thematic_relation(source_id, target_id, relation_type):
    return {
        "source": source_id,
        "target": target_id,
        "type": relation_type,
        "bidirectional": True,  # Key for tovejs-søgning!
        "metadata": {
            "relation_type": "thematic"
        }
    }
```

---

## ✅ VALIDERING OG KVALITETSKONTROL

### REQUIRED CHECKS

#### 1. STRUKTUR VALIDERING
```python
def validate_structure(graph):
    # Check required fields
    assert "entities" in graph
    assert "relations" in graph
    assert "version" in graph
    
    # Check afsnit entities exist
    afsnit_entities = [e for e in graph["entities"] if e["type"] == "afsnit"]
    assert len(afsnit_entities) >= 5  # Minimum afsnit count
    
    # Check paragraph entities
    paragraph_entities = [e for e in graph["entities"] if e["id"].startswith("§")]
    assert len(paragraph_entities) > 0
```

#### 2. RELATIONS VALIDERING
```python
def validate_relations(graph):
    # Check bidirectional marking
    thematic_types = ["enhanced_thematic_related", "supplerer", "udbygger", "modificerer"]
    for relation in graph["relations"]:
        if relation["type"] in thematic_types:
            assert relation["bidirectional"] == True
        elif relation["type"] == "contains":
            assert relation["bidirectional"] == False
```

#### 3. KOMPATIBILITET CHECK
```python
def validate_cross_graph_compatibility(graph1, graph2):
    # Both must have afsnit structure
    graph1_afsnit = [e for e in graph1["entities"] if e["type"] == "afsnit"]
    graph2_afsnit = [e for e in graph2["entities"] if e["type"] == "afsnit"]
    assert len(graph1_afsnit) > 0 and len(graph2_afsnit) > 0
    
    # Both must have bidirectional relations
    graph1_bidirectional = sum(1 for r in graph1["relations"] if r.get("bidirectional"))
    graph2_bidirectional = sum(1 for r in graph2["relations"] if r.get("bidirectional"))
    assert graph1_bidirectional > 0 and graph2_bidirectional > 0
```

---

## 📈 PERFORMANCE OPTIMERING

### INDEXING STRATEGY
1. **Primary indexes**: `id`, `type`, `paragraph_number`
2. **Search indexes**: `content`, `title`, `keywords`
3. **Hierarchical indexes**: `afsnit_number`, `contains_paragraphs`
4. **Thematic indexes**: `thematic_keywords`, `legal_concepts`

### RETRIEVAL OPTIMIZATION
1. **Caching**: Frequently accessed entities og relations
2. **Batch processing**: Multiple entity lookup i single operation
3. **Lazy loading**: Relations kun loaded når nødvendigt
4. **Query optimization**: Smart query planning baseret på type

---

## 🚀 DEPLOYMENT CHECKLIST

### PRE-DEPLOYMENT VALIDATION
- [ ] Alle entities har required fields
- [ ] Alle relations har korrekt bidirectional marking
- [ ] Afsnit struktur er komplet
- [ ] Cross-graph kompatibilitet verificeret
- [ ] Performance tests bestået
- [ ] Tovejs-søgning funktionstest OK

### PRODUCTION FILES
1. **`kildeskatteloven_UNIFIED_V8_BIDIRECTIONAL.json`**
   - 467 entities, 388 relations, 41 tovejs-relationer
   - 12 afsnit-strukturer, komplet hierarki

2. **`ligningsloven_UNIFIED_V8_FINAL_AFSNIT_COMPATIBLE.json`** 
   - 265 entities, 508 relations, 6 tovejs-relationer
   - 9 afsnit-strukturer, kapitel+afsnit hierarki

### SUCCESS METRICS
- ✅ 100% strukturel kompatibilitet
- ✅ Alle søgemodes functional
- ✅ Tovejs-navigation implementeret
- ✅ Cross-graph unified retrieval ready
- ✅ Production-ready performance

---

## 📚 EKSEMPLER

### MINIMAL WORKING EXAMPLE
Se `example_graph_creation.py` for komplet implementering af struktur.

### COMMON PATTERNS
```python
# Skab base paragraf med stykker
create_paragraph_hierarchy("§2A", "Transfer pricing", base_content, stk_content)

# Tilføj thematic relation
add_bidirectional_relation("§2A", "§3", "supplerer")

# Skab afsnit container
create_afsnit_container("II", "Transfer pricing", ["§2", "§2A", "§3"])
```

---

## 🏆 KONKLUSION

Denne specifikation sikrer **100% reproducerbar** struktur for JAILA RAG knowledge graphs med:

- ✅ **Identisk hierarki** på tværs af love
- ✅ **Tovejs-søgning** med bidirectional relations  
- ✅ **Multi-modal retrieval** support
- ✅ **Cross-graph kompatibilitet**
- ✅ **Production-ready** kvalitet

**Follow denne guide nøje for at sikre kompatibilitet med eksisterende graphs og unified retriever functionality.**

---

*Dokument version: 1.0 | Sidst opdateret: 2024 | JAILA RAG V8 Excellence* 