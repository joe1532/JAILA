"""
Hjælpefunktioner til batch-processing af chunks med LLM.
Optimeret for høj ydeevne og effektiv parallel bearbejdning.
"""
import concurrent.futures
from tqdm import tqdm
import json
import time
import os
import random
from openai import OpenAI
import openai

def enrich_chunks_batch_with_llm(chunks, batch_size=20, max_workers=25):
    """
    Beriger en liste af chunks med LLM-metadata i batches med parallel processering.
    Optimeret for høj ydeevne gennem effektiv ressourceudnyttelse.
    
    Args:
        chunks: Liste af chunks der skal beriges
        batch_size: Antal chunks der behandles ad gangen
        max_workers: Antal parallelle tråde der bruges
        
    Returns:
        Liste af berigede chunks
    """
    # Import her for at undgå cykliske importer
    from chunkerlbkg import enrich_chunk_with_llm, build_embedding_text
    
    # Hvis der ikke er chunks, returner med det samme
    if not chunks:
        return []
        
    # Tjek om vi har en gyldig API-nøgle
    if not os.environ.get("OPENAI_API_KEY") and not openai.api_key:
        print("Advarsel: Ingen OpenAI API-nøgle fundet. LLM-berigelse springes over.")
        return chunks
    
    # Optimer batch_size og workers baseret på antal chunks
    # For få chunks i hver batch er ineffektivt, for mange kan overbelaste API'et
    
    # Sæt en minimumstærskel for batch_size for at reducere overhead
    MIN_BATCH_SIZE = 5
    
    # Sæt en maksimaltærskel for at undgå at overbelaste API'et
    MAX_BATCH_SIZE = 30
    
    # Justerer batch_size dynamisk baseret på mængden af chunks
    if len(chunks) < 20:
        # For meget små job: brug mindre batches
        adjusted_batch_size = max(MIN_BATCH_SIZE, len(chunks) // 2)
    elif len(chunks) < batch_size * max_workers:
        # Mellemstørrelse job: optimer baseret på antal workers
        adjusted_batch_size = max(MIN_BATCH_SIZE, min(MAX_BATCH_SIZE, len(chunks) // max_workers))
    else:
        # Store job: brug den specificerede batch_size eller en optimeret værdi
        adjusted_batch_size = min(MAX_BATCH_SIZE, batch_size)
    
    if adjusted_batch_size != batch_size:
        print(f"Justerer batch-størrelse fra {batch_size} til {adjusted_batch_size} for bedre ressourceudnyttelse")
        batch_size = adjusted_batch_size
        
    # Optimer også antal workers baseret på input-størrelse
    effective_workers = min(max_workers, max(1, len(chunks) // batch_size))
    if effective_workers != max_workers:
        print(f"Justerer antal workers fra {max_workers} til {effective_workers} for bedre ressourceudnyttelse")
        max_workers = effective_workers
    
    # Opdel chunks i sub-batches for at undgå at sende for mange kald til API'et på én gang
    # Dette er mere effektivt og reducerer risikoen for rate limiting
    sub_batches = []
    for i in range(0, len(chunks), batch_size):
        sub_batches.append(chunks[i:i + batch_size])
    
    print(f"Fordeler {len(chunks)} chunks i {len(sub_batches)} sub-batches med størrelse {batch_size}")
    
    # Resultater og progress tracking
    processed_chunks = []
    total_processed = 0
    
    # Opret en global progress bar
    with tqdm(total=len(chunks), desc="Total berigelsesproces") as pbar:
        # For hver sub-batch
        for batch_num, batch in enumerate(sub_batches):
            # Opret input til trådene: (chunk, globalt_index, batch_number)
            batch_with_indices = [(chunk, total_processed + j, batch_num) for j, chunk in enumerate(batch)]
            
            # Hjælpefunktion til at berige en enkelt chunk i en batch med bedre fejlhåndtering
            def enrich_single_chunk(args):
                chunk, chunk_index, batch_index = args
                max_retries = 3
                retry_delay = 2  # sekunder
                
                for retry in range(max_retries):
                    try:
                        # Tilføj en lille, progressiv forsinkelse for at undgå rate limiting
                        if retry > 0:
                            delay = retry_delay * (1 + random.random()) * retry
                            time.sleep(delay)
                            
                        # Berig chunk med LLM
                        enriched_chunk = enrich_chunk_with_llm(chunk)
                        
                        # Opdater embedding_text EFTER metadata er opdateret med keywords
                        if enriched_chunk and isinstance(enriched_chunk, dict):
                            enriched_chunk["embedding_text"] = build_embedding_text(enriched_chunk)
                        
                        return enriched_chunk
                    except (openai.RateLimitError, openai.APITimeoutError) as e:
                        # Hvis vi rammer rate limit, vent længere og prøv igen
                        if retry < max_retries - 1:
                            # Øg ventetiden eksponentielt (backoff) med lidt tilfældighed for at undgå samtidige retries
                            base_wait = 2 ** retry  # 1, 2, 4, 8, 16 sekunder...
                            # Tilføj jitter (tilfældighed) på +/- 30% for at undgå synkroniserede retries
                            jitter = base_wait * 0.3 * (random.random() * 2 - 1)
                            wait_time = base_wait + jitter
                            
                            print(f"Rate limit/timeout for chunk {chunk_index} i batch {batch_index}. Venter {wait_time:.1f}s ({retry+1}/{max_retries}).")
                            time.sleep(wait_time)
                        else:
                            print(f"Maksimale forsøg nået for chunk {chunk_index}: {e}")
                            # Selv ved max forsøg, giv serveren en kort pause før vi returnerer
                            time.sleep(1)
                            return chunk  # Returner uændret chunk efter max forsøg
                    except Exception as e:
                        print(f"Fejl i batch-berigelse af chunk {chunk_index}: {e}")
                        # For andre fejl, stop forsøg og returner uændret chunk
                        return chunk
                
                # Hvis vi kommer hertil, er alle forsøg fejlet
                return chunk
            
            print(f"Behandler sub-batch {batch_num+1}/{len(sub_batches)} med {len(batch)} chunks...")
            
            # Brug ThreadPoolExecutor med dynamisk tilpasset antal workers
            # Vi bruger færre workers end max_workers for små batches
            effective_workers = min(max_workers, len(batch))
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=effective_workers) as executor:
                # Start alle opgaver
                future_to_chunk = {executor.submit(enrich_single_chunk, args): args[1] 
                                  for args in batch_with_indices}
                
                # Behandl resultater efterhånden som de er færdige
                for future in concurrent.futures.as_completed(future_to_chunk):
                    try:
                        # Få resultatet
                        result = future.result()
                        processed_chunks.append(result)
                        # Opdater progress bar
                        pbar.update(1)
                    except Exception as e:
                        # Håndter eventuelle undtagelser, der opstod under eksekvering
                        chunk_index = future_to_chunk[future]
                        print(f"Uventet fejl ved behandling af chunk {chunk_index}: {e}")
                        # Tilføj den oprindelige chunk hvis vi kan finde den
                        orig_chunk = next((c for c, idx, _ in batch_with_indices if idx == chunk_index), None)
                        if orig_chunk:
                            processed_chunks.append(orig_chunk)
                        pbar.update(1)
            
            # Opdater total_processed
            total_processed += len(batch)
            
            # Lille pause mellem batches for at undgå rate limiting
            if batch_num < len(sub_batches) - 1:
                time.sleep(0.5)
    
    # Sikre at vi returnerer chunks i samme rækkefølge som input
    if len(processed_chunks) == len(chunks):
        # Opret en map fra chunk_id til chunk for hurtig opslag
        processed_map = {c.get("chunk_id"): c for c in processed_chunks 
                        if isinstance(c, dict) and "chunk_id" in c}
        
        # Rekonstruer den oprindelige rækkefølge
        result = []
        for original in chunks:
            if isinstance(original, dict) and "chunk_id" in original:
                chunk_id = original.get("chunk_id")
                if chunk_id in processed_map:
                    result.append(processed_map[chunk_id])
                else:
                    result.append(original)
            else:
                # For chunks uden ID, brug den oprindelige
                result.append(original)
        
        return result
    else:
        # Hvis antal resultater ikke matcher input, returner raw results
        print(f"Advarsel: Antal berigede chunks ({len(processed_chunks)}) matcher ikke input ({len(chunks)}).")
        return processed_chunks
