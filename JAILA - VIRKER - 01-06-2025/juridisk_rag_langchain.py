#!/usr/bin/env python3
"""
JURIDISK RAG MODEL - LangChain Implementation with Multihop Reasoning
Bygget på search_engine.py med LangChain framework og GPT-4o-2024-08-06
"""

from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain.schema.messages import HumanMessage, SystemMessage
from langchain.prompts import PromptTemplate
import os
import sys
from dotenv import load_dotenv
from typing import List, Dict, Optional, Tuple, Any
import time
import json
from dataclasses import dataclass
from enum import Enum

# Import vores eksisterende søgemaskine
from search_engine import SearchEngine

# Indlæs miljøvariabler
load_dotenv()

class SearchStrategy(Enum):
    """Søgestrategi enumeration"""
    AUTO = "auto"
    PARAGRAPH_FIRST = "paragraph_first"
    SEMANTIC_FIRST = "semantic_first"
    HYBRID = "hybrid"
    MULTIHOP = "multihop"

@dataclass
class LangChainRAGConfig:
    """Konfiguration for LangChain RAG modellen"""
    # LLM settings - GPT-4o-2024-08-06
    model: str = "gpt-4o-2024-08-06"
    temperature: float = 0.1
    max_tokens: int = 2000
    
    # Retrieval settings
    max_documents_per_hop: int = 5
    max_hops: int = 3
    search_strategy: SearchStrategy = SearchStrategy.MULTIHOP
    include_related_notes: bool = True
    
    # Context settings
    max_context_length: int = 12000
    context_overlap: int = 300
    
    # Multihop settings
    enable_multihop: bool = True
    hop_confidence_threshold: float = 0.4
    max_reasoning_depth: int = 3
    
    # Citation settings
    include_citations: bool = True
    citation_format: str = "detailed"

class WeaviateRetriever:
    """
    LangChain-kompatibel retriever der bruger vores SearchEngine
    """
    
    def __init__(self, search_engine: SearchEngine, search_strategy: str = "auto", max_docs: int = 5):
        self.search_engine = search_engine
        self.search_strategy = search_strategy
        self.max_docs = max_docs
    
    def get_relevant_documents(self, query: str) -> List[Document]:
        """Hent relevante dokumenter og konverter til LangChain Documents"""
        
        # Brug vores SearchEngine til at finde dokumenter
        search_results = self.search_engine.search(
            query=query,
            limit=self.max_docs,
            search_type=self.search_strategy
        )
        
        # Konverter til LangChain Document format
        documents = []
        for result in search_results:
            # Byg metadata
            metadata = {
                "chunk_id": result.get('chunk_id', ''),
                "title": result.get('title', ''),
                "paragraph": result.get('paragraph', ''),
                "stk": result.get('stk', ''),
                "nr": result.get('nr', ''),
                "type": result.get('type', ''),
                "law_number": result.get('law_number', ''),
                "reference": self._build_reference_string(result)
            }
            
            # Byg page_content
            page_content = result.get('text', '')
            
            # Tilføj kontekst information til content
            if result.get('paragraph'):
                page_content = f"[{self._build_reference_string(result)}]\n\n{page_content}"
            
            doc = Document(
                page_content=page_content,
                metadata=metadata
            )
            documents.append(doc)
        
        return documents
    
    def _build_reference_string(self, result: Dict) -> str:
        """Byg reference string for dokument"""
        parts = []
        if result.get('title'):
            parts.append(result.get('title'))
        if result.get('paragraph'):
            parts.append(result.get('paragraph'))
        if result.get('stk'):
            parts.append(f"stk. {result.get('stk')}")
        if result.get('nr'):
            parts.append(f"nr. {result.get('nr')}")
        
        return ", ".join(parts) if parts else "N/A"

