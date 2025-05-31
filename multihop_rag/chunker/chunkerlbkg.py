import os
import re
import json
import uuid
import time
import openai
import concurrent.futures
from tqdm import tqdm
from pathlib import Path
from docx import Document
import argparse
import json
import os
import re
import uuid
from datetime import datetime
from typing import Tuple, List, Dict

# Import af batch-processing funktionalitet
try:
    from batch_processing import enrich_chunks_batch_with_llm
    BATCH_PROCESSING_AVAILABLE = True
except ImportError:
    BATCH_PROCESSING_AVAILABLE = False

INPUT_DIR = "input"
OUTPUT_DIR = "output"
MAX_WORKERS = 50  # Maksimalt antal parallelle processer

# Initialiser OpenAI API med nøgle fra miljøvariabel
openai.api_key = os.environ.get("OPENAI_API_KEY")

# ----------- DOMS-TAGGING ------------
def tag_domsreferencer(text):
    """Tilføjer <dom> tags omkring domreferencer i teksten."""
    # Udvidede mønstre til at fange flere formater
    patterns = [
        r'\bSKM\.? ?(?:\d{4}[\.-])? ?\d+(?:[ \.]?\d+)? ?[A-ZÆØÅ]+\b',  # SKM 2023 7 HR, SKM.2023.7.HR, SKM 2003 405 HR
        r'\bTfS\.? ?(?:\d{4}[\.-])? ?\d+(?:[ \.]?[A-ZÆØÅ]+)?(?:[ \.]?\d+)?(?:[ \.]?[A-ZÆØÅ]+)?',  # TfS 1998 354 H, TfS.1998.354.H, TfS 1995 137 LSR
        r'\bU\.? ?(?:\d{4}[\.-])? ?\d+(?:[\.\/]\d+)?(?:[ \.]?[A-ZÆØÅ]+)?(?:[ \.]?\d+)?',  # U 2004.234, U.2004/234H
        r'\bLSR\.? ?(?:\d{4}[\.-])? ?\d+(?:[ \.]?[A-ZÆØÅ]+)?(?:[ \.]?\d+)?(?:[ \.]?[A-ZÆØÅ]+)?',  # LSR 2022 42, LSR.2022.42.SR
        r'\b(?:Vestre|Østre|Højesterets)\.? ?[Ll]andsrets? ?[Dd]om af \d{1,2}\.? ?[a-zæøå]+ \d{4}\b',  # Vestre Landsrets Dom af 12. juni 2018
        r'\b(?:Højesterets|HR)\.? ?[Dd]om af \d{1,2}\.? ?[a-zæøå]+ \d{4}\b'  # Højesterets Dom af 4. marts 2022
    ]
    combined_pattern = re.compile('|'.join(patterns), re.IGNORECASE)

    def replacer(match):
        raw = match.group(0)
        dom_id = re.sub(r'\s+', '', raw).replace("/", ".").replace(" ", "")
        return f'<dom id="{dom_id}">{raw}</dom>'

    return combined_pattern.sub(replacer, text)

def extract_dom_references(text):
    """Udtrækker domsreferencer fra teksten og returnerer en liste af unikke referencer."""
    references = []
    dom_pattern = re.compile(r'<dom\s+id="([^"]+)">([^<]+)</dom>')
    
    for match in dom_pattern.finditer(text):
        dom_id = match.group(1)
        dom_text = match.group(2)
        references.append({"id": dom_id, "text": dom_text})
    
    return references

def remove_note_references(text: str, chunk_id: str) -> Tuple[str, List[Dict]]:
    """
    Fjerner notehenvisninger i parentes fra teksten og returnerer:
    - En ren tekst til embeddings (uden parentes-noter)
    - Liste over note-referencer med deres position og genereret note_id
    
    Dette giver optimal kvalitet for embeddings, mens den oprindelige tekst med 
    parentes-noter bevares separat.
    """
    note_refs = []
    clean_text_parts = []  # Til embeddings (uden noter)
    last_index = 0

    # Søg efter notemønstret (X) hvor X er et tal
    for match in re.finditer(r'\((\d+)\)', text):
        start, end = match.span()
        note_number = match.group(1)
        note_id = f"note_{chunk_id}_{note_number}"

        # Tilføj tekst før henvisningen
        text_before = text[last_index:start]
        clean_text_parts.append(text_before)
        
        # Clean-versionen får ikke notehenvisningen overhovedet

        # Registrér note-reference med kontekst
        context_start = max(0, start - 30)  # Op til 30 tegn før noten
        context_end = min(len(text), end + 30)  # Op til 30 tegn efter noten
        
        note_refs.append({
            "note_number": note_number,
            "note_id": note_id,
            "char_offset": len(''.join(clean_text_parts)),  # Position i den rene tekst
            "context": text[context_start:context_end].strip()
        })

        last_index = end

    # Tilføj evt. resttekst
    text_after = text[last_index:]
    clean_text_parts.append(text_after)
    
    clean_text = ''.join(clean_text_parts)  # Til embeddings

    return clean_text, note_refs


def create_embedding_text(chunk: dict) -> str:
    """
    Skaber en optimeret tekst til embeddings, der:
    1. Fjerner notehenvisninger
    2. Beriger med kontekst (paragraf, titel, dato)
    3. Renser for formatstøj
    
    Args:
        chunk: Dictionary med chunk-data
        
    Returns:
        Optimeret tekst til embeddings
    """
    # Hent den rene tekst uden notehenvisninger
    text = chunk.get("text", "")
    clean_text = re.sub(r'\(\d+\)', '', text)  # Fjern (1), (2), osv.
    
    # Fjern overflødige mellemrum og uens tegnsætning
    clean_text = re.sub(r'\s+', ' ', clean_text)  # Erstat flere mellemrum med ét
    clean_text = clean_text.strip()  # Fjern whitespace i start og slut
    
    # Byg kontekst præfiks
    context_parts = []
    
    # Tilføj lovens titel hvis tilgængelig
    if "title" in chunk and chunk["title"]:
        context_parts.append(chunk["title"])
    
    # Tilføj paragraf, stykke og nummer hvis tilgængelige
    para_parts = []
    if "paragraph" in chunk and chunk["paragraph"]:
        para_parts.append(chunk["paragraph"])
    
    # Håndter stk værdi, så den altid vises korrekt
    if "stk" in chunk and chunk["stk"]:
        stk_value = chunk["stk"]
        if isinstance(stk_value, list) and stk_value:
            # Brug første element fra listen
            para_parts.append(f"stk. {stk_value[0]}")
        else:
            # Brug værdien direkte
            para_parts.append(f"stk. {stk_value}")
    
    # Håndter nr værdi, så den altid vises korrekt
    if "nr" in chunk and chunk["nr"]:
        nr_value = chunk["nr"]
        if isinstance(nr_value, list) and nr_value:
            # Brug første element fra listen
            para_parts.append(f"nr. {nr_value[0]}")
        else:
            # Brug værdien direkte
            para_parts.append(f"nr. {nr_value}")
    
    if para_parts:
        context_parts.append(", ".join(para_parts))
    
    # Tilføj dato hvis tilgængelig
    if "date" in chunk and chunk["date"]:
        context_parts.append(f"({chunk['date']})")
    
    # Byg den endelige embedding tekst
    context = ""
    if context_parts:
        context = ", ".join(context_parts) + ": "
    
    return context + clean_text


def clean_text_for_display(text: str) -> str:
    """
    Fjerner notehenvisninger i parentes-format fra teksten, så den er klar til visning.
    """
    # Fjern alle (X) parentes-noter fra teksten
    return re.sub(r'\(\d+\)', '', text)

def parse_notes(paragraphs):
    notes = {}
    note_re = re.compile(r'^\((\d+)\)\s*(.+)')
    for p in paragraphs:
        m = note_re.match(p)
        if m:
            notes[m.group(1)] = m.group(2).strip()
    return notes

def clean_paragraph(paragraph):
    return re.sub(r'\s+', ' ', paragraph).strip()

def clean_text_from_metadata_prefixes(text):
    """
    Fjerner metadata-præfikser fra teksten, så kun den rene lovtekst bevares.
    Metadata-præfikser er typisk i formatet 'PARAGRAF: § 1 | STYKKE: stk. 1 | NUMMER: nr. 1 | ...'.
    """
    if not text:
        return ""
    
    # Find evt. indeks af den første paragraph (§), som markerer starten på den egentlige lovtekst
    paragraph_match = re.search(r'\n\n\s*\u00a7\s*\d+', text)
    
    if paragraph_match:
        # Returner alt fra og med paragraftegnet
        return text[paragraph_match.start():].strip()
    
    # Alternativ metode: fjern alle linjer med metadata-præfikser
    lines = text.split('\n')
    cleaned_lines = []
    metadata_pattern = re.compile(r'^(PARAGRAF:|STYKKE:|NUMMER:|AFSNIT:|LOVTITEL:|STATUS:|REFERENCE:)', re.IGNORECASE)
    
    # Gem kun linjer, der ikke matcher metadata-mønstret
    for line in lines:
        if not metadata_pattern.search(line):
            cleaned_lines.append(line)
    
    return '\n'.join(cleaned_lines).strip()

