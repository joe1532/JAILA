# Simple Search - Legal Document Retrieval System

## Overblik

`simple_search.py` er et komplet retrieval system til søgning i juridiske dokumenter opbevaret i Weaviate vector database. Systemet anvender **kun retrieval funktionalitet** uden LLM-integration og understøtter flere forskellige søgemetoder med intelligent type-detection.

## 🎯 Hovedfunktioner

### Søgetyper
1. **Chunk ID Søgning** - Direkte UUID-baseret opslag
2. **Paragraf Søgning** - § referencer (§ 33 A, § 15, paragraf 8)
3. **Semantisk Søgning** - AI-baseret vector search
4. **Nøgleord Søgning** - Tekstbaseret LIKE-søgning
5. **Automatisk Søgning** - Intelligent type detection

### Brugergrænseflader
- **Kommandolinje**: `python simple_search.py "søgeord"`
- **Interaktiv menu**: 6 valgmuligheder med tilpassede prompts
- **Kommando interface**: `c:`, `p:`, `s:`, `k:` prefixer

## 🛠️ Installation og Setup

### Forudsætninger
```bash
pip install weaviate-client python-dotenv
```

### Miljøvariabler
Opret `.env` fil:
```
OPENAI_API_KEY=din_openai_api_key
```

### Weaviate Server
Kør lokalt på `http://localhost:8080` (Docker eller lokal installation)

## 📋 Brug

### Kommandolinje (Hurtigst)
```bash
# Automatisk detection
python simple_search.py "§ 33 A"                    # Paragraf søgning
python simple_search.py "fradrag"                   # Semantisk søgning
python simple_search.py "uuid-chunk-id"             # Chunk ID søgning

# Eksempler
python simple_search.py "b4f17c6b-09ef-487e-a416-c0521419feee"
python simple_search.py "§ 15"
python simple_search.py "skattefradrag"
```

### Interaktiv Menu
```bash
python simple_search.py

# Valgmuligheder:
# 1. Automatisk (prøver chunk ID, paragraf, derefter semantisk)
# 2. Kun chunk ID søgning
# 3. Kun paragraf søgning
# 4. Kun semantisk søgning
# 5. Kun nøgleord søgning
# 6. Interaktiv søgning
```

### Kommando Interface (Option 6)
```bash
c:uuid-her          # Chunk ID søgning
p:§ 33 A            # Paragraf søgning
s:skattefradrag     # Semantisk søgning
k:skat              # Nøgleord søgning
almindeligt ord     # Automatisk detection
```

## 🔍 Søgefunktioner - Detaljeret

### 1. Chunk ID Søgning (`chunk_search()`)

**Formål**: Direkte opslag på UUID chunk identifiers

**Input**: UUID format `8-4-4-4-12` tegn med bindestreger

**Funktionalitet**:
- Finder specifikt chunk
- **Automatisk relationship følgning**:
  - Hvis `type="paragraf"` → henter relaterede noter
  - Hvis `type="notes"` → henter relateret paragraf
- Viser komplette relationer

**Eksempel**:
```python
# Input: "b4f17c6b-09ef-487e-a416-c0521419feee"
# Output: Note chunk + relateret § 33 A paragraf
```

### 2. Paragraf Søgning (`paragraph_search()`)

**Formål**: Søgning efter juridiske paragraf-referencer

**Regex Patterns**:
```python
r'§\s*(\d+\s*[a-zA-Z]*)'       # § 15, § 33 A, § 15a
r'paragraf\s*(\d+\s*[a-zA-Z]*)'  # paragraf 15, paragraf 33 A
r'section\s*(\d+\s*[a-zA-Z]*)'   # section 15, section 33 A
r'stk\.?\s*(\d+)'                # stk. 15, stk 15
```

