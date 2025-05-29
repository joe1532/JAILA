"""
JAILA - Juridisk AI og LangChain Application
Dette modul integrerer LangChain for juridisk RAG-system med multihop-funktionalitet.
"""

# Eksporter hovedfunktioner, så de er direkte tilgængelige ved import
from JAILA.retrieval import juridisk_søgning, multihop_juridisk_søgning, hybrid_søgning
from JAILA.connections import check_weaviate_connection

# Version
__version__ = "0.1.0"