def extract_chunks(paragraphs, notes, law_title, law_number, law_date, section):
    chunks = []
    current_paragraph = None
    current_stk = None
    current_chunk = None
    
    note_ref_re = re.compile(r'\((\d+)\)')
    section_re = re.compile(r'^AFSNIT [IVXLCDM]+\. .+')
    ophævet_re = re.compile(r'^\(Ophævet\)$', re.IGNORECASE)
    paragraph_re = re.compile(r'^§\s*(\d+)\s*([A-ZÆØÅa-zæøå]+)?\.?')
    stk_re = re.compile(r'^Stk\. ?(\d+)')
    nr_re = re.compile(r'(\d+)[)\.]\s')
    
    MAX_NUMRE_PR_CHUNK = 1

    for idx, p in enumerate(paragraphs):
        txt = clean_paragraph(p)
        if not txt:
            continue
        
        if section_re.match(txt):
            section = txt
            continue
        
        para_match = paragraph_re.match(txt)
        if para_match:
            if current_chunk:
                if not current_chunk["stk"]:
                    current_chunk["stk"] = ["1"]
                chunks.append(current_chunk)
            
            paragrafnummer = para_match.group(1)
            paragrafbogstav = para_match.group(2) if para_match.group(2) else ""
            if paragrafbogstav:
                current_paragraph = f"§ {paragrafnummer} {paragrafbogstav}"
            else:
                current_paragraph = f"§ {paragrafnummer}"
            current_stk = "1"  
            
            current_chunk = {
                "chunk_id": str(uuid.uuid4()),
                "section": section,
                "paragraph": current_paragraph,
                "stk": [current_stk],
                "nr": [],
                "status": "gældende",
                "law_number": law_number,
                "title": law_title,
                "date": law_date,
                "text": txt,
                "notes": {},
            }
            
            if ophævet_re.search(txt):
                current_chunk["status"] = "ophævet"
            
            refs = note_ref_re.findall(txt)
            for ref in refs:
                if ref in notes:
                    current_chunk["notes"][ref] = notes[ref]
            continue
        
        if not current_chunk:
            continue
        
        stk_match = stk_re.search(txt)
        if stk_match and current_paragraph:
            stk_num = stk_match.group(1)
            
            if stk_num != current_stk:
                current_stk = stk_num
                
                chunks.append(current_chunk)
                
                current_chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "section": section,
                    "paragraph": current_paragraph,
                    "stk": [stk_num],
                    "nr": [],
                    "status": "gældende",
                    "law_number": law_number,
                    "title": law_title,
                    "date": law_date,
                    "text": txt,
                    "notes": {},
                }
                
                refs = note_ref_re.findall(txt)
                for ref in refs:
                    if ref in notes:
                        current_chunk["notes"][ref] = notes[ref]
                continue
        
        nr_match = None
        
        # Tjek for numre i begyndelsen af linjen
        if txt.strip() and txt.strip()[0].isdigit():
            nr_match = nr_re.match(txt)
            
        # Tjek for numre senere i teksten, men kun efter et komma efterfulgt af nummer
        if not nr_match and current_paragraph and ", " in txt:
            parts = txt.split(", ")
            for i, part in enumerate(parts):
                if i > 0 and part and part[0].isdigit() and nr_re.match(part):
                    nr_match = nr_re.match(part)
                    # Opdater txt til kun at indeholde den del, der starter med nummeret
                    txt = ", ".join(parts[i:])
                    break
                    
        if nr_match and current_paragraph:
            nr_num = nr_match.group(1)
            
            # Hvis vi har for mange numre i den aktuelle chunk, opdel i en ny
            if len(current_chunk["nr"]) >= MAX_NUMRE_PR_CHUNK and nr_num not in current_chunk["nr"]:
                # Gem den nuværende chunk
                chunks.append(current_chunk)
                
                # Opret en ny chunk for de næste numre, men med samme stk.
                current_chunk = {
                    "chunk_id": str(uuid.uuid4()),
                    "section": section,
                    "paragraph": current_paragraph,
                    "stk": [current_stk],
                    "nr": [nr_num],  # Start med det nye nummer
                    "status": "gældende",
                    "law_number": law_number,
                    "title": law_title,
                    "date": law_date,
                    "text": txt,
                    "notes": {},
                }
                
                refs = note_ref_re.findall(txt)
                for ref in refs:
                    if ref in notes:
                        current_chunk["notes"][ref] = notes[ref]
                continue
            
            # Ellers tilføj nummeret til den eksisterende chunk
            if nr_num not in current_chunk["nr"]:
                current_chunk["nr"].append(nr_num)
            
            refs = note_ref_re.findall(txt)
            for ref in refs:
                if ref in notes:
                    current_chunk["notes"][ref] = notes[ref]
                    
            if txt not in current_chunk["text"]:
                current_chunk["text"] += " " + txt
            continue
        
        if current_chunk:
            current_chunk["text"] += " " + txt
            
            refs = note_ref_re.findall(txt)
            for ref in refs:
                if ref in notes:
                    current_chunk["notes"][ref] = notes[ref]
                
    if current_chunk:
        if not current_chunk["stk"]:
            current_chunk["stk"] = ["1"]
        chunks.append(current_chunk)
    
    for chunk in chunks:
        if chunk["nr"]:
            chunk["nr"] = sorted(chunk["nr"], key=int)
            
    for chunk in chunks:
        heading = chunk["paragraph"]
        if chunk["stk"]:
            heading += f", stk. {','.join(chunk['stk'])}"
        if chunk["nr"]:
            heading += f", nr. {','.join(chunk['nr'])}"
        chunk["heading"] = heading
    
    return chunks

def build_standard_metadata(text=None):
    """Genererer standardmetadata uden brug af LLM."""
    return {
        "rule_type": "hovedregel",
        "keywords": ["automatisk", "genereret", "uden", "llm"],
        "summary": "",
        "entities": []
    }

