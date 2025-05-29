"""
Hjælpefunktioner for JAILA.
Indeholder forskellige hjælpefunktioner og utilities.
"""
from typing import List, Dict, Any

def split_text_into_chunks(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """
    Opdeler en tekst i mindre overlappende dele.
    
    Args:
        text: Teksten der skal opdeles.
        chunk_size: Størrelsen på hver del.
        overlap: Antal tegn der overlapper mellem delene.
        
    Returns:
        En liste af tekstdele.
    """
    if not text or len(text) <= chunk_size:
        return [text] if text else []
    
    chunks = []
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        
        # Undgå at dele ord ved slutningen af chunken
        if end < len(text):
            # Find sidste mellemrum før end
            while end > start and text[end] != ' ':
                end -= 1
            
            # Hvis vi ikke kunne finde et mellemrum, så brug den oprindelige end
            if end == start:
                end = min(start + chunk_size, len(text))
        
        chunks.append(text[start:end].strip())
        start = end - overlap if end - overlap > 0 else 0
    
    return chunks
