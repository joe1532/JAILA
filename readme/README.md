# JAILA - Juridisk AI og LangChain Applikation

JAILA er et avanceret juridisk RAG-system (Retrieval-Augmented Generation), der kombinerer vektorsøgning via Weaviate med LangChain's multihop RAG-funktionalitet til at besvare komplekse juridiske spørgsmål med høj præcision.

## Indhold

- [Oversigt](#oversigt)
- [Funktioner](#funktioner)
- [Installation](#installation)
- [Konfiguration](#konfiguration)
- [Brug](#brug)
- [Systemarkitektur](#systemarkitektur)
- [Docker-integration](#docker-integration)
- [Avanceret brug](#avanceret-brug)

## Oversigt

JAILA er designet til at hjælpe med at besvare komplekse juridiske spørgsmål ved at:

1. Nedbryde komplekse juridiske spørgsmål i flere, mere specifikke delspørgsmål
2. Søge efter relevant information for hvert delspørgsmål i en Weaviate vektordatabase
3. Sammenfatte delresultaterne til et sammenhængende, juridisk korrekt svar

Systemet bruger Weaviate som vektordatabase og OpenAI's sprogmodeller til forståelse og generering af svar.

## Funktioner

- **Multihop juridisk søgning**: Nedbryder komplekse spørgsmål i delspørgsmål for mere præcise svar
- **Standard juridisk søgning**: Direkte søgning for enklere spørgsmål
- **Hybrid søgning**: Kombinerer vektorsøgning og nøgleordssøgning for optimal præcision
- **Avanceret retriever**: Bruger MultiQueryRetriever når tilgængelig for forbedrede søgeresultater
- **Fejlhåndtering**: Robust håndtering af situationer hvor Weaviate ikke er tilgængelig
- **Modulariseret kodebase**: Velorganiseret kode for nem vedligeholdelse og udvidelse

## Installation

### Forudsætninger

- Python 3.8+
- Docker (til at køre Weaviate)
- OpenAI API-nøgle

### Komplet trin-for-trin vejledning

Følg denne vejledning for at genskabe hele opsætningen fra bunden:

#### 1. Opsæt projektmappen

```bash
# Opret projektmappe
mkdir -p c:\Skatdata\Weaviate
cd c:\Skatdata\Weaviate

# Opret de nødvendige undermapper
mkdir -p JAILA
mkdir -p docker
mkdir -p backup\weaviate_data
```

#### 2. Opret JAILA-modulet

Opret følgende filer i JAILA-mappen:

```bash
# Opret __init__.py
touch JAILA\__init__.py

# Opret de andre moduler
touch JAILA\config.py
touch JAILA\connections.py
touch JAILA\prompts.py
touch JAILA\retrieval.py
touch JAILA\utils.py
touch JAILA\test.py
```

Udfyld filerne med kode fra GitHub-repositoriet eller de filer, vi har oprettet.

#### 3. Opret Docker-konfiguration

Opret følgende filer i docker-mappen:

```bash
# Opret docker-compose.yml
touch docker\docker-compose.yml

# Opret Dockerfiles
touch docker\Dockerfile.app
touch docker\Dockerfile.streamlit

# Opret requirements-filer
touch docker\requirements.txt
touch docker\streamlit-requirements.txt
```

Udfyld docker-compose.yml med følgende indhold:

```yaml
version: '3.8'

services:
  # Weaviate vektor-database
  weaviate:
    image: semitechnologies/weaviate:1.23.7
    ports:
      - "8080:8080"
    restart: on-failure:0
    environment:
      QUERY_DEFAULTS_LIMIT: 25
      AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED: 'true'
      PERSISTENCE_DATA_PATH: '/var/lib/weaviate'
      DEFAULT_VECTORIZER_MODULE: 'text2vec-openai'
      ENABLE_MODULES: 'text2vec-openai,text2vec-huggingface,ref2vec-centroid,generative-openai'
      OPENAI_APIKEY: ${OPENAI_API_KEY}
      CLUSTER_HOSTNAME: 'node1'
    volumes:
      - ../backup/weaviate_data:/var/lib/weaviate
    networks:
      - legal-rag-network

  # RAG applikation backend
  rag-app:
    build:
      context: ..
      dockerfile: docker/Dockerfile.app
    ports:
      - "8000:8000"
    environment:
      WEAVIATE_URL: http://weaviate:8080
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    volumes:
      - ../data:/app/data
    depends_on:
      - weaviate
    networks:
      - legal-rag-network

  # Streamlit frontend
  streamlit:
    build:
      context: ..
      dockerfile: docker/Dockerfile.streamlit
    ports:
      - "8501:8501"
    environment:
      RAG_API_URL: http://rag-app:8000
    depends_on:
      - rag-app
    networks:
      - legal-rag-network

networks:
  legal-rag-network:
```

#### 4. Opsæt import_simple.py

Opret import_simple.py i rodmappen med følgende indhold:

```python
# import_simple.py - Importerer juridiske dokumenter til Weaviate

import weaviate
import json
import os
from typing import Dict, Any, List
from dotenv import load_dotenv
import glob

# Indlæs miljøvariabler
load_dotenv()

# Konfiguration
WEAVIATE_URL = os.environ.get("WEAVIATE_URL", "http://localhost:8080")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
CLASS_NAME = "LegalDocument"
JSONL_DIR = "embedder/output"

def check_weaviate_connection():
    """Tjekker om Weaviate-serveren kører og er tilgængelig"""
    import requests
    try:
        response = requests.get(f"{WEAVIATE_URL}/v1/.well-known/ready", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False

def create_schema(client):
    """Opretter schema i Weaviate"""
    class_obj = {
        "class": CLASS_NAME,
        "vectorizer": "text2vec-openai",
        "moduleConfig": {
            "text2vec-openai": {
                "model": "ada",
                "modelVersion": "002",
                "type": "text"
            }
        },
        "properties": [
            {"name": "text", "dataType": ["text"]},
            {"name": "text_for_embedding", "dataType": ["text"], "moduleConfig": {"text2vec-openai": {"skip": False}}},
            {"name": "chunk_id", "dataType": ["string"]},
            {"name": "title", "dataType": ["string"], "indexInverted": True},
            {"name": "law_number", "dataType": ["string"], "indexInverted": True},
            {"name": "paragraph", "dataType": ["string"], "indexInverted": True},
            {"name": "stk", "dataType": ["string"], "indexInverted": True},
            {"name": "nr", "dataType": ["string"], "indexInverted": True},
            {"name": "heading", "dataType": ["text"], "indexInverted": True},
            {"name": "summary", "dataType": ["text"], "indexInverted": True}
        ]
    }
    
    # Tjek om klassen allerede eksisterer
    try:
        schema = client.schema.get()
        classes = [c["class"] for c in schema["classes"]] if "classes" in schema else []
        
        if CLASS_NAME in classes:
            print(f"Klassen {CLASS_NAME} eksisterer allerede.")
            return
            
        print("Opretter nyt schema...")
        client.schema.create_class(class_obj)
        print("Schema oprettet.")
    except Exception as e:
        print(f"Fejl ved oprettelse af schema: {e}")
        raise

def import_data(file_path):
    """Importerer data fra en JSONL-fil til Weaviate"""
    print(f"Importerer data fra {file_path}...")
    client = get_weaviate_client()
    
    objects_imported = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            try:
                obj = json.loads(line)
                
                # Oprette et dict med de primære felter
                data_object = {
                    "text": obj.get("text", ""),
                    "text_for_embedding": obj.get("text_for_embedding", obj.get("text", "")),
                    "chunk_id": obj.get("chunk_id", ""),
                    "title": obj.get("title", ""),
                    "law_number": obj.get("law_number", ""),
                    "paragraph": obj.get("paragraph", ""),
                    "stk": obj.get("stk", ""),
                    "nr": obj.get("nr", ""),
                    "heading": obj.get("heading", ""),
                    "summary": obj.get("summary", "")
                }
                
                # Indsæt i Weaviate
                client.data_object.create(
                    data_object,
                    CLASS_NAME,
                    vector=None  # Vektoren genereres automatisk via text2vec-openai
                )
                
                objects_imported += 1
                if objects_imported % 100 == 0:
                    print(f"Behandlet {objects_imported} objekter...")
                    
            except json.JSONDecodeError:
                print(f"Linje {i} er ikke gyldig JSON, springer over")
            except Exception as e:
                print(f"Fejl ved import af objekt {i}: {e}")
    
    print(f"Import afsluttet. {objects_imported} objekter importeret.")
    return objects_imported

def get_weaviate_client():
    """Opretter forbindelse til Weaviate"""
    try:
        client = weaviate.Client(
            url=WEAVIATE_URL,
            additional_headers={
                "X-OpenAI-Api-Key": OPENAI_API_KEY
            }
        )
        return client
    except Exception as e:
        print(f"Fejl ved oprettelse af Weaviate-klient: {e}")
        return None

def main():
    print("Opretter forbindelse til Weaviate...")
    if not check_weaviate_connection():
        print(f"Kan ikke forbinde til Weaviate på {WEAVIATE_URL}. Sikr dig, at Weaviate-serveren kører.")
        return
        
    print("Forbindelse til Weaviate oprettet!")
    client = get_weaviate_client()
    
    if not client:
        print("Kunne ikke oprette Weaviate-klient.")
        return
    
    print("Kontrollerer eksisterende skema...")
    create_schema(client)
    
    # Find JSONL-filer i den angivne mappe
    jsonl_files = glob.glob(f"{JSONL_DIR}/*.jsonl")
    if not jsonl_files:
        print(f"Ingen JSONL-filer fundet i: {JSONL_DIR}")
        return
        
    print(f"Leder efter JSONL-filer i: {JSONL_DIR}")
    for file_path in jsonl_files:
        import_data(file_path)
    
    print("Alle data er blevet importeret.")

if __name__ == "__main__":
    main()
```

#### 5. Opret .env fil

Opret en .env fil i rodmappen med dine API-nøgler:

```
OPENAI_API_KEY=din_openai_api_nøgle_her
WEAVIATE_URL=http://localhost:8080
```

#### 6. Installer pakker

Installer de nødvendige Python-pakker:

```bash
pip install langchain langchain-openai langchain-community weaviate-client python-dotenv
```

#### 7. Start Docker-containere

```bash
cd docker
docker-compose up -d
```

#### 8. Importer data

For at importere juridiske dokumenter:

1. Opret mappen `embedder/output` og placer dine JSONL-filer her
2. Kør import-scriptet:

```bash
python import_simple.py
```

#### 9. Test systemet

Test, at alt fungerer korrekt:

```bash
python -c "import JAILA; print(f'JAILA-pakken importeret korrekt: version {JAILA.__version__}')"
```

Derefter kan du køre en komplet test:

```bash
python JAILA/test.py
```

#### 10. Brug systemet

Nu kan du bruge JAILA i dine applikationer:

```python
from JAILA import multihop_juridisk_søgning

resultat = multihop_juridisk_søgning("Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel?")
print(resultat["answer"])
```

### Installation via pip

```bash
# Installer de nødvendige pakker
pip install langchain langchain-openai langchain-community weaviate-client python-dotenv
```

### Manuel installation

```bash
git clone https://github.com/din-organisation/JAILA.git
cd JAILA
pip install -r requirements.txt
```

## Konfiguration

1. Opret en `.env` fil i projektets rod med følgende indhold:

```
OPENAI_API_KEY=din_openai_api_nøgle
WEAVIATE_URL=http://localhost:8080
```

2. Start Weaviate med Docker:

```bash
cd docker
docker-compose up -d
```

3. Importer dine juridiske dokumenter:

```bash
python import_simple.py
```

## Brug

### Grundlæggende brug

```python
from JAILA import multihop_juridisk_søgning

# Stil et komplekst juridisk spørgsmål
spørgsmål = "Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel, og hvordan påvirker det beregningen af skatten?"

# Få et detaljeret svar
resultat = multihop_juridisk_søgning(spørgsmål)

# Vis svaret
print(resultat["answer"])
```

### Integration med Streamlit

```python
import streamlit as st
from JAILA import multihop_juridisk_søgning

st.title("Juridisk AI-assistent")

# Håndtering af brugerinput
query = st.text_input("Stil et juridisk spørgsmål:")
if st.button("Søg med multihop RAG"):
    with st.spinner("Analyserer spørgsmål og finder relevant information..."):
        result = multihop_juridisk_søgning(query)
        st.write(result["answer"])
```

## Systemarkitektur

JAILA består af følgende hovedkomponenter:

- **config.py**: Konfigurationsindstillinger og konstanter
- **connections.py**: Håndtering af forbindelser til Weaviate
- **prompts.py**: Skabeloner til LLM-prompts
- **retrieval.py**: Funktioner til dokumenthentning og RAG
- **utils.py**: Hjælpefunktioner
- **test.py**: Test-funktionalitet

### Projektstruktur

```
Skatdata/Weaviate/
│
├── README.md                  # Denne dokumentation
├── langchain_integration.py   # Wrapper for bagudkompatibilitet
├── langchain_integration_backup.py  # Backup af den originale fil
├── import_simple.py           # Import-script til Weaviate
│
├── JAILA/                     # Hovedmodul for Juridisk AI
│   ├── __init__.py            # Eksporterer hovedfunktioner
│   ├── config.py              # Konfigurationsindstillinger
│   ├── connections.py         # Forbindelser til Weaviate
│   ├── prompts.py             # LLM prompt-skabeloner
│   ├── retrieval.py           # RAG-funktionalitet
│   ├── utils.py               # Hjælpefunktioner
│   └── test.py                # Test-funktionalitet
│
├── backup/                    # Backup af Weaviate-data
│   └── weaviate_data/         # Persistente data for Weaviate
│
└── docker/                    # Docker-konfiguration
    ├── docker-compose.yml     # Docker Compose konfiguration
    ├── Dockerfile.app         # Dockerfile til backend
    ├── Dockerfile.streamlit   # Dockerfile til frontend
    ├── requirements.txt       # Backend-afhængigheder
    └── streamlit-requirements.txt  # Frontend-afhængigheder
```

### Dataflow

1. Bruger stiller et komplekst juridisk spørgsmål
2. Spørgsmålet nedbrydes i delspørgsmål af LLM
3. Relevante dokumenter hentes for hvert delspørgsmål
4. LLM genererer svar for hvert delspørgsmål baseret på dokumenterne
5. Alle delresultater sammenfattes til et endeligt svar

## Docker-integration

JAILA bruger Docker til at køre Weaviate-databasen. Docker-opsætningen omfatter:

- **Weaviate**: Vektordatabase med OpenAI-integration
- **RAG-app**: Backend-API for juridisk søgning
- **Streamlit**: Brugervenlig frontend

Start containerne med:

```bash
cd docker
docker-compose up -d
```

## Multihop RAG-teknologi

### Hvad er Multihop RAG?

Multihop Retrieval-Augmented Generation (Multihop RAG) er en avanceret variant af standard RAG-systemer, der er særligt effektiv til at besvare komplekse spørgsmål, der kræver flere lag af ræsonnement.

I standard RAG hentes relevante dokumenter baseret på brugerens spørgsmål, og derefter genererer en sprogmodel et svar baseret på disse dokumenter. Ved komplekse spørgsmål har denne tilgang begrænsninger, da:

1. Komplekse spørgsmål ofte indeholder flere delspørgsmål
2. Et enkelt opslag sjældent finder alle relevante dokumenter
3. Relevansen af dokumenter kan være svær at bestemme for det samlede spørgsmål

### Sådan fungerer JAILA's multihop-proces

JAILA implementerer multihop RAG i tre hovedtrin:

#### 1. Spørgsmålsnedbrydning

```
Input: "Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel, og hvordan påvirker det beregningen af skatten?"

Output (delspørgsmål):
- Hvad er de specifikke dokumentationskrav for at få fradrag for udgifter til erhvervsmæssig kørsel?
- Hvordan påvirker manglende opfyldelse af dokumentationskravene beregningen af skatten?
- Er der eventuelle undtagelser eller særlige regler, der gælder for visse typer af udgifter til erhvervsmæssig kørsel?
```

#### 2. Retrieval og svar på delspørgsmål

For hvert delspørgsmål:
- Hent relevante dokumenter fra Weaviate vektordatabasen
- Generer et svar baseret på de fundne dokumenter
- Gem svaret som et delresultat

#### 3. Syntese af endeligt svar

- Kombiner alle delresultater til en samlet kontekst
- Generer et endeligt, sammenhængende svar der adresserer det oprindelige spørgsmål

### Fordele ved multihop RAG

- **Højere præcision**: Finder mere specifik information relevant for hvert aspekt af spørgsmålet
- **Bedre kildeidentifikation**: Kan spore hvilke kilder der bidrog til hvilke dele af svaret
- **Kompleks ræsonnement**: Kan håndtere juridiske spørgsmål der kræver flere lag af analyse
- **Transparens**: Giver indsigt i ræsonnementskæden gennem delspørgsmål og -svar

### Implementering i koden

```python
# Hovedfunktionen for multihop RAG findes i JAILA/retrieval.py
from JAILA import multihop_juridisk_søgning

# Promptskabeloner for de forskellige trin findes i JAILA/prompts.py
from JAILA.prompts import create_multihop_prompt_templates

# Se funktionen multihop_juridisk_søgning for detaljer om implementeringen
```

## Træning med nye juridiske dokumenter

JAILA kan nemt udvides til at håndtere nye typer juridiske dokumenter. Denne sektion beskriver processen for at tilføje nye dokumenter til systemet.

### Forberedelse af dokumenter

1. **Dokumentstruktur**: Juridiske dokumenter bør følge en konsistent struktur for optimal indeksering
2. **Metadata**: Inkluder relevante metadata som lov-nummer, paragraf, stykke, mv.
3. **Opdeling**: Store dokumenter bør opdeles i mindre semantiske enheder (chunks)

### Import-processen

```python
# Eksempel på importering af nye dokumenter

import json
import os
from JAILA.connections import get_weaviate_client
from JAILA.config import CLASS_NAME
from JAILA.utils import split_text_into_chunks

def import_nye_dokumenter(fil_sti):
    # Få Weaviate-klient
    client = get_weaviate_client()
    
    # Læs JSONL-fil
    with open(fil_sti, 'r', encoding='utf-8') as f:
        for line in f:
            obj = json.loads(line)
            
            # Forbered data-objekt med de nødvendige felter
            data_object = {
                "text": obj.get("text", ""),
                "text_for_embedding": obj.get("text_for_embedding", obj.get("text", "")),
                "chunk_id": obj.get("chunk_id", ""),
                "title": obj.get("title", ""),
                "law_number": obj.get("law_number", ""),
                "paragraph": obj.get("paragraph", ""),
                "stk": obj.get("stk", ""),
                "nr": obj.get("nr", ""),
                "heading": obj.get("heading", ""),
                "summary": obj.get("summary", "")
            }
            
            # Indsæt i Weaviate
            client.data_object.create(
                data_object,
                CLASS_NAME,
                vector=None  # Vektoren genereres automatisk via text2vec-openai
            )
```

### Konvertering af forskellige dokumentformater

JAILA forventer dokumenter i JSONL-format med specifikke felter. Brug disse guides til at konvertere fra forskellige formater:

#### PDF til JSONL

```python
import fitz  # PyMuPDF
import json
import re
import uuid

def pdf_to_jsonl(pdf_path, output_path, chunk_size=1000):
    # Åbn PDF
    doc = fitz.open(pdf_path)
    
    # Udtræk titel fra filnavn
    title = os.path.basename(pdf_path).replace('.pdf', '')
    
    # Udtræk lovnummer med regex hvis muligt
    law_number_match = re.search(r'(LBK|BEK)\s+nr\s+\d+', title)
    law_number = law_number_match.group(0) if law_number_match else ""
    
    full_text = ""
    # Kombiner tekst fra alle sider
    for page in doc:
        full_text += page.get_text()
    
    # Del teksten i chunks
    chunks = split_text_into_chunks(full_text, chunk_size=chunk_size)
    
    # Gem som JSONL
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            obj = {
                "chunk_id": f"{title}-{i}",
                "text": chunk,
                "title": title,
                "law_number": law_number,
                # Forsøg at udtrække paragraf med regex hvis relevant
                "paragraph": extract_paragraph(chunk)
            }
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
```

#### Word-dokument til JSONL

```python
from docx import Document
import json

def docx_to_jsonl(docx_path, output_path):
    # Læs Word-dokument
    doc = Document(docx_path)
    title = os.path.basename(docx_path).replace('.docx', '')
    
    # Udtræk tekst fra afsnit
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    
    # Kombiner afsnit til større chunks
    chunks = []
    current_chunk = ""
    
    for p in paragraphs:
        if len(current_chunk) + len(p) > 1000:  # Max chunk size
            chunks.append(current_chunk)
            current_chunk = p
        else:
            current_chunk += "\n" + p if current_chunk else p
    
    if current_chunk:  # Tilføj sidste chunk
        chunks.append(current_chunk)
    
    # Gem som JSONL
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, chunk in enumerate(chunks):
            obj = {
                "chunk_id": f"{title}-{i}",
                "text": chunk,
                "title": title
            }
            f.write(json.dumps(obj, ensure_ascii=False) + '\n')
```

### Anbefalinger til dokumentforberedelse

1. **Semantisk meningsfulde chunks**: Del dokumenter ved naturlige breaks (paragraffer, sektioner)
2. **Overlap mellem chunks**: Brug overlap mellem chunks (200-300 tegn) for at undgå tab af kontekst
3. **Metadata-berigelse**: Jo flere metadata, jo bedre filtrering og kontekst
4. **Konsistens**: Brug samme format og struktur for alle dokumenter
5. **Pre-processing**: Fjern headers, footers, sidenumre og andre irrelevante elementer

## Avanceret brug

### Tilpasning af prompter

Du kan tilpasse prompt-skabelonerne ved at redigere `JAILA/prompts.py`. Dette er nyttigt for at optimere systemets forståelse af specifikke juridiske områder.

### Hybrid søgning med filtre

```python
from JAILA import hybrid_søgning

# Søg efter specifik lovgivning med filtrering
resultater = hybrid_søgning(
    query="Kørselsfradrag beregning",
    filters={"law_number": "LBK nr 1284 af 14/11/2018"},
    limit=10
)
```

### Anvendelse i FastAPI

```python
from fastapi import FastAPI
from pydantic import BaseModel
from JAILA import multihop_juridisk_søgning

app = FastAPI()

class JuridiskSpørgsmål(BaseModel):
    spørgsmål: str

@app.post("/juridisk-ai/søg")
async def søg(forespørgsel: JuridiskSpørgsmål):
    resultat = multihop_juridisk_søgning(forespørgsel.spørgsmål)
    return resultat
```

---

## Performance-optimering og fejlfinding

### Performance-optimering

For at få den bedste ydeevne fra JAILA-systemet, kan du overveje følgende optimeringer:

#### Weaviate-optimering

1. **Vektor-indeksering**: Weaviate bruger HNSW-algoritmen til indeksering. Optimal konfiguration:

```python
# I din schema definition
client.schema.create_class({
    "class": CLASS_NAME,
    "vectorIndexConfig": {
        "skip": False,
        "ef": 128,  # Højere værdi giver bedre præcision men langsommere søgning
        "efConstruction": 128,  # Højere værdi giver bedre indeksering men tager længere tid
        "maxConnections": 64  # Antal forbindelser i HNSW-grafen
    }
})
```

2. **Sharding**: For store datasæt (>1M dokumenter), brug sharding:

```python
client.schema.create_class({
    "class": CLASS_NAME,
    "shardingConfig": {
        "virtualPerPhysical": 128,
        "desiredCount": 3,
        "actualCount": 3
    }
})
```

#### LLM og Embeddings-optimering

1. **Modelvalgc**: Balancer mellem hastighed og kvalitet:
   - For høj hastighed: `gpt-3.5-turbo`
   - For højeste kvalitet: `gpt-4` eller nyere modeller

2. **Promptoptimering**: Kalibrer prompter for at reducere token-forbrug:

```python
# Eksempel på prompt-optimering i JAILA/prompts.py
def create_optimized_prompt_templates():
    """Opretter mere token-effektive prompter"""
    # Kortere first_hop_template
    first_hop_template = """
    Nedbryd følgende juridiske spørgsmål i 2-3 konkrete delspørgsmål:
    {question}
    Format: - delspørgsmål 1\n- delspørgsmål 2
    """
    # ...
```

#### Cache-strategier

1. **LangChain caching**: Implementer caching for at undgå gentagne LLM-kald:

```python
from langchain.cache import InMemoryCache
import langchain

# Aktiver caching
langchain.llm_cache = InMemoryCache()

# For mere permanent caching:
from langchain.cache import SQLiteCache
langchain.llm_cache = SQLiteCache(database_path=".langchain.db")
```

2. **Weaviate caching**: Cache embeddings lokalt:

```python
import hashlib
import pickle
import os

def cached_embedding(text, embeddings_model, cache_dir=".cache"):
    # Opret cache-mappe hvis den ikke findes
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # Generer en unik nøgle baseret på teksten
    hash_key = hashlib.md5(text.encode()).hexdigest()
    cache_path = os.path.join(cache_dir, f"{hash_key}.pkl")
    
    # Tjek om embedding findes i cache
    if os.path.exists(cache_path):
        with open(cache_path, 'rb') as f:
            return pickle.load(f)
    
    # Hvis ikke i cache, generer embedding
    embedding = embeddings_model.embed_query(text)
    
    # Gem i cache
    with open(cache_path, 'wb') as f:
        pickle.dump(embedding, f)
    
    return embedding
```

### Fejlfinding

#### Weaviate-forbindelsesproblemer

| Problem | Mulig årsag | Løsning |
|---------|-------------|--------|
| Kan ikke forbinde til Weaviate | Docker kører ikke | Start Docker og containere med `docker-compose up -d` |
| `ConnectionError` | Forkert URL | Kontroller `WEAVIATE_URL` i `.env` filen |
| Timeout-fejl | Netværksproblemer | Øg timeout-værdien i klienten |

```python
# Øg timeout i Weaviate-klienten
from JAILA.connections import get_weaviate_client

def get_weaviate_client_with_timeout():
    import weaviate
    from weaviate.embedded import EmbeddedOptions
    
    try:
        client = weaviate.Client(
            url=weaviate_url,
            additional_headers={
                "X-OpenAI-Api-Key": openai_api_key
            },
            timeout_config=(5, 60)  # (connect_timeout, read_timeout)
        )
        return client
    except Exception as e:
        print(f"Fejl ved oprettelse af Weaviate-klient: {e}")
        return None
```

#### LLM og embedding-fejl

| Problem | Mulig årsag | Løsning |
|---------|-------------|--------|
| `InvalidRequestError` | For mange tokens | Reducer størrelsen på input eller ændre model |
| `AuthenticationError` | Ugyldig API-nøgle | Kontroller `OPENAI_API_KEY` i `.env` filen |
| `RateLimitError` | For mange API-kald | Implementer backoff-strategi |

```python
# Eksempel på backoff-strategi for OpenAI API
import time
import random
from openai import RateLimitError

def llm_with_backoff(prompt, max_retries=5):
    from JAILA.config import openai_api_key
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(api_key=openai_api_key)
    retries = 0
    
    while retries < max_retries:
        try:
            return llm.invoke(prompt).content
        except RateLimitError:
            retries += 1
            if retries >= max_retries:
                raise
            # Eksponentiel backoff med jitter
            sleep_time = (2 ** retries) + random.random()
            print(f"Rate limit nået. Venter {sleep_time:.2f} sekunder...")
            time.sleep(sleep_time)
```

#### Debugging-værktøjer

1. **Verbose logging**: Aktiver detaljeret logging for at spore fejl:

```python
import logging

# Aktiver logging
logging.basicConfig(level=logging.INFO)
langchain.verbose = True

# For mere detaljeret logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("jaila_debug.log"),
        logging.StreamHandler()
    ]
)
```

2. **Trace-værktøj**: Brug LangChain's trace-funktionalitet:

```python
import os
from langchain.callbacks import tracing_enabled

os.environ["LANGCHAIN_TRACING"] = "true"

# Nu vil alle kald blive sporet og kan ses i LangSmith UI
with tracing_enabled() as session:
    result = multihop_juridisk_søgning("Hvad er reglerne for kørselsfradrag?")
    print(f"Session ID: {session.session_id}")
```

## Teknisk API-dokumentation

JAILA eksponerer en række funktioner og klasser, der kan bruges i dine applikationer. Her er en detaljeret dokumentation af de vigtigste API'er.

### Hovedfunktioner

#### `juridisk_søgning`

```python
def juridisk_søgning(spørgsmål: str, antal_resultater: int = 5, model: str = DEFAULT_MODEL) -> dict
```

**Beskrivelse**: Udfører en direkte juridisk søgning baseret på et enkelt spørgsmål.

**Parametre**:
- `spørgsmål` (str): Det juridiske spørgsmål der skal besvares
- `antal_resultater` (int, optional): Antal dokumenter at hente. Standard er 5.
- `model` (str, optional): Navnet på LLM-modellen at bruge. Standard er defineret i config.py.

**Returværdi**: En dictionary med følgende nøgler:
- `answer` (str): Det genererede svar
- `question` (str): Det oprindelige spørgsmål
- `source_documents` (list): Liste af kildedokumenter

**Eksempel**:
```python
fra JAILA import juridisk_søgning

resultat = juridisk_søgning("Hvad er reglerne for kørselsfradrag?")
print(resultat["answer"])
```

#### `multihop_juridisk_søgning`

```python
def multihop_juridisk_søgning(spørgsmål: str, antal_resultater: int = 5, model: str = DEFAULT_MODEL) -> dict
```

**Beskrivelse**: Udfører en multihop juridisk søgning, hvor komplekse spørgsmål nedbrydes i delspørgsmål.

**Parametre**:
- `spørgsmål` (str): Det komplekse juridiske spørgsmål der skal besvares
- `antal_resultater` (int, optional): Antal dokumenter at hente for hvert delspørgsmål. Standard er 5.
- `model` (str, optional): Navnet på LLM-modellen at bruge. Standard er defineret i config.py.

**Returværdi**: En dictionary med følgende nøgler:
- `answer` (str): Det genererede endelige svar
- `question` (str): Det oprindelige spørgsmål
- `intermediate_results` (list): Liste af svar på delspørgsmål

**Eksempel**:
```python
fra JAILA import multihop_juridisk_søgning

resultat = multihop_juridisk_søgning(
    "Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel, "
    "og hvordan påvirker det beregningen af skatten?"
)
print(resultat["answer"])
```

#### `hybrid_søgning`

```python
def hybrid_søgning(query: str, filters: Optional[Dict] = None, limit: int = 5) -> List[Dict]
```

**Beskrivelse**: Udfører en hybrid søgning med både vektor- og nøgleordsbaseret søgning.

**Parametre**:
- `query` (str): Søgeforespørgslen
- `filters` (Dict, optional): Eventuelle filtre at anvende i format {felt: værdi}
- `limit` (int, optional): Maksimalt antal resultater. Standard er 5.

**Returværdi**: En liste af dokumenter med metadata.

**Eksempel**:
```python
fra JAILA import hybrid_søgning

resultater = hybrid_søgning(
    query="Kørselsfradrag beregning", 
    filters={"law_number": "LBK nr 1284 af 14/11/2018"}, 
    limit=10
)
for doc in resultater:
    print(f"Titel: {doc.get('title')}, Score: {doc.get('score')}")
```

### Utility-funktioner

#### `check_weaviate_connection`

```python
def check_weaviate_connection() -> bool
```

**Beskrivelse**: Kontrollerer om Weaviate-serveren kører og er tilgængelig.

**Returværdi**: `True` hvis forbindelsen er OK, ellers `False`.

#### `get_weaviate_client`

```python
def get_weaviate_client() -> weaviate.Client
```

**Beskrivelse**: Opretter og returnerer en Weaviate-klient.

**Returværdi**: En Weaviate-klientinstans eller `None` ved fejl.

#### `get_vector_store`

```python
def get_vector_store(class_name: str = CLASS_NAME) -> Weaviate
```

**Beskrivelse**: Opretter og returnerer et LangChain Weaviate vektorlager.

**Parametre**:
- `class_name` (str, optional): Navnet på Weaviate-klassen. Standard er værdien af CLASS_NAME fra config.py.

**Returværdi**: Et LangChain Weaviate vektorlagerobjekt eller en DummyVectorStore ved fejl.

### Promptskabeloner

#### `create_multihop_prompt_templates`

```python
def create_multihop_prompt_templates() -> Dict[str, PromptTemplate]
```

**Beskrivelse**: Opretter og returnerer prompt-skabeloner til multihop-forespørgsler.

**Returværdi**: En dictionary med følgende nøgler:
- `first_hop`: Prompt til at nedbryde et spørgsmål i delspørgsmål
- `intermediate_hop`: Prompt til at besvare delspørgsmål baseret på dokumenter
- `final_hop`: Prompt til at generere det endelige svar baseret på delresultater

#### `create_qa_prompt_template`

```python
def create_qa_prompt_template() -> PromptTemplate
```

**Beskrivelse**: Opretter og returnerer en prompt-skabelon til standard juridisk spørgsmål-svar.

**Returværdi**: En PromptTemplate til spørgsmål-svar.

### Udvidelse af API'et

For at tilføje nye funktioner til JAILA API'et, følg disse trin:

1. Tilføj din nye funktion til det relevante modul (f.eks. `retrieval.py` for nye søgefunktioner)
2. Eksporter funktionen i modulets `__init__.py` fil:

```python
# I JAILA/__init__.py
from JAILA.retrieval import din_nye_funktion

__all__ = [
    'juridisk_søgning',
    'multihop_juridisk_søgning',
    'hybrid_søgning',
    'din_nye_funktion',  # Tilføj din nye funktion her
    # ...
]
```

3. Opdater bagudkompatibilitetslaget i `langchain_integration.py`:

```python
# I langchain_integration.py
from JAILA import din_nye_funktion

__all__ = [
    # ...
    'din_nye_funktion',
]
```

## Vedligeholdelse og bidrag

JAILA er et åbent projekt, og bidrag er velkomne. Følg disse trin for at bidrage:

1. Fork projektet
2. Opret en feature branch (`git checkout -b feature/amazing-feature`)
3. Commit dine ændringer (`git commit -m 'Add some amazing feature'`)
4. Push til branchen (`git push origin feature/amazing-feature`)
5. Åbn en Pull Request

## Licens

Distribueret under MIT-licensen. Se `LICENSE` for yderligere information.

## Kontakt

Dit Navn - [din.email@example.com](mailto:din.email@example.com)

Projektlink: [https://github.com/din-organisation/JAILA](https://github.com/din-organisation/JAILA)