def build_embedding_text(chunk):
    """Bygger tekst til embedding baseret på chunk indhold."""
    # Håndter tilfælde hvor chunk er en streng
    if isinstance(chunk, str):
        return chunk
        
    # Håndter tilfælde hvor stk er en streng i stedet for liste
    if "stk" in chunk:
        if isinstance(chunk["stk"], list):
            try:
                sorted_stk = sorted(chunk["stk"], key=int) if chunk["stk"] else []
            except (ValueError, TypeError):
                # Hvis vi ikke kan sortere numerisk, brug alfabetisk sortering som fallback
                sorted_stk = sorted(chunk["stk"]) if chunk["stk"] else []
        elif isinstance(chunk["stk"], str):
            sorted_stk = [chunk["stk"]]
        else:
            sorted_stk = []
    else:
        sorted_stk = []
    
    # Håndter tilfælde hvor nr er en streng i stedet for liste
    if "nr" in chunk:
        if isinstance(chunk["nr"], list):
            try:
                sorted_nr = sorted(chunk["nr"], key=int) if chunk["nr"] else []
            except (ValueError, TypeError):
                sorted_nr = sorted(chunk["nr"]) if chunk["nr"] else []
        elif isinstance(chunk["nr"], str):
            sorted_nr = [chunk["nr"]]
        else:
            sorted_nr = []
    else:
        sorted_nr = []
    
    # Begynd at opbygge markørlinjen
    markers = f"PARAGRAF: {chunk.get('paragraph', 'ukendt')}"
    
    if sorted_stk:
        markers += f" | STYKKE: stk. {','.join(map(str, sorted_stk))}"
    
    if sorted_nr:
        markers += f" | NUMMER: nr. {','.join(map(str, sorted_nr))}"
    
    markers += f" | AFSNIT: {chunk.get('section', '')}"
    markers += f" | LOVTITEL: {chunk.get('title', 'ukendt')}"
    markers += f" | STATUS: {chunk.get('status', 'ukendt')}"
    markers += f" | REFERENCE: {chunk.get('law_number', 'ukendt')}"
    
    # Tilføj keywords fra metadata hvis de findes
    keywords_text = ""
    entities_text = ""
    summary_text = ""
    
    # Udtræk og formatér keywords fra metadata
    if "metadata" in chunk and isinstance(chunk["metadata"], dict):
        # Håndtér keywords
        if "keywords" in chunk["metadata"]:
            keywords = chunk["metadata"]["keywords"]
            if isinstance(keywords, list) and keywords:
                keywords_text = f" | KEYWORDS: {', '.join(keywords)}"
        
        # Håndtér entities (inklusive dom-referencer)
        if "entities" in chunk["metadata"] and chunk["metadata"]["entities"]:
            entities = chunk["metadata"]["entities"]
            if isinstance(entities, list) and entities:
                # Udtræk navnene på entities (simple strenge eller 'text' fra dictionary)
                entity_names = []
                for entity in entities:
                    if isinstance(entity, str):
                        entity_names.append(entity)
                    elif isinstance(entity, dict) and "text" in entity:
                        entity_names.append(entity["text"])
                if entity_names:
                    entities_text = f" | ENTITIES: {', '.join(entity_names)}"
        
        # Tilføj summary til embedding text for bedre søgning
        if "summary" in chunk["metadata"] and chunk["metadata"]["summary"]:
            summary = chunk["metadata"]["summary"]
            if isinstance(summary, str) and summary.strip():
                summary_text = f" | SUMMARY: {summary.strip()}"
    
    # Sikre at vi har en tekst
    text = chunk.get('text', '')
    if isinstance(text, str):
        base = f"{markers}{keywords_text}{entities_text}{summary_text}\n\n{text.strip()}"
    else:
        base = f"{markers}{keywords_text}{entities_text}{summary_text}\n\n(Tekst mangler)"
    
    # Håndter note-referencer
    notes_text = ""
    
    # Tjek først hvilken type chunk det er
    chunk_type = chunk.get("type", "")
    
    # For paragraf-chunks, vis kun note-referencer, ikke indhold
    if chunk_type == "paragraf":
        # Tjek for note_references feltet og vis kun ID'er
        if "note_references" in chunk and chunk["note_references"]:
            if isinstance(chunk["note_references"], list):
                notes_text += f"\nNoter: {', '.join(map(str, chunk['note_references']))}"
            else:
                notes_text += f"\nNoter: {chunk['note_references']}"
        
        # Ignorér det gamle notes felt for paragraf-chunks
    
    # For note-chunks, indholdet er allerede inkluderet i teksten
    elif chunk_type == "note":
        pass
    
    # For andre typer af chunks (bagudkompatibilitet)
    else:
        # Tjek først for det nye note_references felt
        if "note_references" in chunk and chunk["note_references"]:
            if isinstance(chunk["note_references"], list):
                notes_text += f"\nNoter: {', '.join(map(str, chunk['note_references']))}"
            else:
                notes_text += f"\nNoter: {chunk['note_references']}"
        # For bagudkompatibilitet, vis også noter for ikke-paragraf chunks
        elif "notes" in chunk and chunk["notes"]:
            # Håndter stk som enten streng eller liste
            para_parts = []
            if "stk" in chunk and chunk["stk"]:
                stk_value = chunk["stk"]
                if isinstance(stk_value, list):
                    # Hvis det er en liste, brug kun første værdi
                    if stk_value and len(stk_value) > 0:
                        para_parts.append(f"stk. {stk_value[0]}")
                else:
                    # Hvis det er en streng, brug den direkte
                    para_parts.append(f"stk. {stk_value}")
            
            # Håndter nr som enten streng eller liste
            if "nr" in chunk and chunk["nr"]:
                nr_value = chunk["nr"]
                if isinstance(nr_value, list):
                    # Hvis det er en liste, brug kun første værdi
                    if nr_value and len(nr_value) > 0:
                        para_parts.append(f"nr. {nr_value[0]}")
                else:
                    # Hvis det er en streng, brug den direkte
                    para_parts.append(f"nr. {nr_value}")
            
            # Hvis notes er et dictionary
            if isinstance(chunk["notes"], dict):
                for k, v in chunk["notes"].items():
                    if isinstance(v, str):
                        notes_text += f"\nNote ({k}): {v}"
                    else:
                        notes_text += f"\nNote ({k}): (Note-indhold mangler)"
            # Hvis notes er en liste
            elif isinstance(chunk["notes"], list):
                for i, note in enumerate(chunk["notes"]):
                    if isinstance(note, str):
                        notes_text += f"\nNote ({i}): {note}"
                    elif isinstance(note, dict) and 'text' in note:
                        notes_text += f"\nNote ({i}): {note['text']}"
            # Hvis notes er en anden iterabel type
            elif hasattr(chunk["notes"], '__iter__'):
                for i, note in enumerate(chunk["notes"]):
                    if isinstance(note, str):
                        notes_text += f"\nNote ({i}): {note}"
                    elif isinstance(note, dict) and 'text' in note:
                        notes_text += f"\nNote ({i}): {note['text']}"
            # Hvis notes er en streng
            elif isinstance(chunk["notes"], str):
                notes_text += f"\nNoter: {chunk['notes']}"
            
    return base + notes_text

def build_metadata(chunk, position=None, source_filename="", domain="skat"):
    """Bygger et dedikeret metadata-felt med metadata for chunken i overensstemmelse med Weaviate skemaet."""
    # Håndter tilfælde hvor chunk ikke er et dictionary men en streng
    if isinstance(chunk, str):
        # Returner et minimal metadata objekt for strenge
        return {
            "chunk_id": str(uuid.uuid4()),
            "text": chunk,
            "status": "ukendt",
            "type": "tekst",
            "topic": "generelt",
            "rule_type": "hovedregel",
            "interpretation_flag": False,
            "keywords": ["automatisk", "genereret"],
            "entities": [],
            "dom_references": [],
            "related_note_chunks": [],
            "related_paragraph_chunk_id": None,
            "summary": ""
        }
    
    # Håndter forskellige typer af chunks
    chunk_type = chunk.get("type", "paragraf")
    
    # Håndter stk og nr som strenge
    if "stk" in chunk:
        if isinstance(chunk["stk"], list):
            stk_string = ','.join(chunk["stk"]) if chunk["stk"] else ""
        elif isinstance(chunk["stk"], str):
            stk_string = chunk["stk"]
        else:
            stk_string = ""
    else:
        stk_string = ""
        
    if "nr" in chunk:
        if isinstance(chunk["nr"], list):
            nr_string = ','.join(chunk["nr"]) if chunk["nr"] else ""
        elif isinstance(chunk["nr"], str):
            nr_string = chunk["nr"]
        else:
            nr_string = ""
    else:
        nr_string = ""
    
    # Etabler heading
    heading = chunk.get("heading", "")
    if not heading:
        if chunk_type == "notes":
            heading = f"Noter til {chunk.get('related_paragraph', '')}"
        elif chunk.get("section") and chunk.get("section").strip():
            # Brug første del af sektionen som heading
            heading = chunk.get("section").split('.')[0] if '.' in chunk.get("section", "") else chunk.get("section", "")
        else:
            heading = "Generelt"
    
    # Bestem topic
    topic = ""
    if chunk_type == "notes":
        topic = f"noter til {chunk.get('related_paragraph', '')}".lower()
    elif chunk.get("section") and chunk.get("section").strip():
        topic = chunk.get("section").lower()
    elif heading and heading.strip():
        topic = heading.lower()
    else:
        topic = "generelt"
    
    # Forbered keywords som liste
    keywords = []
    if chunk.get("keywords"):
        if isinstance(chunk["keywords"], str):
            # Split på komma hvis det er en streng
            keywords = [k.strip() for k in chunk["keywords"].split(',') if k.strip()]
        elif isinstance(chunk["keywords"], list):
            keywords = chunk["keywords"]
    
    # Udtrække domsreferencer
    dom_references = []
    for ref in extract_dom_references(chunk.get("text", "")):
        dom_references.append(ref["text"])
    
    # Forbered entities som liste
    entities = []
    
    # Tilføj relevante entiteter baseret på chunk data
    if chunk.get("paragraph"):
        if "stk" in chunk and chunk["stk"]:
            stk_text = chunk["stk"] if isinstance(chunk["stk"], str) else ",".join(chunk["stk"])
            if "nr" in chunk and chunk["nr"]:
                nr_text = chunk["nr"] if isinstance(chunk["nr"], str) else ",".join(chunk["nr"])
                entities.append(f"{chunk['paragraph']}, stk. {stk_text}, nr. {nr_text}")
            else:
                entities.append(f"{chunk['paragraph']}, stk. {stk_text}")
        else:
            entities.append(chunk["paragraph"])
    
    # Tilføj lovtitel som entitet
    if chunk.get("title"):
        entities.append(chunk["title"])
    
    # Byg heading baseret på paragraf, stk og nr for at matche eksemplet
    heading = ""
    if chunk.get("paragraph"):
        heading = chunk["paragraph"]
        if "stk" in chunk and chunk["stk"]:
            stk_text = chunk["stk"] if isinstance(chunk["stk"], str) else ",".join(chunk["stk"])
            heading += f", stk. {stk_text}"
            if "nr" in chunk and chunk["nr"]:
                nr_text = chunk["nr"] if isinstance(chunk["nr"], str) else ",".join(chunk["nr"])
                heading += f", nr. {nr_text}"
    elif chunk.get("section") and chunk.get("section").strip():
        heading = chunk["section"]
    else:
        heading = "Generelt"
    
    # Vi bruger ikke længere formateret tekst med metadata præfiks, da det skaber støj og duplikation
    # Brug den rene, oprindelige lovtekst uden formatering
    original_text = clean_text_from_metadata_prefixes(chunk.get("text", ""))
    
    # Bygger metadata i overensstemmelse med Weaviate skemaet
    metadata = {
        "chunk_id": chunk.get("chunk_id", ""),
        "text": original_text,
        "law_number": chunk.get("law_number", ""),
        "title": chunk.get("title", ""),
        "date": chunk.get("date", ""),
        "paragraph": chunk.get("paragraph", "") if chunk_type != "notes" else "",
        "stk": stk_string,
        "nr": nr_string,
        "section": chunk.get("section", ""),
        "status": chunk.get("status", "ukendt"),
        "type": chunk_type,
        "heading": heading,
        "topic": topic.lower() if topic else "",
        "rule_type": "hovedregel",
        "interpretation_flag": False,
        "summary": "",  # Tom som standard, kan opdateres med LLM
        "keywords": keywords,
        "entities": entities,
        "dom_references": dom_references,
        "related_paragraph_chunk_id": chunk.get("related_paragraph_chunk_id", None)
    }
    
    # Tilføj relaterede chunks
    if chunk.get("related_paragraph_chunk_id"):
        metadata["related_paragraph_chunk_id"] = chunk.get("related_paragraph_chunk_id")
    
    # Tilføj note chunks
    if chunk.get("related_note_chunks"):
        metadata["related_note_chunks"] = chunk.get("related_note_chunks")

    return metadata