**Søgelogik**:
1. **Prioriteret søgning** - mest specifikke først
2. **Case-insensitive** - både "§ 33 A" og "§ 33 a"
3. **Topic søgning først** (højest relevans)
4. **Text søgning** som fallback
5. **Automatisk noter** - henter relaterede noter

**Prioriterede patterns**:
```python
f"§ {paragraph_ref.lower()}"    # "§ 33 a" - præcis topic match
f"§ {paragraph_ref}"            # "§ 33 A" - præcis input match  
paragraph_ref.lower()           # "33 a" - kort topic match
paragraph_ref                   # "33 A" - kort input match
```

### 3. Semantisk Søgning (`semantic_search()`)

**Formål**: AI-baseret begrebssøgning

**Teknologi**: Weaviate `with_near_text()` med OpenAI embeddings

**Eksempler**:
```python
semantic_search("fradrag")        # Finder fradrag-relaterede dokumenter
semantic_search("skattelempelse") # Finder lempelse-relaterede dokumenter
```

### 4. Nøgleord Søgning (`keyword_search()`)

**Formål**: Direkte tekstmatch i dokumenter

**Operator**: `Like` med wildcards (`*søgeord*`)

**Søger i**: `text` felt

## 🧠 Intelligent Detection

### Automatic Type Detection (`search_query()`)

**Logik**:
1. **UUID check** → Chunk ID søgning
2. **§ pattern check** → Paragraf søgning  
3. **Almindelige ord** → Semantisk søgning
4. **Fallback** → Nøgleord søgning

**Implementering**:
```python
def search_query(query):
    if detect_chunk_id(query):
        return chunk_search(query)
    
    paragraph_results = paragraph_search(query)
    if paragraph_results:
        return paragraph_results
        
    semantic_results = semantic_search(query)
    if semantic_results:
        return semantic_results
        
    return keyword_search(query)  # Fallback
```

### UUID Detection (`detect_chunk_id()`)

**Pattern**: `^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`

### Paragraf Detection (`detect_paragraph_references()`)

**Normalisering**:
- Trim whitespace
- Uppercase letters
- Dubletter fjernet

## 📊 Database Schema

### Anvendte Felter (`ALL_FIELDS`)
```python
[
    "chunk_id",                    # UUID identifier
    "title",                       # Dokument titel
    "text",                        # Hovedtekst
    "text_for_embedding",          # Embedding tekst
    "type",                        # "paragraf" | "notes"
    "topic",                       # § reference
    "keywords",                    # Søgenøgleord (list)
    "entities",                    # Navngivne entiteter
    "rule_type",                   # "hovedregel" | "undtagelse" | etc.
    "law_number",                  # Lovnummer
    "status",                      # "gældende" | etc.
    "note_reference_ids",          # Relaterede noter (list)
    "related_note_chunks",         # Note chunk IDs (list)
    "related_paragraph_chunk_id",  # Paragraf chunk ID
    "summary",                     # Sammendrag
    "dom_references",              # Domstolsreferencer
    "date",                        # Dato
    "document_name"                # Dokumentnavn
]
```

### Type Værdier
- `"paragraf"` - Juridiske paragraffer
- `"notes"` - Forklarende noter

### Relationships
```
paragraf.related_note_chunks[] ←→ notes.related_paragraph_chunk_id
```

## 🎨 Output Format

### Resultat Struktur
```
📄 RESULTAT 1:
   ID: chunk-id-uuid
   Type: paragraf|notes
   Titel: Dokumenttitel
   Topic: § reference
   Lov: Lovnummer
   Status: gældende
   Keywords: keyword1, keyword2, keyword3
   Rule type: hovedregel|undtagelse|fortolkning
   Relaterede noter: N stk        # Kun for paragraffer
   Relateret paragraf: chunk-id   # Kun for noter
   Tekst: Første 200 tegn...
   ------------------------------------------------------------
```

## ⚙️ Konfiguration

