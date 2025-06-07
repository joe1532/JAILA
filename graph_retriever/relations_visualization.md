# 🔗 Ligningsloven Knowledge Graph Relations

**Dato:** 7. december 2024  
**Formål:** Visualisering af alle 22 expert-identificerede relationer

## 📊 Relations Network Diagram

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
        
        %% Erhvervsfradrag
        subgraph "Erhvervsfradrag"
            8["§8<br/>Erhvervsfradrag"]
            8A["§8A<br/>Almennyttige gaver"]
            
            8 -.- 8A
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
            15P_main["§15P<br/>Hovedparagraf"]
            15P_stk2["§15P, stk. 2"]
            15P_stk3["§15P, stk. 3"]
            
            16_main --> 16_stk1
            15O_main --> 15O_stk2
            15P_main --> 15P_stk2
            15P_main --> 15P_stk3
        end
        
        %% Alternative relationer
        subgraph "Alternative Regler"
            15O_alt1["§15O, stk. 1<br/>Bundfradrag"]
            15O_alt2["§15O, stk. 2<br/>Faktiske udgifter"]
            15P_alt1["§15P, stk. 1<br/>Bundfradrag"]
            15P_alt3["§15P, stk. 3<br/>Faktiske udgifter"]
            
            15O_alt1 <--> 15O_alt2
            15P_alt1 <--> 15P_alt3
        end
        
        %% Explicit references
        16A_stk5["§16A, stk. 5"] -.->|"henviser til"| 16
        7P["§7P<br/>Medarbejderaktier"] -.->|"henviser til"| 28["§28<br/>Personaleoptions"]
        
    end
    
    %% Summary Statistics Box
    STATS["📊 Graph Statistics<br/>---<br/>📄 Entities: 210<br/>🔗 Relations: 22<br/>💪 Avg Strength: 0.85<br/>🎯 Avg Confidence: 0.93<br/>---<br/>🏆 Expert Manual Analysis<br/>vs 7 GPT-4o relations"]
```

## 📋 Relation Type Breakdown

### **Conceptual Relations** (12)
- Bundfradrag System: §15O ↔ §15P ↔ §15Q ↔ §15R
- Personalegoder: §7 ↔ §7A, §16 ↔ §16A, §16 ↔ §7
- Forskningsfradrag: §8B ↔ §8H
- Erhvervsfradrag: §8 ↔ §8A
- Dobbeltbeskatning: §33 ↔ §33A

### **Hierarchical Relations** (4)
- §16 → §16, stk. 1
- §15O → §15O, stk. 2
- §15P → §15P, stk. 2
- §15P → §15P, stk. 3

### **Procedural Relations** (3)
- §5 → §5A (Rentefradrag til nedskrivning)
- §5 → §5B (Rentefradrag til skattepligtsændringer)
- §5 → §5C (Rentefradrag til overdragelse)

### **Explicit References** (2)
- §16A, stk. 5 henviser til §16
- §7P henviser til §28

### **Alternative Relations** (2)
- §15O: bundfradrag ↔ faktiske udgifter
- §15P: bundfradrag ↔ faktiske udgifter

## 🏆 Quality Metrics

- **Average Strength**: 0.85
- **Average Confidence**: 0.93
- **Total Relations**: 22 (vs 7 from GPT-4o)
- **Total Entities**: 210

## ⚠️ Critical Missing Relations (in GPT-4o)

1. **Bundfradrag System** - Entire interconnected system
2. **§16 ↔ §7** - Taxable vs tax-free benefits
3. **§5 series** - Interest deduction system
4. **§8B ↔ §8H** - Research deduction types

---

*Generated: December 7, 2024* 