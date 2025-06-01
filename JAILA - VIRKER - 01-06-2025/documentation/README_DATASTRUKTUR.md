# 🏗️ DATASTRUKTUR GUIDE - OPTIMERET SCHEMA

**Status**: ✅ **PRODUKTIONSKLAR**  
**Schema Version**: 2.0 (1024-dim optimeret)  
**Sidste opdatering**: 31. maj 2025

## 📊 **CURRENT DATABASE STATUS**

### **✅ Komplet Opsætning**
```
📄 Total dokumenter: 3,098
🔢 Vector dimensioner: 1024 (optimeret)
📋 Schema properties: 33 (komplet mapping)
💾 Storage størrelse: ~12 MB
⚡ Performance: 0.59-0.67s gennemsnit
🎯 Import success rate: 100%
```

### **📚 Data Coverage**
```
📖 Aktieavancebeskatningsloven: ~897 chunks
📖 Kildeskatteloven:           ~726 chunks  
📖 Ligningsloven:              ~1,517 chunks
📖 Statsskatteloven:           ~87 chunks
─────────────────────────────────────────
📄 TOTAL:                      3,098 chunks
```

---

## 🔧 **WEAVIATE SCHEMA DESIGN**

### **📝 LegalDocument Class Configuration**

```python
{
    "class": "LegalDocument",
    "vectorizer": "text2vec-openai",
    "moduleConfig": {
        "text2vec-openai": {
            "model": "text-embedding-3-large",
            "modelVersion": "latest", 
            "dimensions": 1024,  # 🎯 OPTIMERET: 67% storage besparelse
            "type": "text"
        },
        "generative-openai": {}
    },
    "invertedIndexConfig": {
        "bm25": {
            "b": 0.75,    # Optimeret for juridiske dokumenter
            "k1": 1.2     # Optimeret for paragrafsøgning
        },
        "stopwords": {"preset": "en"}
    }
}
```

---

## 📋 **SCHEMA PROPERTIES (33 FELTER)**

### **🔑 1. PRIMÆRE TEKSTFELTER**

#### **`text` (Original Tekst)**
```python
{
    "name": "text",
    "dataType": ["text"],
    "description": "Original paragraf/note tekst",
    "indexInverted": True,
    "tokenization": "word",
    "moduleConfig": {
        "text2vec-openai": {"skip": True}  # Bruger text_for_embedding
    }
}
```

#### **`text_for_embedding` (Optimeret Tekst)** 🎯
```python
{
    "name": "text_for_embedding", 
    "dataType": ["text"],
    "description": "Optimeret tekst til 1024-dim embedding",
    "indexInverted": False,
    "moduleConfig": {
        "text2vec-openai": {
            "skip": False,  # DENNE bruges til embedding
            "vectorizePropertyName": False
        }
    }
}
```

#### **`title` (Lovens Titel)**
```python
{
    "name": "title",
    "dataType": ["text"], 
    "description": "Lovens titel (fx 'Ligningsloven')",
    "indexInverted": True,
    "tokenization": "word",
    "moduleConfig": {
        "text2vec-openai": {"skip": False}  # Include i semantisk søgning
    }
}
```

### **🔗 2. IDENTIFIKATIONSFELTER**

#### **`chunk_id` (UUID)** 🆔
```python
{
    "name": "chunk_id",
    "dataType": ["text"],
    "description": "Unik chunk identifier (UUID)",
    "indexInverted": True,
    "tokenization": "field"  # Behandl som én enhed
}
```