### Weaviate Forbindelse
```python
client = weaviate.Client(
    url="http://localhost:8080",
    additional_headers={"X-OpenAI-Api-Key": openai_api_key}
)
```

### Søgegrænser
- **Default limit**: 5 resultater
- **Topic søgning**: max 5 per pattern
- **Text søgning**: max 3 per pattern  
- **Noter per paragraf**: max 1 (undgår overload)

### Error Handling
- **Weaviate connection errors**
- **Missing environment variables**
- **Query execution errors**
- **Graceful degradation**

## 🐛 Fejlfinding

### Almindelige Problemer

**1. Ingen resultater for § søgning**
```bash
# Problem: Forkert format
python simple_search.py "33 A"

# Løsning: Brug § symbol
python simple_search.py "§ 33 A"
```

**2. Weaviate connection error**
```bash
# Check at Docker kører
docker ps | grep weaviate

# Start Weaviate
./start_docker.bat
```

**3. OpenAI API key fejl**
```bash
# Check .env fil
cat .env | grep OPENAI_API_KEY
```

**4. Paragraf søgning finder ikke almindelige ord**
```bash
# Problem: Option 3 med "fradrag"
# Løsning: Brug option 1 (Automatisk) eller 4 (Semantisk)
```

### Debug Mode
Tilføj debug print til functions for detaljeret logging.

## 📈 Performance

### Søgehastighed
1. **Chunk ID**: Hurtigst (direkte lookup)
2. **Paragraf**: Middel (topic + text søgning)
3. **Semantisk**: Langsomst (embedding calculation)
4. **Nøgleord**: Hurtig (Like operator)

### Optimering
- **Topic søgning prioriteres** for paragraffer
- **Early stopping** når limit nås
- **Deduplication** forhindrer dubletter
- **Begrænset noter** per paragraf

## 🔒 Sikkerhed

### Input Validation
- UUID format validation
- Regex-baseret § detection
- SQL injection protection (Weaviate queries)

### API Key Protection
- Environment variables
- Ikke hardcoded credentials

## 🚀 Udvidelsesmuligheder

### Nye Søgetyper
```python
def advanced_search(query, filters=None):
    # Implementer filtrering på law_number, date, etc.
    pass

def fuzzy_search(query, threshold=0.8):
    # Implementer fuzzy matching
    pass
```

### Performance Optimering
- Caching af ofte brugte queries
- Batch processing for multiple queries
- Connection pooling

### UI Integration
- Web interface med Streamlit
- API endpoints for external integration
- Export functionality (JSON, CSV)

## 📚 Eksempler

### Typiske Use Cases

**Juridisk Research**:
```bash
python simple_search.py "§ 33 A"     # Find specifik paragraf
python simple_search.py "fradrag"    # Find fradrag-relateret
python simple_search.py "lempelse"   # Find lempelse-regler
```

**Chunk Navigation**:
```bash
# Fra paragraf til noter
python simple_search.py "c97b7c36-f5d9-4589-ae8f-bf5a773de1be"

# Fra note til paragraf  
python simple_search.py "b4f17c6b-09ef-487e-a416-c0521419feee"
```

**Interaktiv Udforskning**:
```bash
python simple_search.py
# Vælg 6 (Interaktiv)
# Brug p:, s:, k: kommandoer
```

## 🔄 Vedligeholdelse

### Regular Tasks
1. **Database backup** af Weaviate data
2. **Log monitoring** for errors
3. **Performance metrics** tracking
4. **Index optimization** i Weaviate

### Updates
- **Regex patterns** for nye § formater
- **Field mapping** ved schema ændringer  
- **Error handling** improvements
- **New search functionality**

---

## 🏷️ Version Info

**Current Version**: 1.0  
**Last Updated**: December 2024  
**Python Requirements**: 3.8+  
**Dependencies**: weaviate-client, python-dotenv  

**Author**: AI Assistant  
**Purpose**: Legal document retrieval for Danish law  
**License**: Internal use 