def enrich_chunk_with_llm(chunk):
    """Beriger en enkelt chunks metadata med LLM-analyse."""
    import openai  # sørg for at din API-nøgle er sat som miljøvariabel
    from openai import OpenAI
    import json
    
    # Tjek om vi har et gyldigt chunk
    if not chunk:
        return chunk
    
    # Opret en OpenAI klient
    client = OpenAI()
    
    # Metadata håndteres ikke længere som et indlejret objekt, så vi behøver ikke at oprette det
    # Hvis der stadig er et metadata-felt, fjern det
    if "metadata" in chunk:
        del chunk["metadata"]
    
    try:
        # Først: Lav en separat prompt for at klassificere rule_type præcist
        rule_type_system_prompt = """Du er juridisk assistent og skal klassificere danske lovbestemmelser.

Du skal vælge den mest passende rule_type blandt følgende kategorier:

"hovedregel": En bestemmelse der fastsætter den almindelige retstilstand eller hovednorm.

"undtagelse": En bestemmelse der begrænser, afviger fra eller indskrænker en hovedregel.

"fortolkning": En bestemmelse der forklarer, definerer eller præciserer, hvordan en regel skal forstås.

"henvisning": En bestemmelse der alene videresender betydningen til en anden bestemmelse, uden selvstændigt retsindhold.

Returnér et JSON-objekt med:

rule_type: én af de fire ovenstående værdier

confidence: et tal mellem 0 og 100 der angiver hvor sikker du er

explanation: kort juridisk begrundelse for valget"""
        
        # Derefter gør det klart i promten at vi forventer JSON for de resterende metadata
        metadata_system_prompt = """Du er en ekspert i jura og skal analysere en lovtekst. Giv din analyse som et JSON-objekt der følger denne skabelon:
{
  "interpretation_flag": true|false,
  "summary": "Kort sammenfatning af bestemmelsen",
  "keywords": ["nøgleord1", "nøgleord2", ...],
  "entities": [{"type": "lovhenvisning", "text": "§ 10"}, {"type": "personnavn", "text": "ægtefælle"}]
}

Hvor:
- interpretation_flag: Sæt til true hvis reglen kræver juridisk fortolkning. Vær MEGET OPMÆRKSOM på at fange regler, der indeholder skøn, vage begreber, betingelser, eller komplekse juridiske vurderinger. Eksempler på formuleringer der typisk kræver fortolkning: "rimelig", "nødvendig", "væsentlig", "efter omstændighederne", "særlige forhold", "kan", "bør", "inden for rimelig tid", "passende", osv. Sæt også til true hvis teksten henviser til andre bestemmelser, der skal fortolkes sammen med reglen.
- summary: En kort præcis sammenfatning af hvad reglen betyder
- keywords: Liste af 3-5 relevante nøgleord eller -fraser, der beskriver emnerne i reglen
- entities: Angiv MAKSIMALT 7 specifikke juridiske enheder, aktører eller institutioner der omtales. Vælg kun de mest relevante for regelens forståelse. Hver entitet skal have en 'type' (fx 'lovhenvisning', 'myndighed', 'juridisk_person') og en 'text' (den præcise tekst).

Svar UDELUKKENDE med JSON, ingen indledende tekst."""
        
        # Konstruer den rette prompt baseret på chunk-typen
        user_prompt = ""
        chunk_type = chunk.get("type", "paragraf")
        
        if chunk_type in ["paragraf", "tekst"]:
            # For paragraf eller tekst chunks
            if "paragraph" in chunk and chunk["paragraph"]:
                paragraph_text = f"PARAGRAF: {chunk['paragraph']}"
                if "stk" in chunk and chunk["stk"]:
                    stk_text = ', '.join(map(str, chunk["stk"])) if isinstance(chunk["stk"], list) else chunk["stk"]
                    paragraph_text += f", stk. {stk_text}"
                if "nr" in chunk and chunk["nr"]:
                    nr_text = ', '.join(map(str, chunk["nr"])) if isinstance(chunk["nr"], list) else chunk["nr"]
                    paragraph_text += f", nr. {nr_text}"
                
                user_prompt += f"{paragraph_text}\n\n"
            
            # Tilføj lovtitel hvis tilgængelig
            if "title" in chunk and chunk["title"]:
                user_prompt += f"LOVTITEL: {chunk['title']}\n"
            
            # Tilføj teksten
            if "text" in chunk and chunk["text"]:
                user_prompt += f"\nTEKST:\n{chunk['text']}"
        
        elif chunk_type in ["note", "notes"]:
            # For note chunks
            user_prompt += "NOTETYPE: Lovnoter\n\n"
            
            # Tilføj teksten
            if "text" in chunk and chunk["text"]:
                user_prompt += f"TEKST:\n{chunk['text']}"
        
        else:
            # For andre typer chunks
            user_prompt += f"TYPE: {chunk_type}\n\n"
            
            # Tilføj teksten
            if "text" in chunk and chunk["text"]:
                user_prompt += f"TEKST:\n{chunk['text']}"
        
        # Konstruer prompt til at bestemme rule_type først
        response_rule_type = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": rule_type_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,  # Endnu lavere temperatur for mere konsistente rule_type værdier
        )
        
        # Hent rule_type klassificering
        rule_type_text = response_rule_type.choices[0].message.content.strip()
        
        # Parse JSON-svar for rule_type
        rule_type_data = {}
        try:
            rule_type_data = json.loads(rule_type_text)
        except json.JSONDecodeError:
            # Hvis svaret ikke er gyldig JSON, forsøg at rense det
            match = re.search(r'{.*}', rule_type_text, re.DOTALL)
            if match:
                try:
                    rule_type_data = json.loads(match.group(0))
                except Exception as e:
                    print(f"Kunne ikke parse rule_type JSON efter rensning: {e}")
                    rule_type_data = {}
            else:
                print(f"Kunne ikke finde rule_type JSON i svaret: {rule_type_text}")
                rule_type_data = {}
        
        # Udtræk rule_type, confidence og explanation
        rule_type = rule_type_data.get("rule_type", "hovedregel")
        confidence = rule_type_data.get("confidence", 0)
        explanation = rule_type_data.get("explanation", "")
        
        # Log hvis rule_type ikke er en af de forventede værdier
        expected_rule_types = ["hovedregel", "undtagelse", "fortolkning", "henvisning"]
        if rule_type not in expected_rule_types:
            print(f"Advarsel: Uventet rule_type værdi: {rule_type}. Bruger 'hovedregel' som standard.")
            rule_type = "hovedregel"
        
        # Kald GPT-4-mini for de resterende metadata
        response = client.chat.completions.create(
            model="gpt-4.1-mini-2025-04-14",
            messages=[
                {"role": "system", "content": metadata_system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Lavere temperatur for mere konsistente svar
        )
        
        # Hent svaret med metadata
        response_text = response.choices[0].message.content.strip()
        
        # Parse JSON-svar for metadata
        try:
            json_data = json.loads(response_text)
        except json.JSONDecodeError:
            # Hvis svaret ikke er gyldig JSON, forsøg at rense det
            match = re.search(r'{.*}', response_text, re.DOTALL)
            if match:
                try:
                    json_data = json.loads(match.group(0))
                except Exception as e:
                    print(f"Kunne ikke parse metadata JSON efter rensning: {e}")
                    json_data = {}
            else:
                print(f"Kunne ikke finde metadata JSON i svaret: {response_text}")
                json_data = {}
        
        # Opdater chunk metadata med LLM-resultater
        
        # Import entity_types modulet for avanceret entity-type genkendelse
        try:
            from entity_types import find_entity_type
            entity_type_finder_available = True
        except ImportError:
            entity_type_finder_available = False
            print("Advarsel: entity_types modul ikke tilgængeligt. Bruger simpel entity-type genkendelse.")
            
        # Supplement til LLM's vurdering af interpretation_flag
        # Tjek for ord og fraser der ofte indikerer fortolkningsbehov
        interpretation_indicators = [
            "rimelig", "nødvendig", "væsentlig", "efter omstændighederne", 
            "særlige forhold", "kan", "bør", "inden for rimelig tid", "passende",
            "skøn", "vurdering", "hensyntagen", "almindelige", "efter aftale",
            "forudsat", "med mindre", "i det omfang", "medmindre", "såfremt",
            "hvis", "efter forespørgsel", "efter anmodning", "ved forevisning",
            "hensigtmæssig", "til dels", "så vidt muligt", "når det er påkrævet",
            "efter samtykke", "på betingelse af", "under hensyn til", "af betydning"
        ]
        
        # Tjek om teksten indeholder indikationer på fortolkningsbehov
        text_to_check = ""
        if "text" in chunk and isinstance(chunk["text"], str):
            text_to_check = chunk["text"].lower()
        
        needs_interpretation = False
        if any(indicator in text_to_check for indicator in interpretation_indicators):
            needs_interpretation = True
        
        # Håndter entities som simple strenge for at matche Weaviate's forventede format
        entities = json_data.get("entities", [])
        
        # Begræns antallet af entities til maksimalt 7 (samme som i prompten)
        MAX_ENTITIES = 7
        if len(entities) > MAX_ENTITIES:
            print(f"Begrænser antal entities fra {len(entities)} til {MAX_ENTITIES}")
            entities = entities[:MAX_ENTITIES]
        
        # Konverter alle entities til simple strenge
        string_entities = []
        for entity in entities:
            if isinstance(entity, str):
                # Allerede en streng, tilføj direkte
                string_entities.append(entity)
            elif isinstance(entity, dict) and "text" in entity:
                # Udpak kun teksten fra objektet
                string_entities.append(entity["text"])
        
        # Fjern eventuelle duplikater og behold rækkefølgen
        seen = set()
        unique_entities = []
        for entity in string_entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)
        
        # Kombiner LLM's vurdering med den regelbaserede tilgang for interpretation_flag
        llm_interpretation = json_data.get("interpretation_flag", False)
        # Hvis enten LLM eller vores regelbaserede tilgang markerer fortolkningsbehov, sæt flaget til true
        final_interpretation_flag = llm_interpretation or needs_interpretation
        
        if not llm_interpretation and needs_interpretation:
            print(f"Fortolkningsbehov opdaget i tekst, men ikke af LLM: Chunk {chunk.get('chunk_id', '')}")
        
        # Log den juridiske begrundelse for rule_type klassificeringen hvis confidence er høj
        if confidence >= 70:
            print(f"Høj confidence ({confidence}) for rule_type '{rule_type}': {explanation}")
        
        # Opdater chunk direkte på topniveau i stedet for at bruge et nestet metadata-objekt
        chunk.update({
            # Brug rule_type fra den dedikerede klassificering
            "rule_type": rule_type,
            "rule_type_confidence": confidence,
            "rule_type_explanation": explanation,
            # Brug de resterende metadata fra den anden prompt
            "interpretation_flag": final_interpretation_flag,
            "summary": json_data.get("summary", ""),
            "keywords": json_data.get("keywords", []),
            "entities": unique_entities,
            "llm_model_used": "gpt-4.1-mini-2025-04-14"
        })
        
        # Vi bruger ikke længere embedding_text, da 'text' feltet indeholder den rene lovtekst
        # Fjernet: chunk["embedding_text"] = build_embedding_text(chunk)
            
    except Exception as e:
        print(f"LLM-fejl i chunk {chunk.get('chunk_id')}: {e}")
    
    return chunk


def process_chunk(chunk, position=None, source_filename="", domain="skat"):
    """Bearbejder en enkelt chunk og tilfører standardmetadata uden LLM."""
    # Tjek om chunken allerede har LLM-genereret metadata (direkte på topniveau nu)
    has_llm_metadata = False
    if "llm_model_used" in chunk:
        has_llm_metadata = True
        # Gem de eksisterende LLM-værdier (de er nu på topniveau)
        existing_rule_type = chunk.get("rule_type")
        existing_keywords = chunk.get("keywords", [])
        existing_summary = chunk.get("summary", "")
        existing_entities = chunk.get("entities", [])
        existing_interpretation_flag = chunk.get("interpretation_flag", False)
    
    # Byg metadata-objektet
    metadata = build_metadata(chunk, position=position, source_filename=source_filename, domain=domain)
    
    # Hvis der allerede er LLM-metadata, bevar disse værdier
    if has_llm_metadata:
        metadata["rule_type"] = existing_rule_type
        metadata["keywords"] = existing_keywords
        metadata["summary"] = existing_summary
        metadata["entities"] = existing_entities
        metadata["llm_model_used"] = chunk.get("llm_model_used", "")
    else:
        # Tilføj standardmetadata
        standard_meta = build_standard_metadata()
        metadata["rule_type"] = standard_meta["rule_type"]
        metadata["keywords"] = standard_meta["keywords"]
        metadata["summary"] = standard_meta["summary"]
        metadata["entities"] = standard_meta["entities"]
    
    # Opdater chunk direkte med metadata (flad struktur uden indlejret metadata-felt)
    chunk.update(metadata)
    
    # Fjern eventuelt embedding_text felt hvis det findes
    if "embedding_text" in chunk:
        del chunk["embedding_text"]
        
    # Fjern eventuelt metadata-felt hvis det stadig findes
    if "metadata" in chunk:
        del chunk["metadata"]
    
    return chunk

def process_chunk_with_notes(chunk):
    """
    Behandler en chunk og dens noter for domsreferencer.
    Returnerer altid en liste af chunks, hvor den første er hovedchunken
    og de efterfølgende er note-chunks (hvis der er nogen).
    """
    # Opret en liste til resultater
    result_chunks = []
    
    # Håndter tom chunk
    if not chunk:
        return result_chunks
    
    # Kopier chunken, så vi ikke ændrer den originale
    chunk_copy = chunk.copy() if isinstance(chunk, dict) else {"text": str(chunk), "type": "tekst", "chunk_id": str(uuid.uuid4())}
    
    # Sikre at chunk_copy har et chunk_id
    if "chunk_id" not in chunk_copy:
        chunk_copy["chunk_id"] = str(uuid.uuid4())
    
    # Tag domsreferencer i hovedteksten
    if "text" in chunk_copy and isinstance(chunk_copy["text"], str):
        chunk_copy["text"] = tag_domsreferencer(chunk_copy["text"])
        
        # Tilføj type, hvis den ikke findes
        if "type" not in chunk_copy:
            chunk_copy["type"] = "paragraf"
        
        # Udtræk domsreferencer fra hovedteksten
        dom_refs = extract_dom_references(chunk_copy["text"])
        
        # Gem dom_references som liste af tekster
        if dom_refs:
            chunk_copy["dom_references"] = [ref["text"] for ref in dom_refs]
        
        # Behandl notehenvisninger i teksten
        if "chunk_id" in chunk_copy:
            # Gem den oprindelige tekst med parentes-noter
            original_text = chunk_copy["text"]
            
            # Fjern notehenvisninger fra teksten
            clean_text, note_refs = remove_note_references(original_text, chunk_copy["chunk_id"])
            
            # Brug ren tekst uden noter som primær tekst
            chunk_copy["text"] = clean_text
            
            # Generer optimeret tekst til embeddings med kontekst
            chunk_copy["text_for_embedding"] = create_embedding_text(chunk_copy)
            
            # Gem note-referencer hvis der er nogen
            if note_refs:
                chunk_copy["note_references"] = note_refs
    
    # Behandl noter hvis der er nogen
    note_chunks = []
    if "notes" in chunk_copy and chunk_copy["notes"]:
        if isinstance(chunk_copy["notes"], dict):
            for note_number, note_text in chunk_copy["notes"].items():
                if isinstance(note_text, str):
                    # Tag domsreferencer i noten
                    tagged_note_text = tag_domsreferencer(note_text)
                    
                    # Udtræk referencer fra note
                    note_refs = extract_dom_references(tagged_note_text)
                    dom_references = [ref["text"] for ref in note_refs] if note_refs else []
                    
                    # Udtræk paragraf-reference fra hovedchunken
                    paragraph_ref = ""
                    if "paragraph" in chunk_copy:
                        paragraph_ref = chunk_copy["paragraph"]
                    elif "header" in chunk_copy:
                        paragraph_ref = chunk_copy["header"]
                    
                    # Opret en separat chunk for denne note
                    note_chunk_id = str(uuid.uuid4())
                    note_chunk = {
                        "chunk_id": note_chunk_id,
                        "type": "notes",
                        "note_number": note_number,  # Gem notenummeret eksplicit
                        "text": tagged_note_text,  # Ren tekst bruges også til embeddings
                        "related_paragraph_chunk_id": chunk_copy["chunk_id"],
                        "related_paragraph_text": chunk_copy["text"][:100] + "...",  # Preview af paragrafteksten
                        "related_paragraph_ref": paragraph_ref,  # Paragraf-reference som noten hører til
                        "dom_references": dom_references
                    }
                    
                    # Kopier relevante felter fra hovedchunken
                    for field in ["paragraph", "section", "title", "law_number", "status", "date"]:
                        if field in chunk_copy:
                            note_chunk[field] = chunk_copy[field]
                    
                    # Kopier stk og nr fra hovedchunken
                    if "stk" in chunk_copy:
                        if isinstance(chunk_copy["stk"], list):
                            note_chunk["stk"] = ",".join(chunk_copy["stk"]) if chunk_copy["stk"] else ""
                        elif isinstance(chunk_copy["stk"], str):
                            note_chunk["stk"] = chunk_copy["stk"]
                    else:
                        note_chunk["stk"] = ""
                        
                    if "nr" in chunk_copy:
                        if isinstance(chunk_copy["nr"], list):
                            note_chunk["nr"] = ",".join(chunk_copy["nr"]) if chunk_copy["nr"] else ""
                        elif isinstance(chunk_copy["nr"], str):
                            note_chunk["nr"] = chunk_copy["nr"]
                    else:
                        note_chunk["nr"] = ""
                    
                    # Tilføj note_chunk til note_chunks liste
                    note_chunks.append(note_chunk)
        
        # Hvis der er note-chunks, tilføj dem til resultatet
        if note_chunks:
            # Opdater hovedchunkens related_note_chunks med ID'er på note-chunks
            chunk_copy["related_note_chunks"] = [nc["chunk_id"] for nc in note_chunks]
        
        # Fjern notes-feltet fra hovedchunken (kun beholder referencer)
        if "notes" in chunk_copy:
            del chunk_copy["notes"]
    
    # Forbedrer note-referencer hvis der er både note-referencer og note-chunks
    if "note_references" in chunk_copy and note_chunks:
        # Opdater note-referencer med chunk_id for note-chunks
        for ref in chunk_copy["note_references"]:
            note_number = ref.get("note_number")
            if note_number:
                # Find den tilsvarende note-chunk
                for note_chunk in note_chunks:
                    if note_chunk.get("note_number") == note_number:
                        # Tilføj direkte reference til note-chunken
                        ref["note_chunk_id"] = note_chunk["chunk_id"]
                        break
    
    # Tilføj hovedchunken først til resultatet
    result_chunks.append(chunk_copy)
    
    # Tilføj note-chunks til resultatet
    if note_chunks:
        result_chunks.extend(note_chunks)
    
    return result_chunks

def process_chunks_parallel(chunks, source_filename="", domain="skat"):
    """Bearbejder chunks parallelt ved hjælp af en thread pool."""
    processed_chunks = []
    
    # Opret en thread pool med højere antal arbejdere (da vi ikke bruger LLM)
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        # Forbered alle opgaver
        future_to_chunk = {
            executor.submit(
                process_chunk, 
                chunk, 
                position=i,
                source_filename=source_filename,
                domain=domain
            ): (i, chunk) for i, chunk in enumerate(chunks)
        }
        
        # Brug tqdm til at vise fremskridt
        for future in tqdm(
            concurrent.futures.as_completed(future_to_chunk), 
            total=len(chunks),
            desc="Bearbejder chunks uden LLM"
        ):
            try:
                processed_chunk = future.result()
                processed_chunks.append(processed_chunk)
            except Exception as e:
                idx, chunk = future_to_chunk[future]
                print(f"Fejl i chunk {idx} ({chunk.get('paragraph', 'ukendt')}): {e}")
                # Tilføj chunk med standardmetadata
                chunk["embedding_text"] = build_embedding_text(chunk)
                chunk["metadata"] = build_metadata(
                    chunk, 
                    position=idx,
                    source_filename=source_filename,
                    domain=domain
                )
                processed_chunks.append(chunk)
    
    # Sorter chunks efter deres oprindelige position (nu på topniveau)
    # Hvis position ikke findes, brug 0 som standard
    processed_chunks.sort(key=lambda x: x.get("position", 0))
    
    return processed_chunks

def process_file(file_path, use_llm=False, use_batch=False, batch_size=10, max_workers=5):
    """
    Behandler en fil og genererer chunks i JSONL-format.
    
    Args:
        file_path: Sti til filen der skal behandles
        use_llm: Om LLM skal bruges til at generere metadata (langsommere, men mere præcist)
    """
    print(f"Behandler fil: {file_path}")
    try:
        # Beregn output filnavn og forbered stier
        filename = Path(file_path).stem
        output_file = Path(OUTPUT_DIR) / f"{filename}_chunks.jsonl"
        
        # Læs filen
        if str(file_path).endswith('.docx'):
            # Brug eksisterende kode til at læse og behandle DOCX-filer
            doc = Document(file_path)
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            print(f"Læste {len(paragraphs)} afsnit fra filen")
            
            # Udtræk lovtitel og andre metadata fra filnavnet
            file_stem = Path(file_path).stem
            # Antager et filnavnsformat som 'Lovtitel (dato nr. xxx)'
            title_match = re.match(r'^(.+?)\s*\((.+?)\s+nr\.\s+(.+?)\)$', file_stem)
            
            if title_match:
                law_title = title_match.group(1).strip()  # Lovens titel
                law_date = title_match.group(2).strip()    # Dato
                law_number = f"LBK nr. {title_match.group(3).strip()} af {law_date}"  # Lovnummer med dato
            else:
                # Brug filnavnet som lovtitel hvis det ikke matcher formatet
                law_title = file_stem
                law_number = "Ukendt lovnummer"
                law_date = "Ukendt dato"
            section = ""
            
            # Find startpunktet for noter
            note_start = None
            for i, p in enumerate(paragraphs):
                if re.match(r'^\(\d+\)\s', p):
                    note_start = i
                    break
                    
            if note_start is not None:
                main_text = paragraphs[:note_start]
                note_paras = paragraphs[note_start:]
                print(f"Fandt noter fra linje {note_start}")
            else:
                main_text = paragraphs
                note_paras = []
                print("Ingen noter fundet i dokumentet")
                
            # Parse noter
            notes = parse_notes(note_paras)
            print(f"Parsede {len(notes)} noter")
            
            # Ekstraher chunks fra teksten
            chunks = extract_chunks(main_text, notes, law_title, law_number, law_date, section)
            print(f"Ekstraherede {len(chunks)} chunks")
        else:
            print(f"Ikke-understøttet filformat: {file_path}")
            return False
        
        # Første trin: Behandl chunks og opret separate note-chunks (UDEN LLM)
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            try:
                print(f"Bearbejder chunk {i+1}/{len(chunks)}: {chunk.get('paragraph', 'ukendt')}")
                
                # Behandl hver chunk og få en liste af chunks (hovedchunk + note-chunks)
                chunk_result = process_chunk_with_notes(chunk)
                
                # Konverter chunk_result til en liste, hvis det ikke allerede er en liste
                if not isinstance(chunk_result, list):
                    # Hvis det er et dictionary eller et andet objekt, pak det ind i en liste
                    chunk_result = [chunk_result]
                
                # Håndter strenge i chunk_result før vi begynder iterationen
                for j in range(len(chunk_result)):
                    if isinstance(chunk_result[j], str):
                        # For strenge, opret et nyt chunk dictionary med teksten
                        string_id = f"string_{i}_{j}_{str(uuid.uuid4())[:8]}"
                        dict_chunk = {
                            "chunk_id": string_id,
                            "type": "tekst",
                            "text": chunk_result[j],
                            "related_chunk_id": chunk["chunk_id"] if isinstance(chunk, dict) and "chunk_id" in chunk else None
                        }
                        
                        # Erstat strengen med den nye dictionary
                        chunk_result[j] = dict_chunk
                
                # Tilføj embedding tekst og metadata til hver chunk i resultatet
                for j, c in enumerate(chunk_result):
                    try:
                        # Tilføj metadata direkte på topniveau (uden nestet metadata-objekt)
                        source_filename = filename
                        # Brug original position for hovedchunken, modificeret for noter
                        position = i if j == 0 else i * 1000 + j
                        metadata = build_metadata(c, position=position, source_filename=source_filename, domain="skat")
                        # Fusær metadata direkte ind i chunk-objektet i stedet for at tilføje det som et nestet objekt
                        c.update(metadata)
                        
                        # Samle chunks til LLM-berigelse i batches
                        if use_llm and j == 0 and isinstance(c, dict) and "text" in c and c.get("type") == "paragraf":
                            # Vi samler alle hovedchunks til batch-berigelse senere
                            pass  # 'pass' bruges når der ikke er anden kode at udføre i denne blok
                        
                        # FJERNET: Vi bruger ikke længere embedding_text. Teksten renses i stedet direkte
                        # Rens text-feltet for metadata-præfikser, så det kun indeholder den rene lovtekst
                        if "text" in c:
                            c["text"] = clean_text_from_metadata_prefixes(c["text"])
                        else:
                            # Håndter tilfælde uden text-felt
                            c["text"] = ""
                    except Exception as e:
                        print(f"Fejl ved tilføjelse af data til chunk {j} i chunk_result {i}: {e}")
                        # Tilføj minimum data for at undgå fejl senere
                        if isinstance(c, dict):
                            # Tilføj direkte på topniveau (ingen nestet metadata)
                            c.update({
                                "chunk_id": str(uuid.uuid4()),
                                "text": c.get("text", ""),
                                "status": "ukendt",
                                "type": c.get("type", "tekst"),
                                "domain": "skat"
                            })
                
                processed_chunks.extend(chunk_result)
            except Exception as e:
                print(f"Fejl under bearbejdning af chunk {i}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"Bearbejdede {len(processed_chunks)} chunks (inklusiv note-chunks)")
        
        # Mellem trin: Etabler relationer mellem noter og mellem parallelle paragraffer
        # Dette gøres efter alle chunks er oprettet, men før LLM-berigelse
        
        # 1. Opret maps til at finde chunks baseret på paragraf, type osv.
        paragraph_to_chunks = {}
        note_chunks_by_paragraph = {}
        chunk_id_to_chunk = {}
        paragraph_chunks = []  # Liste til at gemme paragraf-chunks
        
        for i, chunk in enumerate(processed_chunks):
            if not isinstance(chunk, dict):
                continue
                
            # Gem chunk baseret på dens ID for hurtig opslag
            if "chunk_id" in chunk:
                chunk_id_to_chunk[chunk["chunk_id"]] = chunk
            
            # Registrer paragraf-chunks
            if chunk.get("type") == "paragraf" and "paragraph" in chunk:
                paragraph = chunk["paragraph"]
                if paragraph not in paragraph_to_chunks:
                    paragraph_to_chunks[paragraph] = []
                paragraph_to_chunks[paragraph].append(chunk)
                paragraph_chunks.append(chunk)  # Tilføj til paragraf-chunks listen
            
            # Registrer note-chunks
            if chunk.get("type") in ["note", "notes"] and "paragraph" in chunk:
                paragraph = chunk["paragraph"]
                if paragraph not in note_chunks_by_paragraph:
                    note_chunks_by_paragraph[paragraph] = []
                note_chunks_by_paragraph[paragraph].append(chunk)
        
        # 2. Etabler relationer mellem parallelle paragraffer (fx § 4 og § 4 A)
        print("Etablerer relationer mellem parallelle paragraffer...")
        parallel_relations_count = 0
        
        # Regex til at identificere basis-paragraffer og bogstav-paragraffer
        base_para_re = re.compile(r'^\u00a7\s*(\d+)$')  # Matcher fx '§ 4'
        letter_para_re = re.compile(r'^\u00a7\s*(\d+)\s*([A-ZÆØÅ][a-zæøå]*)$')  # Matcher fx '§ 4 A'
        
        for paragraph, chunks in paragraph_to_chunks.items():
            # Tjek om dette er en paragraf med bogstav
            letter_match = letter_para_re.match(paragraph)
            if letter_match:
                number = letter_match.group(1)  # fx '4' fra '§ 4 A'
                base_paragraph = f"§ {number}"  # fx '§ 4'
                
                # Find basis-paragraffen
                if base_paragraph in paragraph_to_chunks:
                    for letter_chunk in chunks:
                        # Tilføj reference til basis-paragraffen
                        if "related_paragraphs" not in letter_chunk:
                            letter_chunk["related_paragraphs"] = []
                            
                        # Tilføj alle basis-paragraf chunks som relaterede
                        for base_chunk in paragraph_to_chunks[base_paragraph]:
                            if base_chunk["chunk_id"] not in letter_chunk["related_paragraphs"]:
                                letter_chunk["related_paragraphs"].append(base_chunk["chunk_id"])
                                parallel_relations_count += 1
                                
                            # Gør relationen gensidig
                            if "related_paragraphs" not in base_chunk:
                                base_chunk["related_paragraphs"] = []
                            if letter_chunk["chunk_id"] not in base_chunk["related_paragraphs"]:
                                base_chunk["related_paragraphs"].append(letter_chunk["chunk_id"])
        
        # 3. Etabler relationer mellem noter til samme paragraf
        print("Etablerer relationer mellem noter til samme paragraf...")
        note_relations_count = 0
        
        for paragraph, note_chunks in note_chunks_by_paragraph.items():
            # Hvis der er mere end én note til samme paragraf
            if len(note_chunks) > 1:
                # Opret relationer mellem alle noter til samme paragraf
                for i, note1 in enumerate(note_chunks):
                    # Vi bruger ikke længere kryds-relationer mellem noter, da dette skaber for mange relationer
                    # og er ikke nødvendigt med vores nye note_references struktur
                    pass
        
        print(f"Etableret {parallel_relations_count} relationer mellem parallelle paragraffer")
        print(f"Etableret {note_relations_count} relationer mellem noter")
        
        # 4. Etabler komplette relationer mellem paragraffer og deres noter
        print("Sikrer komplette relationer mellem paragraffer og noter...")
        paragraph_note_relations_count = 0
        missing_relation_count = 0
        
        # Tjek for manglende related_paragraph_chunk_id i noter
        for paragraph, notes in note_chunks_by_paragraph.items():
            # Find paragraf-chunks for denne paragraf
            if paragraph in paragraph_to_chunks:
                paragraph_chunks_for_this_para = paragraph_to_chunks[paragraph]
                
                # For hver note, sikr at den har korrekt related_paragraph_chunk_id
                for note in notes:
                    # Sikr at noten har related_paragraph_chunk_id
                    if "related_paragraph_chunk_id" not in note or not note["related_paragraph_chunk_id"]:
                        # Find den første paragraf-chunk og brug dens ID
                        if paragraph_chunks_for_this_para:
                            note["related_paragraph_chunk_id"] = paragraph_chunks_for_this_para[0]["chunk_id"]
                            missing_relation_count += 1
                    
                    # Vi bruger ikke længere related_note_chunks, da vi nu har note_references
                    # med direkte relationer mellem paragraffer og noter
                    pass
        
        # Sikr at alle note-chunks har en related_paragraph_chunk_id - ellers find den bedste match
        for chunk in processed_chunks:
            if isinstance(chunk, dict) and chunk.get("type") in ["note", "notes"]:
                if "related_paragraph_chunk_id" not in chunk or not chunk["related_paragraph_chunk_id"]:
                    # Forsøg at finde en paragraf-chunk baseret på paragraf-feltet
                    if "paragraph" in chunk and chunk["paragraph"] in paragraph_to_chunks:
                        # Brug den første paragraf-chunks ID
                        para_chunks = paragraph_to_chunks[chunk["paragraph"]]
                        if para_chunks:
                            chunk["related_paragraph_chunk_id"] = para_chunks[0]["chunk_id"]
                            
                            # Opdater metadata objektet med related_paragraph_chunk_id
                            if "metadata" in chunk and chunk["metadata"]:
                                chunk["metadata"]["related_paragraph_chunk_id"] = para_chunks[0]["chunk_id"]
                            
                            missing_relation_count += 1
                            
                            # Vi bruger ikke længere related_note_chunks, da vi nu har note_references
                            # med direkte relationer via note_chunk_id
        
        print(f"Etableret {paragraph_note_relations_count} relationer mellem paragraffer og noter")
        print(f"Repareret {missing_relation_count} manglende related_paragraph_chunk_id relationer")
        
        # Andet trin: LLM-berigelse for hver enkelt chunk hvis brug af LLM er aktiveret
        if use_llm:
            # Samle alle chunks (både paragraffer og noter) til berigelse
            chunks_to_enrich = []
            chunk_indices = []
            
            # Først identificer alle chunks der skal beriges
            for i, chunk in enumerate(processed_chunks):
                if isinstance(chunk, dict):
                    if chunk.get("type") in ["paragraf", "note", "notes"]:
                        chunks_to_enrich.append((chunk, i))
            
            # Opret et map fra chunk_id til chunk index for hurtig opslag
            chunk_id_to_index = {}
            for i, chunk in enumerate(processed_chunks):
                if isinstance(chunk, dict) and "chunk_id" in chunk:
                    chunk_id_to_index[chunk["chunk_id"]] = i
            
            # Berig chunks med LLM - enten som batch eller enkeltvis
            if chunks_to_enrich:
                # Udtræk chunks og deres indekser
                chunk_objects = [c for c, _ in chunks_to_enrich]
                chunk_indices = [idx for _, idx in chunks_to_enrich]
                
                # Hvis batch-processing er aktiveret og tilgængelig
                if use_batch and BATCH_PROCESSING_AVAILABLE:
                    print(f"Beriger {len(chunk_objects)} chunks med LLM i batches (batch-størrelse: {batch_size}, parallelle tråde: {max_workers})...")
                    
                    # Brug batch-processing
                    enriched_chunks = enrich_chunks_batch_with_llm(chunk_objects, batch_size=batch_size, max_workers=max_workers)
                    
                    # Erstat de oprindelige chunks med de berigede
                    for idx, enriched_chunk in zip(chunk_indices, enriched_chunks):
                        processed_chunks[idx] = enriched_chunk
                else:
                    # Hvis batch-processing ikke er aktiveret eller ikke er tilgængelig
                    if use_batch and not BATCH_PROCESSING_AVAILABLE:
                        print("ADVARSEL: Batch-processing er anmodet, men batch_processing.py modulet kunne ikke importeres.")
                        print("Falder tilbage til enkelt-chunk berigelse.")
                        
                    print(f"Beriger {len(chunk_objects)} chunks med LLM enkeltvis...")
                    total_chunks = len(chunk_objects)
                    
                    for i, (chunk, idx) in enumerate(chunks_to_enrich):
                        if i % 10 == 0 or i == total_chunks - 1:
                            print(f"  Behandler chunk {i+1}/{total_chunks}...")
                        
                        # Berig chunken med LLM
                        enriched_chunk = enrich_chunk_with_llm(chunk)
                        
                        # Erstat den oprindelige chunk med den berigede
                        processed_chunks[idx] = enriched_chunk
            
            # Etabler relationer mellem chunks baseret på deres ID'er
            print("Etablerer relationer mellem chunks...")
            
            # Opret map fra paragraf til chunk_id for hurtigere opslag
            paragraph_to_chunk_id = {}
            for idx, chunk in enumerate(processed_chunks):
                if isinstance(chunk, dict) and chunk.get("type") == "paragraf" and "paragraph" in chunk:
                    paragraph_key = chunk["paragraph"]
                    paragraph_to_chunk_id[paragraph_key] = chunk["chunk_id"]
            
            # Først kører vi gennem alle note-chunks og opdaterer deres related_paragraph_chunk_id
            for note_chunk in processed_chunks:
                if isinstance(note_chunk, dict) and note_chunk.get("type") in ["note", "notes"]:
                    # Få paragraf-referencen fra note-chunken
                    related_para = note_chunk.get("related_paragraph")
                    if related_para and related_para in paragraph_to_chunk_id:
                        # Opdater note-chunken med reference til paragraf-chunken
                        note_chunk["related_paragraph_chunk_id"] = paragraph_to_chunk_id[related_para]
            
            # Derefter kører vi gennem paragraf-chunks og opdaterer deres related_chunk_id med note-referencer
            for chunk in processed_chunks:
                if isinstance(chunk, dict) and chunk.get("type") == "paragraf":
                    # Håndtér note-referencer
                    if "note_references" in chunk and chunk["note_references"]:
                        # Find note-chunks baseret på referencer
                        related_notes = []
                        for note_ref in chunk["note_references"]:
                            # Søg efter note-chunks baseret på reference og paragraf
                            for note_chunk in processed_chunks:
                                if isinstance(note_chunk, dict) and note_chunk.get("type") in ["note", "notes"]:
                                    # Tjek om noten er relateret til denne paragraf og har det rigtige note-nummer
                                    if note_chunk.get("related_paragraph") == chunk.get("paragraph") and \
                                       (f"({note_ref})" in note_chunk.get("text", "") or \
                                        note_chunk.get("note_number") == note_ref):
                                        related_notes.append(note_chunk["chunk_id"])
                                        # Opdater også note-chunken med related_paragraph_chunk_id hvis ikke allerede sat
                                        if "related_paragraph_chunk_id" not in note_chunk:
                                            note_chunk["related_paragraph_chunk_id"] = chunk["chunk_id"]
                        
                        # Opdater chunk med related_chunk_id
                        if related_notes:
                            chunk["related_chunk_id"] = related_notes
                    
                    # Inkluder dom-referencer i entities
                    if "dom_references" in chunk and chunk["dom_references"]:
                        # Hvis der ikke allerede er entities felt, opret en tom liste
                        if "entities" not in chunk:
                            chunk["entities"] = []
                        
                        # Tilføj dom-referencer til entities
                        for dom_ref in chunk["dom_references"]:
                            if isinstance(dom_ref, dict) and "id" in dom_ref and "text" in dom_ref:
                                # Tilføj domsreferencen som en simpel streng til entities
                                dom_entity_text = dom_ref["text"]
                                
                                # Tilføj til entities hvis den ikke allerede findes
                                if dom_entity_text not in chunk["entities"]:
                                    chunk["entities"].append(dom_entity_text)
                
            print("LLM-metadata tilføjet, springer standardmetadata over.")
            final_chunks = processed_chunks
        else:
            # Hvis ikke brug af LLM, så tilføj standardmetadata med parallelle arbejdere
            print("Tilføjer standardmetadata til chunks...")
            final_chunks = process_chunks_parallel(processed_chunks, source_filename=filename, domain="skat")
        
        # Fjern alle embedding_text felter og sikr at teksten er ren
        for chunk in final_chunks:
            # Fjern embedding_text feltet hvis det findes
            if "embedding_text" in chunk:
                del chunk["embedding_text"]
            
            # Sikr at text-feltet er renset for metadata-præfikser
            if "text" in chunk:
                chunk["text"] = clean_text_from_metadata_prefixes(chunk["text"])
        
        # Gem resultatet
        with open(output_file, 'w', encoding='utf-8') as f:
            for chunk in final_chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + '\n')
        
        print(f"Gemt {len(final_chunks)} chunks til {output_file}")
        return True
        
    except Exception as e:
        print(f"Fejl under bearbejdning af {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    # Opret output-mappe, hvis den ikke eksisterer
    Path(OUTPUT_DIR).mkdir(exist_ok=True)
    
    # Definer kommandolinje argumenter
    parser = argparse.ArgumentParser(description="Bearbejd lovbekendtgørelser til chunks")
    parser.add_argument("input_dir", nargs="?", default=INPUT_DIR, help="Sti til mappen med input filer")
    parser.add_argument("--pattern", "-p", default="*.docx", help="Mønster for filer der skal behandles (default: *.docx)")
    parser.add_argument("--use-llm", "-l", action="store_true", help="Brug LLM til metadata-udtrækning (langsommere, men mere præcist)")
    parser.add_argument("--batch", "-b", action="store_true", help="Brug batch-processing til LLM-berigelse (hurtigere, men kræver mere hukommelse)")
    parser.add_argument("--batch-size", type=int, default=10, help="Antal chunks i hver batch ved batch-processing (default: 10)")
    parser.add_argument("--max-workers", type=int, default=5, help="Antal parallelle tråde ved batch-processing (default: 5)")
    args = parser.parse_args()
    
    # Find alle docx-filer i input-mappen
    input_files = list(Path(args.input_dir).glob(args.pattern))
    
    if not input_files:
        print("Ingen .docx filer fundet i input-mappen.")
        return
    
    print(f"Fandt {len(input_files)} filer til processering.")
    
    # Behandl filer
    for file_path in input_files:
        process_file(file_path, use_llm=args.use_llm, use_batch=args.batch, 
                     batch_size=args.batch_size, max_workers=args.max_workers)
    
    print("Processering afsluttet.")

if __name__ == "__main__":
    main()