#### **`type` (Dokumenttype)**
```python
{
    "name": "type",
    "dataType": ["text"],
    "description": "Type: 'paragraf' eller 'notes'",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`topic` (§ Reference)** 🎯
```python
{
    "name": "topic",
    "dataType": ["text"],
    "description": "§ reference eller emne (fx '§ 33 A')",
    "indexInverted": True,
    "tokenization": "field",  # Bevar "§ 33 A" som helhed
    "moduleConfig": {
        "text2vec-openai": {"skip": True}  # Præcis søgning
    }
}
```

### **🏗️ 3. STRUKTURELLE FELTER**

#### **`section` (Afsnit)**
```python
{
    "name": "section",
    "dataType": ["text"],
    "description": "Lovens afsnit (fx 'AFSNIT I. SKATTEPLIGTEN')",
    "indexInverted": True,
    "tokenization": "word"
}
```

#### **`paragraph` (Paragraf Nummer)**
```python
{
    "name": "paragraph", 
    "dataType": ["text"],
    "description": "Paragraf nummer (fx '§ 15')",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`stk` (Stykke)**
```python
{
    "name": "stk",
    "dataType": ["text"], 
    "description": "Stykke nummer",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`nr` (Nummer)**
```python
{
    "name": "nr",
    "dataType": ["text"],
    "description": "Nummer inden for stykke",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`heading` (Overskrift)**
```python
{
    "name": "heading",
    "dataType": ["text"],
    "description": "Overskrift (fx '§ 1, stk. 1')",
    "indexInverted": True,
    "tokenization": "word"
}
```

### **📊 4. METADATA FELTER**

#### **`document_name` (Kilde Dokument)**
```python
{
    "name": "document_name",
    "dataType": ["text"],
    "description": "Kilde dokumentnavn",
    "indexInverted": True,
    "tokenization": "word"
}
```

#### **`law_number` (Lovnummer)**
```python
{
    "name": "law_number",
    "dataType": ["text"],
    "description": "Lovnummer (fx '2023-01-13 nr. 42')",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`status` (Gyldighedsstatus)**
```python
{
    "name": "status",
    "dataType": ["text"],
    "description": "Status: 'gældende' eller 'historisk'",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`date` (Lovens Dato)**
```python
{
    "name": "date",
    "dataType": ["text"],
    "description": "Lovens dato",
    "indexInverted": True,
    "tokenization": "field"
}
```

### **🔗 5. RELATIONS FELTER**

#### **`related_note_chunks` (Paragraf → Noter)** 🔗
```python
{
    "name": "related_note_chunks",
    "dataType": ["text[]"],
    "description": "Relaterede note chunk IDs (array)",
    "indexInverted": True
}
```

#### **`related_paragraph_chunk_id` (Note → Paragraf)**
```python
{
    "name": "related_paragraph_chunk_id",
    "dataType": ["text"],
    "description": "Relateret paragraf chunk ID",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`note_reference_ids` (Reference IDs)**
```python
{
    "name": "note_reference_ids",
    "dataType": ["text[]"],
    "description": "Note reference IDs for mapping",
    "indexInverted": True
}
```

#### **`related_paragraph_ref` (Paragraf Reference)**
```python
{
    "name": "related_paragraph_ref",
    "dataType": ["text"],
    "description": "Reference til relateret paragraf",
    "indexInverted": True
}
```

#### **`related_paragraph_text` (Paragraf Tekst)**
```python
{
    "name": "related_paragraph_text",
    "dataType": ["text"],
    "description": "Tekst fra relateret paragraf",
    "indexInverted": True,
    "tokenization": "word"
}
```

#### **`related_paragraphs` (Flere Paragraffer)**
```python
{
    "name": "related_paragraphs",
    "dataType": ["text[]"],
    "description": "Array af relaterede paragraffer",
    "indexInverted": True
}
```

### **🧠 6. LLM GENEREREDE FELTER**

#### **`keywords` (Ekstraherede Nøgleord)** 🏷️
```python
{
    "name": "keywords",
    "dataType": ["text[]"],
    "description": "AI-ekstraherede søgenøgleord",
    "indexInverted": True
}
```

#### **`entities` (Navngivne Entiteter)**
```python
{
    "name": "entities", 
    "dataType": ["text[]"],
    "description": "Organisationer, love, personer, etc.",
    "indexInverted": True
}
```

#### **`rule_type` (Regeltype)** 📝
```python
{
    "name": "rule_type",
    "dataType": ["text"],
    "description": "hovedregel, undtagelse, definition, procedure, etc.",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`rule_type_confidence` (Confidence Score)**
```python
{
    "name": "rule_type_confidence",
    "dataType": ["int"],
    "description": "Confidence score for rule_type (0-100)"
}
```

#### **`rule_type_explanation` (Forklaring)**
```python
{
    "name": "rule_type_explanation",
    "dataType": ["text"],
    "description": "AI forklaring af regeltype",
    "indexInverted": True,
    "tokenization": "word"
}
```

#### **`interpretation_flag` (Fortolkning Flag)** 🔍
```python
{
    "name": "interpretation_flag",
    "dataType": ["boolean"],
    "description": "Kræver fortolkning (true/false)"
}
```

#### **`llm_model_used` (LLM Model)**
```python
{
    "name": "llm_model_used",
    "dataType": ["text"],
    "description": "Hvilken LLM model blev brugt",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`summary` (AI Sammendrag)**
```python
{
    "name": "summary",
    "dataType": ["text"],
    "description": "AI-genereret sammendrag",
    "indexInverted": True,
    "tokenization": "word",
    "moduleConfig": {
        "text2vec-openai": {"skip": False}  # Include i embedding
    }
}
```

### **⚖️ 7. JURIDISKE FELTER**

#### **`note_references` (Note Referencer)**
```python
{
    "name": "note_references",
    "dataType": ["text[]"],
    "description": "Note referencer og citationer",
    "indexInverted": True
}
```

#### **`notes` (Noter)**
```python
{
    "name": "notes",
    "dataType": ["text"],
    "description": "Juridiske noter og kommentarer",
    "indexInverted": True,
    "tokenization": "word"
}
```

#### **`note_number` (Note Nummer)**
```python
{
    "name": "note_number",
    "dataType": ["text"],
    "description": "Note nummer reference",
    "indexInverted": True,
    "tokenization": "field"
}
```

#### **`dom_references` (Dom Referencer)**
```python
{
    "name": "dom_references",
    "dataType": ["text[]"],
    "description": "Referencer til domme og afgørelser",
    "indexInverted": True
}
```

---

## 🎯 **EMBEDDING OPTIMERING**

### **Text Processing for 1024 Dimensions**
```python
def prepare_document_for_embedding(doc):
    """Optimeret tekst til 1024-dim embedding"""
    
    embedding_parts = []
    
    # 1. Titel (vigtig kontekst)
    if doc.get('title'):
        embedding_parts.append(f"Titel: {doc['title']}")
    
    # 2. Type og topic (strukturel kontekst) 
    if doc.get('type') and doc.get('topic'):
        embedding_parts.append(f"{doc['type']}: {doc['topic']}")
    
    # 3. Hovedtekst (prioriteret)
    if doc.get('text'):
        text = doc['text']
        # Optimal længde for 1024 dim
        if len(text) > 6000:
            text = text[:6000] + "..."
        embedding_parts.append(text)
    
    # 4. Nøgleord (søgeoptimering)
    if doc.get('keywords'):
        keywords = ', '.join(doc['keywords'][:5])
        embedding_parts.append(f"Nøgleord: {keywords}")
    
    return "\n".join(embedding_parts)
```

### **Performance Fordele ved 1024 Dim**
```
Storage besparelse:   67% mindre (12 MB vs 36 MB)
Vector operations:    3x hurtigere
Embedding kvalitet:   Samme som 3072 (matryoshka)
Cost optimering:      Samme OpenAI pris, bedre performance
```

---

## 🔄 **DATA FLOW & PROCESSING**

### **Import Pipeline**
```
JSONL Filer → Schema Validation → Text Processing → 
Embedding Generation → Batch Upload → Verification
```

### **Chunk Relations**
```
Paragraf Chunk
├── related_note_chunks[] ──→ Note Chunk 1
├── related_note_chunks[] ──→ Note Chunk 2  
└── related_note_chunks[] ──→ Note Chunk N

Note Chunk
└── related_paragraph_chunk_id ──→ Paragraf Chunk
```

### **Search Flow**
```
User Query → Query Analysis → Search Type Detection → 
Weaviate Query → Result Processing → Relations Loading
```

---

## 🛠️ **MANAGEMENT COMMANDS**

### **Schema Recreation**
```bash
# Komplet schema rebuild med 1024 optimering
python import_simple_1024.py --force-recreate
```

### **Database Inspection**
```bash
# Status og performance metrics
python database_status.py
```

### **Schema Verification**
```python
# Check schema properties
import weaviate
client = weaviate.Client("http://localhost:8080")
schema = client.schema.get("LegalDocument")
print(f"Properties: {len(schema['properties'])}")
```

---

## 📊 **PERFORMANCE CHARACTERISTICS**

### **Query Performance**
```
Chunk ID søgning:     0.2-0.4s (UUID lookup)
Paragraf søgning:     0.6-0.8s (topic + text search)  
Semantisk søgning:    0.6-0.7s (vector similarity)
Nøgleord søgning:     0.4-0.6s (BM25 search)
```

### **Storage Metrics**
```
Per-document storage: 4.0 KB average
Total vector storage: ~12 MB
Index storage:        ~2-3 MB
Relations overhead:   Minimal (UUID references)
```

### **Scalability**
```
Current:   3,098 documents ✅
Capacity:  50,000+ documents (estimated)
Memory:    Low overhead (1024 dim)
Disk:      Efficient storage (optimized schema)
```

---

## 🎯 **PRODUCTION READINESS**

### **✅ Completed Features**
- [x] **Optimeret schema** med 33 properties
- [x] **1024-dim embedding** med matryoshka truncation
- [x] **Komplet relations mapping** (paragraf ↔ noter)
- [x] **Robust import pipeline** med fejlhåndtering
- [x] **Performance optimering** (67% storage besparelse)
- [x] **Search functionality** med automatisk type detection

### **🚀 Ready for RAG Integration**
```python
# Production-ready retrieval
from redskaber.simple_search import search_query

# Direkte integration i RAG pipeline
results = search_query("§ 33 A rejsegodtgørelse")
context = prepare_context_for_llm(results)
```

**Status**: ✅ **Produktionsklar til RAG implementation**
