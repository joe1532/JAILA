"""
Test-funktioner for JAILA-systemet.
Bruges til at validere, at modulerne fungerer korrekt.
"""
from typing import Optional

from JAILA.retrieval import juridisk_søgning, multihop_juridisk_søgning, hybrid_søgning
from JAILA.connections import check_weaviate_connection
from JAILA.config import weaviate_url
import os

def test_integration(test_type="multihop", test_query="Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel, og hvordan påvirker det beregningen af skatten?"):
    """Testfunktion for at validere JAILA-integrationen."""
    print("Tester JAILA integration med multihop RAG...")
    
    try:
        if test_type == "normal":
            result = juridisk_søgning(test_query)
            print(f"Resultat: {result['answer'][:500]}...\n")
            print(f"Antal fundne dokumenter: {len(result['source_documents'])}")
            
        elif test_type == "multihop":
            print(f"Kører multihop juridisk søgning...")
            result = multihop_juridisk_søgning(test_query)
            print(f"\nOprindeligt spørgsmål: {result['question']}\n")
            print(f"Endeligt svar:\n{result['answer']}\n")
            print("Detaljer om delspørgsmål:")
            # Vi viser kun de første 100 tegn af hvert delresultat
            for i, sub_result in enumerate(result['intermediate_results']):
                print(f"Delresultat {i+1}: {sub_result[:100]}...\n")
            
        elif test_type == "hybrid":
            result = hybrid_søgning(test_query)
            print(f"Hybrid søgeresultat: {result[:300]}...")
    
    except Exception as e:
        print(f"Fejl under test: {e}")

def run_tests():
    """Kør alle tests for JAILA-systemet."""
    # Fortæl brugeren om kravene
    if not os.environ.get("OPENAI_API_KEY"):
        print("ADVARSEL: OPENAI_API_KEY er ikke sat i miljøvariablerne. Dette er påkrævet for at køre JAILA med OpenAI.")
        print("Du kan sætte den med:\n\n    export OPENAI_API_KEY=din-api-nøgle\n")
    
    # Kontroller Weaviate-forbindelse
    if not check_weaviate_connection():
        print("\nAdvarsel: Kan ikke forbinde til Weaviate-serveren. Sørg for at den kører på: " + weaviate_url)
        print("\nEksempel på brug i din app.py:")
        print("""    
        from JAILA import multihop_juridisk_søgning
        
        # Håndtering af brugerinput
        query = st.text_input("Stil et juridisk spørgsmål:")
        if st.button("Søg med multihop RAG"):
            with st.spinner("Analyserer spørgsmål og finder relevant information..."):
                result = multihop_juridisk_søgning(query)
                st.write(result["answer"])
        """)
        print("\nFor at køre fulde tests, sørg for at Weaviate-serveren kører på: " + weaviate_url)
        return False
    
    # Vælg testtype: 'normal', 'multihop' eller 'hybrid'
    test_type = "multihop"  # Ændres til 'normal' for at teste standard RAG
    
    # Eksempel på komplekst juridisk spørgsmål, der er godt til multihop RAG
    test_query = "Hvilke dokumentationskrav er der for at få fradrag for udgifter til erhvervsmæssig kørsel, og hvordan påvirker det beregningen af skatten?"
    
    # Kør den valgte test
    try:
        test_integration(test_type, test_query)
        print("\nJAILA integration test gennemført!")
        return True
    except Exception as e:
        print(f"\nFejl under test: {e}")
        return False

if __name__ == "__main__":
    run_tests()
    
    print("\nDu kan nu importere JAILA i din applikation for at bruge avancerede RAG-funktioner.")
    print("Eksempel på brug i din app.py:")
    print("""    
    from JAILA import multihop_juridisk_søgning
    
    # Håndtering af brugerinput
    query = st.text_input("Stil et juridisk spørgsmål:")
    if st.button("Søg med multihop RAG"):
        with st.spinner("Analyserer spørgsmål og finder relevant information..."):
            result = multihop_juridisk_søgning(query)
            st.write(result["answer"])
    """)
    
    print("\nFør du bruger denne integration, sørg for at Weaviate-serveren kører på: " + weaviate_url)
