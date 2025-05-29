"""
Opslagsfunktioner for JAILA.
Indeholder RAG-funktionalitet, herunder standard, multihop og hybrid søgning.
"""
import re
import os
from typing import List, Dict, Any, Optional, Tuple

from langchain.chains.question_answering import load_qa_chain
from langchain_openai import ChatOpenAI
from langchain.schema import Document
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain.memory import ConversationBufferMemory

from JAILA.connections import get_vector_store, check_weaviate_connection
from JAILA.prompts import create_multihop_prompt_templates, create_qa_prompt_template
from JAILA.config import DEFAULT_MODEL, DEFAULT_TEMPERATURE
from JAILA.hybrid_search import robust_search  # Importerer vores nye robuste søgemetode

# Import MultiQueryRetriever hvis tilgængelig
try:
    from langchain.retrievers import MultiQueryRetriever
except ImportError:
    print("MultiQueryRetriever ikke tilgængelig - bruger standard retriever i stedet")
    MultiQueryRetriever = None

def setup_llm(model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
    """Opsæt og returner en LLM-model."""
    return ChatOpenAI(model_name=model, temperature=temperature)

def setup_retriever(k: int = 5):
    """
    Opsætter en standard retriever.
    
    Args:
        k: Antal dokumenter at hente.
        
    Returns:
        En retriever til at hente dokumenter.
    """
    vector_store = get_vector_store()
    return vector_store.as_retriever(search_kwargs={"k": k})

def setup_advanced_retriever(llm=None, k: int = 5):
    """
    Opsætter en avanceret retriever med MultiQuery funktionalitet hvis tilgængelig.
    
    Args:
        llm: LLM-model til at generere forskellige forespørgsler.
        k: Antal dokumenter at hente.
        
    Returns:
        En avanceret retriever til at hente dokumenter.
    """
    if MultiQueryRetriever is None:
        print("MultiQueryRetriever ikke tilgængelig - bruger standard retriever")
        return setup_retriever(k=k)
    
    if llm is None:
        llm = setup_llm()
    
    vector_store = get_vector_store()
    print("Bruger MultiQueryRetriever for forbedrede resultater")
    
    retriever = MultiQueryRetriever.from_llm(
        retriever=vector_store.as_retriever(search_kwargs={"k": k}),
        llm=llm
    )
    
    return retriever

def format_docs(docs):
    """Formaterer dokumenter til en streng."""
    return "\n\n".join([doc.page_content for doc in docs])

def juridisk_søgning(spørgsmål: str, antal_resultater: int = 5, model: str = DEFAULT_MODEL):
    """
    Udfører en juridisk søgning baseret på et spørgsmål.
    
    Args:
        spørgsmål: Det juridiske spørgsmål at søge efter.
        antal_resultater: Antal dokumenter at hente.
        model: Navnet på LLM-modellen at bruge.
        
    Returns:
        En ordbog med svaret, spørgsmålet og kildedokumenterne.
    """
    # Prøv først med den robuste søgemetode
    try:
        print("Bruger robust søgemetode...")
        return robust_juridisk_søgning(spørgsmål, antal_resultater, model)
    except Exception as e:
        print(f"Robust søgning fejlede: {e}")
        print("Falder tilbage til standard søgemetode...")
    
    # Fallback: Brug standard-metoden hvis den robuste fejler
    # Kontroller Weaviate-forbindelse
    if not check_weaviate_connection():
        return {
            "answer": "Beklager, jeg kunne ikke oprette forbindelse til vores juridiske database. Prøv igen senere.",
            "question": spørgsmål,
            "source_documents": []
        }
    
    # Opsæt LLM og retriever
    llm = setup_llm(model=model)
    retriever = setup_retriever(k=antal_resultater)
    
    # Hent relevante dokumenter
    docs = retriever.get_relevant_documents(spørgsmål)
    
    if not docs:
        return {
            "answer": "Jeg kunne ikke finde nogen relevante juridiske dokumenter om dit spørgsmål.",
            "question": spørgsmål,
            "source_documents": []
        }
    
    # Forbered kontekst fra dokumenterne
    context = format_docs(docs)
    
    # Opret QA-kæde med vores prompt
    qa_prompt = create_qa_prompt_template()
    qa_chain = load_qa_chain(
        llm=llm,
        chain_type="stuff",
        prompt=qa_prompt
    )
    
    # Generer svar
    answer = qa_chain.run(question=spørgsmål, context=context)
    
    return {
        "answer": answer,
        "question": spørgsmål,
        "source_documents": docs
    }

def multihop_juridisk_søgning(spørgsmål: str, antal_resultater: int = 5, model: str = DEFAULT_MODEL):
    """
    Udfører en multihop juridisk søgning, hvor komplekse spørgsmål nedbrydes i delspørgsmål.
    
    Args:
        spørgsmål: Det komplekse juridiske spørgsmål at søge efter.
        antal_resultater: Antal dokumenter at hente for hvert delspørgsmål.
        model: Navnet på LLM-modellen at bruge.
        
    Returns:
        En ordbog med det endelige svar, spørgsmålet og mellemliggende resultater.
    """
    # Kontroller Weaviate-forbindelse
    if not check_weaviate_connection():
        return {
            "answer": "Beklager, jeg kunne ikke oprette forbindelse til vores juridiske database. Prøv igen senere.",
            "question": spørgsmål,
            "intermediate_results": []
        }
    
    # Opsæt LLM
    llm = setup_llm(model=model)
    
    # Brug vores avancerede retriever hvis muligt, ellers fald tilbage til standard retriever
    try:
        retriever = setup_advanced_retriever(llm=llm, k=antal_resultater)
    except Exception as e:
        print(f"Kunne ikke opsætte avanceret retriever: {e}")
        print("Bruger standard retriever i stedet")
        retriever = setup_retriever(k=antal_resultater)
    
    prompt_templates = create_multihop_prompt_templates()
    
    # Trin 1: Genererer delspørgsmål baseret på det oprindelige spørgsmål
    print(f"Analyserer spørgsmål: {spørgsmål}")
    
    # Brug en simpel prompt-template og direkte LLM-kald i stedet for chain
    first_hop_prompt = prompt_templates["first_hop"]
    first_hop_result = llm.invoke(first_hop_prompt.format(question=spørgsmål)).content
    
    # Parser delspørgsmålene fra resultatet
    sub_questions = [sq.strip() for sq in first_hop_result.split('\n') if sq.strip()]
    print(f"Genererede {len(sub_questions)} delspørgsmål: {sub_questions}")
    
    # Trin 2: Søg efter svar på hvert delspørgsmål
    all_intermediate_results = []
    for i, sub_q in enumerate(sub_questions):
        try:
            print(f"Behandler delspørgsmål {i+1}: {sub_q}\n")
            
            # Brug vores robuste søgemetode i stedet for standard retriever
            print(f"Bruger robust søgning for delspørgsmål {i+1}...")
            try:
                # Prøv den robuste søgemetode først
                search_results = robust_search(sub_q, limit=antal_resultater)
                
                # Konverter søgeresultater til dokumenter
                docs = []
                for res in search_results:
                    # Opret metadata
                    metadata = {}
                    for key in ["title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]:
                        if key in res and res[key]:
                            metadata[key] = res[key]
                    
                    # Opret Document objekt
                    doc = Document(page_content=res["text"], metadata=metadata)
                    docs.append(doc)
                    
                print(f"Robust søgning fandt {len(docs)} dokumenter for delspørgsmål {i+1}")
            except Exception as e:
                print(f"Robust søgning fejlede for delspørgsmål {i+1}: {e}")
                print("Falder tilbage til standard retriever...")
                # Fald tilbage til standard retriever hvis robust søgning fejler
                docs = retriever.get_relevant_documents(sub_q)
            
            # Hvis der ikke er nogen dokumenter, så fortæller vi det
            if not docs:
                print(f"Ingen relevante dokumenter fundet for delspørgsmål: {sub_q}")
                intermediate_result = f"Jeg kunne ikke finde relevante oplysninger om '{sub_q}' i de juridiske dokumenter."
                all_intermediate_results.append(intermediate_result)
                continue
                
            # Forbered dokumentindholdet til input
            context = "\n\n".join([doc.page_content for doc in docs])
            
            # Brug direkte LLM-kald i stedet for chain
            intermediate_hop_prompt = prompt_templates["intermediate_hop"]
            intermediate_result = llm.invoke(
                intermediate_hop_prompt.format(question=sub_q, context=context)
            ).content
            all_intermediate_results.append(intermediate_result)
            
            print(f"Svar på delspørgsmål {i+1}: {intermediate_result[:100]}...")
        except Exception as e:
            print(f"Fejl ved behandling af delspørgsmål {i+1}: {e}")
    
    # Trin 3: Generer det endelige svar baseret på alle delresultater
    print("Genererer endeligt svar...")
    
    # Opret strukturerede mellemresultater med delspørgsmål og svar
    structured_intermediate_results = []
    for i, (sub_q, answer) in enumerate(zip(sub_questions, all_intermediate_results)):
        structured_intermediate_results.append({
            "question": sub_q,
            "answer": answer,
            # Vi har ikke dokument-referencer her, men kunne tilføje det i fremtiden
            "source_documents": []
        })
    
    # Sammensæt alle delresultater til én samlet kontekst
    intermediate_context = "\n\n".join(all_intermediate_results)
    
    # Generer det endelige svar ved at bruge direkte LLM-kald
    final_answer_prompt = prompt_templates["final_hop"]
    final_answer = llm.invoke(
        final_answer_prompt.format(original_question=spørgsmål, hop_results=intermediate_context)
    ).content
    
    # Afslut på en pæn måde
    return {
        "question": spørgsmål,
        "answer": final_answer,
        "intermediate_results": structured_intermediate_results,
        "sub_questions": sub_questions  # Gem også de oprindelige delspørgsmål separat
    }

def robust_juridisk_søgning(spørgsmål: str, antal_resultater: int = 5, model: str = DEFAULT_MODEL) -> Dict:
    """Udfør juridisk søgning med vores robuste søgemetode, der virker selvom Weaviate har DNS-problemer"""
    
    # Konverter spørgsmål til en prompt
    prompt_template = create_qa_prompt_template()
    
    # Opret LLM
    llm = ChatOpenAI(temperature=DEFAULT_TEMPERATURE, model=model, api_key=os.environ.get("OPENAI_API_KEY"))
    
    # Brug vores robuste søgefunktion i stedet for standard Weaviate-søgning
    søgeresultater = robust_search(spørgsmål, limit=antal_resultater)
    
    if not søgeresultater:
        return {
            "answer": "Jeg kunne ikke finde relevante dokumenter til at besvare dit spørgsmål. "
                      "Prøv venligst at omformulere spørgsmålet eller spørg om noget andet.",
            "question": spørgsmål,
            "source_documents": []
        }
    
    # Konverter søgeresultater til dokumenter
    dokumenter = []
    for res in søgeresultater:
        # Opret metadata
        metadata = {}
        for key in ["title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]:
            if key in res and res[key]:
                metadata[key] = res[key]
        
        # Opret Document objekt
        doc = Document(page_content=res["text"], metadata=metadata)
        dokumenter.append(doc)
    
    # Generer svar med LLM
    prompt_input = {
        "question": spørgsmål,
        "context": "\n\n".join([doc.page_content for doc in dokumenter])
    }
    chain = prompt_template | llm
    svar = chain.invoke(prompt_input).content
    
    # Returner resultat
    return {
        "answer": svar,
        "question": spørgsmål,
        "source_documents": dokumenter
    }

def hybrid_søgning(query: str, filters: Optional[Dict] = None, limit: int = 5) -> List[Dict]:
    """Udfør en hybrid søgning med både vektor- og nøgleordsbaseret søgning"""
    # Prøv først vores robuste søgemetode
    try:
        resultater = robust_search(query, limit=limit)
        if resultater:
            return resultater
    except Exception as e:
        print(f"Robust søgning fejlede: {e}")
    
    # Hvis robust søgning fejler, prøv den oprindelige metode
    if not check_weaviate_connection():
        print("Advarsel: Weaviate er ikke tilgængelig. Kan ikke udføre hybrid søgning.")
        return []
    
    vector_store = get_vector_store()
    if not isinstance(vector_store, DummyVectorStore):
        try:
            # Få adgang til den underliggende Weaviate-klient
            client = vector_store._client
            
            # Opret en GraphQL-forespørgsel med hybrid søgning
            query_obj = client.query.get(
                CLASS_NAME, 
                ["text", "title", "law_number", "paragraph", "stk", "nr", "heading", "summary"]
            ).with_hybrid(
                query=query,
                alpha=0.5  # Balance mellem vektor- og nøgleordssøgning
            ).with_limit(limit)
            
            # Tilføj eventuelle filtre
            if filters:
                for key, value in filters.items():
                    query_obj = query_obj.with_where({
                        "path": [key],
                        "operator": "Equal",
                        "valueString": value
                    })
            
            # Udfør søgningen
            result = query_obj.do()
            
            # Udtræk resultater
            if "data" in result and "Get" in result["data"] and CLASS_NAME in result["data"]["Get"]:
                return result["data"]["Get"][CLASS_NAME]
            else:
                return []
        except Exception as e:
            print(f"Fejl ved hybrid søgning: {e}")
            return []
    
    return []
