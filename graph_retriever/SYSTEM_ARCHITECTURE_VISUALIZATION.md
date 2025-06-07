# 🏗️ Graph Retriever System Architecture

**Dato:** 7. december 2024  
**Formål:** Visualisering af Graph Retriever økosystemets arkitektur

## 🎯 System Oversigt

```mermaid
graph TB
    subgraph "Graph Retriever System Architecture"
        
        %% Core Components
        GRS["GraphRetrieverStrategy<br/>(graph_retriever_strategy.py)<br/>933 lines"]
        GR["GraphRetriever<br/>(graph_retriever.py)<br/>197 lines"]
        
        %% Data Sources
        JSON["Manual Expert Graph<br/>(ligningsloven_manual_expert_graph.json)<br/>1451 lines<br/>22 relations, 210 entities"]
        
        %% Core Classes
        TLG["TaxLawGraph<br/>Knowledge graph structure"]
        GN["GraphNode<br/>Paragraph representation"]
        GRel["GraphRelation<br/>Relation representation"]
        BS["BatchingStrategy<br/>Optimal context batching"]
        
        %% Integration Points
        JAILA["JAILA RAG System<br/>(juridisk_rag_langchain.py)"]
        SE["SearchEngine<br/>(search_engine.py)"]
        
        %% Relation Types
        ER["Explicit References<br/>'jf. §X', 'se §X'"]
        HR["Hierarchical Relations<br/>Chapter/Section structure"]
        CR["Conceptual Relations<br/>Same legal concepts"]
        PR["Procedural Relations<br/>Sequential steps"]
        
        %% Connections
        GRS --> TLG
        GRS --> BS
        GR --> TLG
        TLG --> GN
        TLG --> GRel
        JSON --> TLG
        
        %% Relation types feed into GraphRelation
        ER --> GRel
        HR --> GRel
        CR --> GRel
        PR --> GRel
        
        %% Integration
        JAILA --> GR
        GR --> SE
        
        %% LLM Processing
        GPT4o["GPT-4o<br/>Relation Extraction"]
        BS --> GPT4o
        GPT4o --> GRel
        
    end
    
    %% Styling
    classDef coreFile fill:#e1f5fe,stroke:#01579b,stroke-width:3px
    classDef dataFile fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef classBox fill:#e8f5e8,stroke:#1b5e20,stroke-width:2px
    classDef integration fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef relation fill:#fce4ec,stroke:#880e4f,stroke-width:2px
    classDef llm fill:#f1f8e9,stroke:#33691e,stroke-width:2px
    
    class GRS,GR coreFile
    class JSON dataFile
    class TLG,GN,GRel,BS classBox
    class JAILA,SE integration
    class ER,HR,CR,PR relation
    class GPT4o llm
```

## 📋 Komponent Beskrivelser

### **Core Files**
- **GraphRetrieverStrategy** (933 linjer) - Hovedstrategi for graph building
- **GraphRetriever** (197 linjer) - Integration interface til JAILA

### **Data Strukturer**
- **TaxLawGraph** - Knowledge graph container
- **GraphNode** - Paragraf representation
- **GraphRelation** - Relation representation
- **BatchingStrategy** - Optimal context batching

### **Integration Points**
- **JAILA RAG System** - Hovedsystem integration
- **SearchEngine** - Semantic search integration

### **Relation Types**
1. **Explicit References** - Direkte henvisninger ("jf. §X")
2. **Hierarchical Relations** - Struktur relationer
3. **Conceptual Relations** - Begrebsmæssige forbindelser
4. **Procedural Relations** - Sekventielle processer

### **LLM Processing**
- **GPT-4o** bruges til relation extraction fra batched content
- **BatchingStrategy** optimerer context for bedre forståelse

---

*Genereret: December 7, 2024* 