class MultihopJuridiskRAG:
    """
    LangChain-baseret Juridisk RAG med Multihop Reasoning
    
    Kombinerer præcis dokumentsøgning med intelligent multi-step reasoning
    for at besvare komplekse juridiske spørgsmål.
    """
    
    def __init__(self, config: LangChainRAGConfig = None, weaviate_url: str = "http://localhost:8080", verbose: bool = True):
        """
        Initialize LangChain RAG system
        
        Args:
            config: RAG konfiguration
            weaviate_url: Weaviate database URL
            verbose: Print progress og debug info
        """
        self.config = config or LangChainRAGConfig()
        self.verbose = verbose
        
        # Initialize OpenAI LLM via LangChain
        self.llm = ChatOpenAI(
            model=self.config.model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        
        # Initialize søgemaskinen
        self.search_engine = SearchEngine(weaviate_url=weaviate_url, verbose=verbose)
        
        # Initialize retriever
        self.retriever = WeaviateRetriever(
            search_engine=self.search_engine,
            search_strategy="auto",
            max_docs=self.config.max_documents_per_hop
        )
        
        # Setup multihop reasoning chain
        self._setup_multihop_chain()
        
        # Test forbindelser
        self._validate_connections()
        
        if self.verbose:
            print("🚀 LANGCHAIN MULTIHOP RAG SYSTEM KLAR")
            print(f"   Model: {self.config.model}")
            print(f"   Max hops: {self.config.max_hops}")
            print(f"   Max docs per hop: {self.config.max_documents_per_hop}")
            print(f"   Multihop enabled: {self.config.enable_multihop}")
    
    def _setup_multihop_chain(self):
        """Setup LangChain chains for multihop reasoning"""
        
        # STEP 1: Query Analysis Chain
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
        
        # STEP 2: Document Analysis Chain
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
        
        # STEP 3: Final Answer Chain
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
    
    def _validate_connections(self) -> None:
        """Validér at alle forbindelser virker"""
        # Test Weaviate
        if not self.search_engine.test_connection():
            raise ConnectionError("Kan ikke forbinde til Weaviate database")
        
        # Test OpenAI via LangChain
        if not os.getenv("OPENAI_API_KEY"):
            raise ValueError("OPENAI_API_KEY environment variable ikke sat")
        
        try:
            # Quick test af LangChain LLM
            test_response = self.llm.invoke([HumanMessage(content="test")])
        except Exception as e:
            raise ConnectionError(f"Kan ikke forbinde til OpenAI API via LangChain: {e}")
    
    def ask(self, question: str) -> Dict:
        """
        Hovedfunktion: Still juridisk spørgsmål med multihop reasoning
        
        Args:
            question: Det juridiske spørgsmål
            
        Returns:
            Dict med svar, kilder, reasoning path og metadata
        """
        start_time = time.time()
        
        if self.verbose:
            print(f"\n❓ MULTIHOP SPØRGSMÅL: {question}")
            print("=" * 80)
        
        if self.config.enable_multihop:
            return self._multihop_reasoning(question, start_time)
        else:
            return self._single_hop_answer(question, start_time)
    
    def _multihop_reasoning(self, question: str, start_time: float) -> Dict:
        """
        MULTIHOP REASONING PIPELINE
        """
        reasoning_path = []
        all_documents = {"hop1": [], "hop2": [], "hop3": []}
        
        # STEP 1: Query Analysis
        if self.verbose:
            print("🔍 STEP 1: Query Analysis")
        
        query_analysis = self._analyze_query(question)
        reasoning_path.append({
            "step": "query_analysis",
            "analysis": query_analysis,
            "timestamp": time.time() - start_time
        })
        
        # STEP 2: Initial Search (HOP 1)
        if self.verbose:
            print("🔍 STEP 2: Initial Search (HOP 1)")
        
        initial_docs = self._perform_search(question, hop_number=1)
        all_documents["hop1"] = initial_docs
        
        if not initial_docs:
            return self._create_no_results_response(question, reasoning_path, time.time() - start_time)
        
        # STEP 3: Analyze Initial Results
        doc_analysis = self._analyze_documents(question, initial_docs, hop_number=1)
        reasoning_path.append({
            "step": "hop1_analysis",
            "analysis": doc_analysis,
            "documents_found": len(initial_docs),
            "timestamp": time.time() - start_time
        })
        
        # STEP 4: Determine if more hops needed
        if doc_analysis.get("needs_more_search") and len(reasoning_path) < self.config.max_hops:
            
            # HOP 2
            if self.verbose:
                print("🔍 STEP 4: Follow-up Search (HOP 2)")
            
            for next_query in doc_analysis.get("next_queries", [])[:2]:  # Max 2 follow-up queries
                hop2_docs = self._perform_search(next_query, hop_number=2)
                all_documents["hop2"].extend(hop2_docs)
            
            if all_documents["hop2"]:
                hop2_analysis = self._analyze_documents(question, all_documents["hop2"], hop_number=2)
                reasoning_path.append({
                    "step": "hop2_analysis",
                    "analysis": hop2_analysis,
                    "documents_found": len(all_documents["hop2"]),
                    "timestamp": time.time() - start_time
                })
                
                # HOP 3 (if needed)
                if hop2_analysis.get("needs_more_search") and len(reasoning_path) < self.config.max_hops:
                    if self.verbose:
                        print("🔍 STEP 5: Deep Search (HOP 3)")
                    
                    for next_query in hop2_analysis.get("next_queries", [])[:1]:  # Max 1 deep query
                        hop3_docs = self._perform_search(next_query, hop_number=3)
                        all_documents["hop3"].extend(hop3_docs)
        
        # STEP 5: Generate Final Answer
        if self.verbose:
            print("🤖 STEP 6: Generate Multihop Answer")
        
        final_answer = self._generate_multihop_answer(question, all_documents, reasoning_path)
        
        # STEP 6: Package Response
        response_time = time.time() - start_time
        return self._package_multihop_response(final_answer, all_documents, reasoning_path, response_time)
    
    def _analyze_query(self, question: str) -> Dict:
        """Analyser spørgsmål for multihop strategi"""
        try:
            prompt = self.query_analysis_template.format(question=question)
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"needs_multihop": False, "search_queries": [question]}
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Query analysis fejl: {e}")
            return {"needs_multihop": False, "search_queries": [question]}
    
    def _perform_search(self, query: str, hop_number: int) -> List[Document]:
        """Udfør søgning for et specifikt hop"""
        if self.verbose:
            print(f"   🔎 Søger (HOP {hop_number}): {query}")
        
        docs = self.retriever.get_relevant_documents(query)
        
        if self.verbose:
            print(f"   📄 Fandt {len(docs)} dokumenter")
        
        return docs
    
    def _analyze_documents(self, question: str, documents: List[Document], hop_number: int) -> Dict:
        """Analyser dokumenter for at bestemme næste skridt"""
        try:
            docs_text = "\n\n".join([f"DOC {i+1}: {doc.page_content[:500]}..." for i, doc in enumerate(documents)])
            
            prompt = self.doc_analysis_template.format(
                question=question,
                documents=docs_text
            )
            
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', response.content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                return {"needs_more_search": False, "next_queries": []}
        except Exception as e:
            if self.verbose:
                print(f"⚠️  Document analysis fejl: {e}")
            return {"needs_more_search": False, "next_queries": []}
    
    def _generate_multihop_answer(self, question: str, all_documents: Dict, reasoning_path: List) -> str:
        """Generer final answer baseret på alle hops"""
        
        # Format documents fra alle hops
        hop1_text = self._format_documents_for_prompt(all_documents["hop1"])
        hop2_text = self._format_documents_for_prompt(all_documents["hop2"])
        hop3_text = self._format_documents_for_prompt(all_documents["hop3"])
        
        # Format reasoning path
        reasoning_text = "\n".join([
            f"STEP {i+1}: {step['step']} -> {step.get('analysis', {}).get('reasoning', 'N/A')}"
            for i, step in enumerate(reasoning_path)
        ])
        
        prompt = self.answer_template.format(
            question=question,
            hop1_docs=hop1_text,
            hop2_docs=hop2_text,
            hop3_docs=hop3_text,
            reasoning_path=reasoning_text
        )
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content
    
    def _format_documents_for_prompt(self, documents: List[Document]) -> str:
        """Format dokumenter til LLM prompt"""
        if not documents:
            return "Ingen dokumenter fundet i dette hop."
        
        formatted = []
        for i, doc in enumerate(documents, 1):
            metadata = doc.metadata
            reference = metadata.get('reference', 'N/A')
            
            formatted.append(f"""
DOKUMENT {i}:
Reference: {reference}
Chunk ID: {metadata.get('chunk_id', 'N/A')[:8]}...
Type: {metadata.get('type', 'N/A')}

INDHOLD:
{doc.page_content[:1000]}{'...' if len(doc.page_content) > 1000 else ''}
""")
        
        return "\n".join(formatted)
    
    def _single_hop_answer(self, question: str, start_time: float) -> Dict:
        """Fallback til single-hop hvis multihop er deaktiveret"""
        if self.verbose:
            print("🔍 SINGLE HOP MODE")
        
        # Simpel retrieval
        documents = self.retriever.get_relevant_documents(question)
        
        if not documents:
            return self._create_no_results_response(question, [], time.time() - start_time)
        
        # Simpel generation
        docs_text = self._format_documents_for_prompt(documents)
        
        simple_prompt = f"""
Du er ekspert i dansk skatteret. Besvar følgende spørgsmål baseret på dokumenterne.

SPØRGSMÅL: {question}

DOKUMENTER:
{docs_text}

SVAR:
"""
        
        response = self.llm.invoke([HumanMessage(content=simple_prompt)])
        
        return {
            "answer": response.content,
            "sources": [self._doc_to_source(doc) for doc in documents],
            "document_count": len(documents),
            "reasoning_path": [{"step": "single_hop", "documents_found": len(documents)}],
            "multihop_used": False,
            "response_time": time.time() - start_time,
            "model_used": self.config.model
        }
    
    def _package_multihop_response(self, answer: str, all_documents: Dict, reasoning_path: List, response_time: float) -> Dict:
        """Package final multihop response"""
        
        # Saml alle dokumenter
        all_docs = all_documents["hop1"] + all_documents["hop2"] + all_documents["hop3"]
        
        # Beregn confidence baseret på antal hops og dokumenter
        confidence = self._calculate_multihop_confidence(all_documents, reasoning_path)
        
        return {
            "answer": answer,
            "sources": [self._doc_to_source(doc) for doc in all_docs],
            "document_count": len(all_docs),
            "confidence": confidence,
            "reasoning_path": reasoning_path,
            "multihop_used": True,
            "hops_performed": len([step for step in reasoning_path if "hop" in step["step"]]),
            "documents_per_hop": {
                "hop1": len(all_documents["hop1"]),
                "hop2": len(all_documents["hop2"]),
                "hop3": len(all_documents["hop3"])
            },
            "response_time": response_time,
            "model_used": self.config.model,
            "config": {
                "max_hops": self.config.max_hops,
                "max_docs_per_hop": self.config.max_documents_per_hop,
                "enable_multihop": self.config.enable_multihop
            }
        }
    
    def _doc_to_source(self, doc: Document) -> Dict:
        """Konverter LangChain Document til source info"""
        return {
            "chunk_id": doc.metadata.get('chunk_id', 'N/A'),
            "title": doc.metadata.get('title', 'N/A'),
            "reference": doc.metadata.get('reference', 'N/A'),
            "type": doc.metadata.get('type', 'N/A'),
            "text_preview": doc.page_content[:200] + "..."
        }
    
    def _calculate_multihop_confidence(self, all_documents: Dict, reasoning_path: List) -> float:
        """Beregn confidence score for multihop answer"""
        base_score = 0.5
        
        # Boost for flere dokumenter
        total_docs = sum(len(docs) for docs in all_documents.values())
        if total_docs >= 5:
            base_score += 0.2
        elif total_docs >= 3:
            base_score += 0.1
        
        # Boost for successful multihop
        successful_hops = len([step for step in reasoning_path if "hop" in step["step"] and step.get("documents_found", 0) > 0])
        base_score += successful_hops * 0.1
        
        # Boost for paragraph documents
        paragraph_docs = sum(1 for docs in all_documents.values() for doc in docs if doc.metadata.get('type') == 'paragraf')
        if paragraph_docs > 0:
            base_score += 0.1
        
        return min(base_score, 1.0)
    
    def _create_no_results_response(self, question: str, reasoning_path: List, response_time: float) -> Dict:
        """Håndter tilfælde hvor ingen dokumenter findes"""
        return {
            "answer": "Beklager, jeg kunne ikke finde relevante juridiske dokumenter for dit spørgsmål gennem multihop søgning. Prøv at omformulere spørgsmålet eller vær mere specifik.",
            "sources": [],
            "document_count": 0,
            "confidence": 0.0,
            "reasoning_path": reasoning_path,
            "multihop_used": True,
            "hops_performed": 0,
            "response_time": response_time,
            "model_used": self.config.model
        }
    
    def interactive_mode(self):
        """Interaktiv multihop RAG session"""
        print("\n🎯 LANGCHAIN MULTIHOP RAG - INTERAKTIV MODE")
        print("=" * 60)
        print("Stil komplekse juridiske spørgsmål - indtast 'quit' for at afslutte")
        print("Kommandoer:")
        print("  '/hops on|off' - toggle multihop reasoning")
        print("  '/config' - vis nuværende konfiguration")
        print("  '/help' - vis hjælp")
        
        while True:
            try:
                question = input("\n❓ Spørgsmål: ").strip()
                
                if question.lower() in ['quit', 'q', 'exit']:
                    print("👋 Farvel!")
                    break
                elif question.startswith('/hops'):
                    setting = question.split()[-1] if len(question.split()) > 1 else "on"
                    self.config.enable_multihop = setting.lower() == "on"
                    print(f"✅ Multihop {'aktiveret' if self.config.enable_multihop else 'deaktiveret'}")
                    continue
                elif question == '/config':
                    print(f"Nuværende konfiguration:")
                    print(f"  Model: {self.config.model}")
                    print(f"  Max hops: {self.config.max_hops}")
                    print(f"  Max docs per hop: {self.config.max_documents_per_hop}")
                    print(f"  Multihop enabled: {self.config.enable_multihop}")
                    continue
                elif question == '/help':
                    print("Eksempler på komplekse spørgsmål:")
                    print("  'Hvad er forskellen mellem kildeskattelovens § 2 og ligningslovens § 7?'")
                    print("  'Hvordan påvirker aktieavancebeskatningsloven skattepligten i § 1?'")
                    print("  'Sammenhængen mellem begrænset skattepligt og fradrag'")
                    continue
                elif not question:
                    continue
                
                # Process spørgsmål med multihop
                result = self.ask(question)
                
                # Print svar
                print(f"\n💬 MULTIHOP SVAR:")
                print("-" * 50)
                print(result['answer'])
                
                print(f"\n📊 MULTIHOP METADATA:")
                print(f"   Kilder: {result['document_count']} dokumenter")
                print(f"   Confidence: {result['confidence']:.1%}")
                print(f"   Hops performed: {result.get('hops_performed', 0)}")
                print(f"   Tid: {result['response_time']:.1f}s")
                print(f"   Model: {result['model_used']}")
                
                if result.get('reasoning_path'):
                    print(f"\n🧠 REASONING PATH:")
                    for i, step in enumerate(result['reasoning_path'], 1):
                        print(f"   {i}. {step['step']}: {step.get('documents_found', 0)} docs")
                
                if result.get('sources'):
                    print(f"\n📚 KILDER (Top 3):")
                    for i, source in enumerate(result['sources'][:3], 1):
                        print(f"   {i}. {source['reference']} ({source['chunk_id'][:8]}...)")
                
            except KeyboardInterrupt:
                print("\n👋 Afbrudt")
                break
            except EOFError:
                break

def main():
    """Hovedprogram"""
    print("🚀 LANGCHAIN MULTIHOP JURIDISK RAG SYSTEM")
    
    if len(sys.argv) > 1:
        # Kommandolinje brug
        question = ' '.join(sys.argv[1:])
        rag = MultihopJuridiskRAG()
        result = rag.ask(question)
        
        print(f"\n💬 MULTIHOP SVAR:")
        print(result['answer'])
        print(f"\n📊 {result['document_count']} kilder, {result['hops_performed']} hops, confidence: {result['confidence']:.1%}")
        
    else:
        # Interaktiv mode
        rag = MultihopJuridiskRAG()
        rag.interactive_mode()

if __name__ == "__main__":
    main() 