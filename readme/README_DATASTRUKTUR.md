# Weaviate Datastruktur for Juridiske Dokumenter

## Indhold
1. [Overordnet Struktur](#overordnet-struktur)
2. [Klassen LegalDocument](#klassen-legaldocument)
3. [Primære Felter](#primære-felter)
4. [Identifikation og Metadata](#identifikation-og-metadata)
5. [Relationsfelter](#relationsfelter)
6. [Indholds- og Analysefelter](#indholds-og-analysefelter)
7. [Vektoriseringsindstillinger](#vektoriseringsindstillinger)
8. [Importering af Data](#importering-af-data)
9. [Søgning i Datastrukturen](#søgning-i-datastrukturen)

## Overordnet Struktur

Weaviate-databasen anvender en klasse kaldet `LegalDocument`, som er konfigureret til at bruge OpenAI's embeddings-model (`text-embedding-3-large`) til vektorisering af tekstindhold. Denne struktur er designet specifikt til at gemme og søge i juridiske dokumenter, herunder lovtekster, paragraffer og relaterede noter.

## Klassen LegalDocument

Klassen `LegalDocument` er den primære datacontainer med følgende overordnede konfiguration:

```json
{
  "class": "LegalDocument",
  "vectorizer": "text2vec-openai",
  "moduleConfig": {
    "text2vec-openai": {
      "model": "text-embedding-3-large",
      "modelVersion": "latest",
      "type": "text",
      "dimensions": 1024
    },
    "generative-openai": {}
  }
}
```

**Vigtige konfigurationsdetaljer:**
- Anvender `text-embedding-3-large` modellen fra OpenAI
- Bruger 1024 dimensioner (supporterede dimensioner for denne model er: 256, 1024 eller 3072)
- Vektoriseringen er af typen "text"

## Primære Felter

### Tekstfelter

```json
{
  "name": "text",
  "dataType": ["text"],
  "description": "Original tekst",
  "moduleConfig": {
    "text2vec-openai": {
      "skip": true
    }
  }
},
{
  "name": "text_for_embedding",
  "dataType": ["text"],
  "description": "Tekst optimeret til embedding",
  "moduleConfig": {
    "text2vec-openai": {
      "skip": false
    }
  }
}
```

- `text`: Indeholder den originale, uredigerede tekst. Dette felt bruges IKKE til at generere embeddings.
- `text_for_embedding`: Specialformateret tekst der er optimeret til at generere embeddings. Dette er det primære felt for vektorisering.

## Identifikation og Metadata

### Primære Identifikationsfelter

```json
{
  "name": "chunk_id",
  "dataType": ["text"],
  "description": "Unik ID for chunk",
  "indexInverted": true
},
{
  "name": "document_id",
  "dataType": ["text"],
  "description": "ID for oprindelsesdokumentet",
  "indexInverted": true
}
```

- `chunk_id`: Unik identifikator for hvert tekstchunk
- `document_id`: Identifikator for det originale dokument, som chunken kommer fra (flere chunks kan dele samme document_id)

### Metadata om Dokumenttypen

```json
{
  "name": "chunk_type",
  "dataType": ["text"],
  "description": "Type af chunk (paragraph/note)",
  "indexInverted": true
},
{
  "name": "title",
  "dataType": ["text"],
  "description": "Dokumentets titel",
  "indexInverted": true
},
{
  "name": "status",
  "dataType": ["text"],
  "description": "Lovens status (gældende, historisk)",
  "indexInverted": true
},
{
  "name": "law_number",
  "dataType": ["text"],
  "description": "Lovens nummer og år",
  "indexInverted": true
}
```

- `chunk_type`: Angiver om chunken er en paragraf eller en note
- `title`: Lovens eller dokumentets titel
- `status`: Indikerer om loven er gældende, historisk, osv.
- `law_number`: Lovens nummer og år (f.eks. "2023-01-13 nr. 42")

## Relationsfelter

```json
{
  "name": "note_references_raw",
  "dataType": ["text"],
  "description": "JSON-strengrepræsentation af notereferencer",
  "indexInverted": true
},
{
  "name": "note_reference_ids",
  "dataType": ["text[]"],
  "description": "Liste af note-IDs for søgning",
  "indexInverted": true
},
{
  "name": "related_note_chunks",
  "dataType": ["text[]"],
  "description": "IDs for relaterede note-chunks",
  "indexInverted": true
},
{
  "name": "related_paragraph_chunk_id",
  "dataType": ["text"],
  "description": "ID for relateret paragraf-chunk",
  "indexInverted": true
}
```

- `note_references_raw`: JSON-streng der indeholder rå notehenvisninger
- `note_reference_ids`: Liste af IDs for relaterede noter, god til filtrering
- `related_note_chunks`: Indeholder IDs for note-chunks der er relateret til dette dokument (typisk for paragraffer)
- `related_paragraph_chunk_id`: ID for den paragraf som en note relaterer til (typisk for noter)

## Indholds- og Analysefelter

```json
{
  "name": "topic",
  "dataType": ["text"],
  "description": "Emne for teksten",
  "indexInverted": true
},
{
  "name": "summary",
  "dataType": ["text"],
  "description": "Opsummering af indholdet",
  "indexInverted": true
},
{
  "name": "keywords",
  "dataType": ["text[]"],
  "description": "Nøgleord",
  "indexInverted": true
},
{
  "name": "entities",
  "dataType": ["text[]"],
  "description": "Navngivne entiteter",
  "indexInverted": true
},
{
  "name": "dom_references",
  "dataType": ["text[]"],
  "description": "Referencer til domme",
  "indexInverted": true
}
```

- `topic`: Overordnet emne for teksten
- `summary`: Kortfattet opsummering af indholdet
- `keywords`: Liste af nøgleord relateret til indholdet
- `entities`: Navngivne entiteter såsom personer, organisationer, steder, mv.
- `dom_references`: Referencer til relevante domme

### Regelanalysefelter

```json
{
  "name": "rule_type",
  "dataType": ["text"],
  "description": "Type af regel",
  "indexInverted": true
},
{
  "name": "rule_type_confidence",
  "dataType": ["number"],
  "description": "Konfidensscore for regeltypen",
  "indexInverted": false
},
{
  "name": "rule_type_explanation",
  "dataType": ["text"],
  "description": "Forklaring af regeltypen",
  "indexInverted": true
},
{
  "name": "interpretation_flag",
  "dataType": ["boolean"],
  "description": "Flag for fortolkning",
  "indexInverted": false
}
```

- `rule_type`: Klassificering af regeltype (f.eks. "definition", "forpligtelse", "sanktion")
- `rule_type_confidence`: Numerisk score for tillid til klassificeringen
- `rule_type_explanation`: Tekstforklaring af hvorfor reglen er klassificeret som den er
- `interpretation_flag`: Boolean der indikerer om reglen kræver særlig fortolkning

### Meta-felter

```json
{
  "name": "llm_model_used",
  "dataType": ["text"],
  "description": "LLM-model brugt til at generere metadata",
  "indexInverted": true
}
```

- `llm_model_used`: Angiver hvilken sprogmodel der blev anvendt til at generere de analytiske metadata

## Vektoriseringsindstillinger

Weaviate bruger OpenAI's embeddings til at vektorisere tekst, med følgende konfiguration:

- **Model**: `text-embedding-3-large`
- **Dimensioner**: 1024 (kan alternativt være 256 eller 3072)
- **Type**: text

Bemærk at selve embeddings kun genereres for `text_for_embedding`-feltet, ikke for det originale `text`-felt. Dette er konfigureret med `"skip": true` på `text`-feltet og `"skip": false` på `text_for_embedding`-feltet.

## Importering af Data

Data importeres primært via JSONL-filer med følgende proces:

1. Hver linje i JSONL-filen repræsenterer ét objekt (enten en paragraf eller en note)
2. Obligatoriske felter inkluderer:
   - `chunk_id`
   - `document_id`
   - `chunk_type`
   - `text`
3. Under import optimeres teksten til embeddings og gemmes i `text_for_embedding`-feltet
4. Relationer mellem paragraffer og noter etableres via reference-felterne

### Eksempel på JSONL-data:

```json
{"chunk_id": "para_1", "document_id": "lov123", "chunk_type": "paragraph", "text": "§1. Dette er en paragraf.", "related_note_chunks": ["note_1", "note_2"]}
{"chunk_id": "note_1", "document_id": "lov123", "chunk_type": "note", "text": "Dette er en note til §1.", "related_paragraph_chunk_id": "para_1"}
```

## Søgning i Datastrukturen

Du kan udnytte datastrukturen til forskellige typer søgninger:

### Semantisk Søgning
Brug vector-søgning via OpenAI's embeddings til at finde konceptuelt lignende dokumenter:

```python
client.query.get("LegalDocument", [fields]).with_near_text({"concepts": ["skattefradrag"]})
```

### Nøgleordssøgning
Søg efter specifikke nøgleord i teksten:

```python
client.query.get("LegalDocument", [fields]).with_where({
    "path": ["text"],
    "operator": "ContainsAny",
    "valueText": "skat"
})
```

### Relationssøgning
Find relaterede noter til en paragraf:

```python
# Find dokument først
result = client.query.get("LegalDocument", ["chunk_id", "related_note_chunks"]).with_where({
    "path": ["chunk_id"],
    "operator": "Equal",
    "valueText": "para_1"
}).do()

# Derefter hent relaterede noter
note_ids = result["data"]["Get"]["LegalDocument"][0]["related_note_chunks"]
```

### Metadata-filtrering
Filtrer efter dokumenttype, status, osv.:

```python
client.query.get("LegalDocument", [fields]).with_where({
    "path": ["chunk_type"],
    "operator": "Equal",
    "valueText": "paragraph"
})
```

---

Denne datastruktur er designet til at give både kraftfuld semantisk søgning via embeddings og præcis filtreringsfunktionalitet baseret på metadata. Strukturen understøtter også komplekse relationer mellem juridiske dokumenttyper som paragraffer og deres tilhørende noter.
