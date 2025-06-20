# 🔗 Ligningsloven Relations Network

```mermaid
graph TD
    subgraph "Ligningsloven Knowledge Graph Relations - Manual Expert Analysis"
        
        %% Bundfradrag System (Critical relations group)
        subgraph "Bundfradrag System"
            15O["§15O<br/>Fritidsbolig bundfradrag"]
            15P["§15P<br/>Helårsbolig bundfradrag"]
            15Q["§15Q<br/>Helårsbolig specialregel"]
            15R["§15R<br/>Aktiver bundfradrag"]
            
            15O -.- 15P
            15O -.- 15Q
            15P -.- 15Q
            15Q -.- 15R
            15P -.- 15R
        end
        
        %% Personalegoder System
        subgraph "Personalegoder/Gaver"
            7["§7<br/>Skattefrihed"]
            7A["§7A<br/>Undtagelser"]
            16["§16<br/>Personalegoder"]
            16A["§16A<br/>Aktieudbytte"]
            
            7 -.- 7A
            16 -.- 16A
            16 -.- 7
        end
        
        %% Renter og Fradrag
        subgraph "Renter og Fradrag"
            5["§5<br/>Rentefradrag"]
            5A["§5A<br/>Nedskrivning"]
            5B["§5B<br/>Skattepligtsændringer"]
            5C["§5C<br/>Overdragelse"]
            
            5 --> 5A
            5 --> 5B
            5 --> 5C
        end
        
        %% Forskningsfradrag
        subgraph "Forskningsfradrag"
            8B["§8B<br/>Erhvervsmæssig"]
            8H["§8H<br/>Gavefradrag"]
            
            8B -.- 8H
        end
        
        %% Dobbeltbeskatning
        subgraph "Dobbeltbeskatning"
            33["§33<br/>Hovedregel"]
            33A["§33A<br/>Specialbestemmelser"]
            
            33 -.- 33A
        end
        
        %% Hierarkiske relationer
        subgraph "Hierarkiske Relationer"
            16_main["§16<br/>Hovedparagraf"]
            16_stk1["§16, stk. 1"]
            15O_main["§15O<br/>Hovedparagraf"]
            15O_stk2["§15O, stk. 2"]
            
            16_main --> 16_stk1
            15O_main --> 15O_stk2
        end
        
    end
    
    %% Summary Statistics
    STATS["📊 Expert Graph<br/>22 relations<br/>vs 7 GPT-4o"]
```

**Relation Quality:** Expert manual analysis vs automated extraction  
**Result:** 22 high-quality relations vs 7 questionable GPT-4o relations
