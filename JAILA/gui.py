# JAILA/gui.py - Streamlit GUI til JAILA

import streamlit as st
import sys
import os
from pathlib import Path

# Tilføj rodmappen til Python-stien for at sikre, at vi kan importere JAILA
sys.path.append(str(Path(__file__).parent.parent))

from JAILA import multihop_juridisk_søgning, juridisk_søgning, check_weaviate_connection

st.set_page_config(
    page_title="JAILA - Juridisk AI Assistent",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Tjek Weaviate-forbindelse
    connection_status = check_weaviate_connection()
    
    if not connection_status:
        st.warning("⚠️ Kunne ikke forbinde til Weaviate-databasen. Kører i begrænset tilstand.")
        st.info("ℹ️ Du kan stadig stille spørgsmål, men svarene vil ikke være baseret på dokumentdatabasen.")
        st.sidebar.error("❌ Ingen forbindelse til Weaviate")
        
        # Vis hjælpesektion til fejlfinding
        with st.expander("Fejlfindings-hjælp"):
            st.markdown("""
            ### Mulige årsager til forbindelsesproblemer:
            
            1. **Weaviate-serveren kører ikke**
               - Start Docker og kør `docker-compose up -d` i docker-mappen
            
            2. **Netværksproblemer**
               - Kontroller din internetforbindelse
               - Tjek om der er problemer med DNS-opslag til api.openai.com
               - Prøv at åbne https://api.openai.com i en browser
            
            3. **Ugyldig API-nøgle**
               - Kontroller at OPENAI_API_KEY i .env-filen er korrekt
            
            4. **Firewall blokerer forbindelsen**
               - Sørg for at din firewall tillader forbindelser til api.openai.com
            """)
    else:
        st.sidebar.success("✅ Forbindelse til Weaviate-databasen er etableret.")
    
    # Sidebaren
    st.sidebar.title("JAILA")
    st.sidebar.subheader("Juridisk AI Assistent")
    
    søgetype = st.sidebar.radio(
        "Søgetype:",
        ["Standard søgning", "Multihop søgning"]
    )
    
    antal_resultater = st.sidebar.slider(
        "Antal resultater at hente:", 
        min_value=1, 
        max_value=10, 
        value=5
    )
    
    model = st.sidebar.selectbox(
        "Vælg model:",
        ["gpt-4o-2024-08-06", "gpt-4.1-mini-2025-04-14"]
    )
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Om JAILA")
    st.sidebar.markdown(
        """
        JAILA er et juridisk RAG-system, der kan besvare spørgsmål om dansk lovgivning
        ved hjælp af avanceret tekstgenkendelse og kunstig intelligens.
        """
    )
    
    # Hovedindhold
    st.title("⚖️ JAILA - Juridisk AI Assistent")
    
    st.markdown(
        """
        Velkommen til JAILA - din digitale juridiske assistent. 
        JAILA kan hjælpe dig med at finde svar på juridiske spørgsmål baseret på dansk lovgivning.
        
        **Sådan bruger du JAILA:**
        1. Vælg søgetype i sidebaren
        2. Indtast dit juridiske spørgsmål i feltet nedenfor
        3. Tryk på "Søg" for at få et svar
        """
    )
    
    # Input felt
    spørgsmål = st.text_area(
        "Indtast dit juridiske spørgsmål:",
        height=100,
        placeholder="F.eks.: Hvad er reglerne for kørselsfradrag? Eller: Hvilke krav stilles der til dokumentation for erhvervsmæssig kørsel?"
    )
    
    # Søgeknap
    if st.button("Søg", type="primary"):
        if not spørgsmål:
            st.error("Indtast venligst et spørgsmål.")
        else:
            # Vis spinner mens søgningen udføres
            with st.spinner("Søger efter svar..."):
                try:
                    if søgetype == "Standard søgning":
                        resultat = juridisk_søgning(spørgsmål, antal_resultater=antal_resultater, model=model)
                        vis_standard_resultat(resultat)
                    else:  # Multihop søgning
                        resultat = multihop_juridisk_søgning(spørgsmål, antal_resultater=antal_resultater, model=model)
                        vis_multihop_resultat(resultat)
                except Exception as e:
                    st.error(f"Der opstod en fejl: {str(e)}")

def vis_standard_resultat(resultat):
    """Viser resultatet af en standard søgning"""
    st.markdown("## Svar")
    st.markdown(resultat["answer"])
    
    # Vis kildedokumenter
    if "source_documents" in resultat and resultat["source_documents"]:
        with st.expander("Kildedokumenter"):
            for i, doc in enumerate(resultat["source_documents"]):
                st.markdown(f"### Dokument {i+1}")
                
                # Vis metadata hvis tilgængelig
                metadata = doc.metadata if hasattr(doc, "metadata") else {}
                if metadata:
                    st.markdown("**Metadata:**")
                    for key, value in metadata.items():
                        st.markdown(f"- **{key}:** {value}")
                
                # Vis selve dokumentet
                st.markdown("**Indhold:**")
                st.markdown(doc.page_content if hasattr(doc, "page_content") else str(doc))
                st.markdown("---")

def vis_multihop_resultat(resultat):
    """Viser resultatet af en multihop søgning med detaljeret indblik i processen"""
    # Vis originalt spørgsmål
    st.info(f"**Originalt spørgsmål:** {resultat['question']}")
    
    # Vis multihop-processen
    with st.expander("Se hvordan AI'en har nedbrudt dit spørgsmål", expanded=True):
        st.markdown("### Sådan analyserede AI'en dit spørgsmål")
        
        # Vis nedbrydningen af spørgsmålet
        st.markdown("AI'en nedbryder komplekse spørgsmål i mindre dele for at finde præcise svar i juridiske dokumenter.")
        
        # Vis delspørgsmål som en liste med nummerering
        if "sub_questions" in resultat:
            st.markdown("**Delspørgsmål genereret af AI:**")
            for i, q in enumerate(resultat["sub_questions"]):
                st.markdown(f"{i+1}. {q}")
        
        # Vis processen som et flowdiagram
        st.markdown("### Multihop RAG-processen")
        st.markdown("""
        ```mermaid
        graph TD
            A[Originalt spørgsmål] --> B[Nedbrydning i delspørgsmål]
            B --> C[Søgning efter relevante dokumenter]
            C --> D[Besvarelse af delspørgsmål]
            D --> E[Samlet syntese til endeligt svar]
        ```
        """)
    
    # Vis endeligt svar
    st.markdown("## Endeligt svar")
    st.markdown(resultat["answer"])
    
    # Vis detaljeret information om hvert delspørgsmål
    if "intermediate_results" in resultat and resultat["intermediate_results"]:
        with st.expander("Detaljeret indblik i AI'ens tankeproces"):
            st.markdown("### Sådan har AI'en besvaret hvert delspørgsmål")
            
            # Opret tabs for hvert delspørgsmål
            tabs = st.tabs([f"Delspørgsmål {i+1}" for i in range(len(resultat["intermediate_results"]))])
            
            for i, (tab, res) in enumerate(zip(tabs, resultat["intermediate_results"])):
                with tab:
                    st.markdown(f"**Spørgsmål:** {res['question']}")
                    st.markdown(f"**Svar:** {res['answer']}")
                    
                    # Vis kildedokumenter for hvert delspørgsmål
                    if "source_documents" in res and res["source_documents"]:
                        st.markdown("**Kildedokumenter brugt til dette svar:**")
                        for j, doc in enumerate(res["source_documents"]):
                            with st.expander(f"Dokument {j+1}"):
                                # Vis metadata hvis tilgængelig
                                metadata = doc.metadata if hasattr(doc, "metadata") else {}
                                if metadata:
                                    st.markdown("**Metadata:**")
                                    for key, value in metadata.items():
                                        st.markdown(f"- **{key}:** {value}")
                                
                                # Vis selve dokumentet
                                st.markdown("**Indhold:**")
                                st.markdown(doc.page_content if hasattr(doc, "page_content") else str(doc))

if __name__ == "__main__":
    main()
