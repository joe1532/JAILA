# 🧠 MULTIHOP REASONING EKSEMPLER - Forskellige Spørgsmålstyper

**Hvordan fungerer multihop reasoning for forskellige juridiske spørgsmål?**

---

## 🎯 **TYPE 1: KONCEPTUELLE SPØRGSMÅL**

### **Spørgsmål:** *"Hvad betyder begrænset skattepligt i dansk ret?"*

```
🔍 HOP 1: Søger "begrænset skattepligt"
   → Finder grundlæggende definition i KSL § 2

🧠 ANALYSE: Har grunddefinition, men mangler:
   - Konkrete kriterier
   - Praktiske eksempler  
   - Sammenhæng med andre skatteformer

🔍 HOP 2: Søger "begrænset skattepligt kriterier indkomst"
   → Finder specifikke regler om hvilken indkomst

🔍 HOP 3: Søger "begrænset skattepligt vs fuld skattepligt"
   → Finder forskelle og sammenhænge

🤖 SYNTESE: Komplet forklaring af begrebet
   → Definition + kriterier + praktiske eksempler
```

**Hvorfor multihop?** Koncepter kræver ofte flere lag af forståelse - definition → kriterier → sammenhæng → eksempler.

---

## 🎯 **TYPE 2: KOMPLEKSE JURIDISKE SAMMENHÆNGE**

### **Spørgsmål:** *"Hvordan påvirker aktieavancebeskatningsloven andre skattelove?"*

```
🔍 HOP 1: Søger "aktieavancebeskatningsloven"
   → Finder ABL's grundprincipper

🧠 ANALYSE: Har ABL info, men mangler:
   - Hvordan ABL interagerer med KSL
   - Påvirkning på personskatteregler
   - Specifikke cross-references

🔍 HOP 2: Søger "aktieavancebeskatningsloven kildeskatteloven"
   → Finder sammenhænge mellem ABL og KSL

🔍 HOP 3: Søger "aktieindkomst skattepligt ligningsloven"
   → Finder yderligere sammenhænge med LL

🤖 SYNTESE: Komplet oversigt over ABL's påvirkning
   → ABL principper + KSL sammenhænge + LL påvirkning
```

**Hvorfor multihop?** Komplekse juridiske sammenhænge kræver opbygning af forståelse på tværs af flere lovgivninger.

---

## 🎯 **TYPE 3: PRAKTISK ANVENDELSE**

### **Spørgsmål:** *"Hvornår skal en udlænding betale skat i Danmark?"*

```
🔍 HOP 1: Søger "udlænding skat Danmark skattepligt"
   → Finder generelle regler om skattepligt

🧠 ANALYSE: Har generelle regler, men mangler:
   - Specifikke tidsfrister
   - Forskellige scenarier (bosiddende vs ikke-bosiddende)
   - Praktiske procedurer

🔍 HOP 2: Søger "skattepligt udlænding 183 dage regel"
   → Finder specifikke tidsregler

🔍 HOP 3: Søger "skatteregistrering udlænding procedure"
   → Finder praktiske procedurer og frister

🤖 SYNTESE: Komplet praktisk guide
   → Generelle regler + specifikke kriterier + procedurer
```

**Hvorfor multihop?** Praktiske spørgsmål kræver både juridisk baggrund og konkrete handlingsvejledninger.

---

## 🎯 **TYPE 4: LOVGIVNING PÅ TVÆRS**

### **Spørgsmål:** *"Sammenhængen mellem kildeskat og selskabsbeskatning"*

```
🔍 HOP 1: Søger "kildeskat selskaber"
   → Finder KSL regler for selskaber

🧠 ANALYSE: Har KSL info, men mangler:
   - Selskabsskattelovens perspektiv
   - Hvordan de to systemer interagerer
   - Potentielle konflikter eller overlap

🔍 HOP 2: Søger "selskabsskatteloven kildeskat"
   → Finder SSL's perspektiv på kildeskat

🔍 HOP 3: Søger "dobbeltbeskatning selskab kildeskat"
   → Finder information om overlap og undgåelse af dobbeltbeskatning

🤖 SYNTESE: Komplet analyse af sammenhængen
   → KSL regler + SSL regler + interaction logic
```

**Hvorfor multihop?** Cross-law spørgsmål kræver forståelse af hver lov separat og dernæst deres interaktion.

---

## 🎯 **TYPE 5: HISTORISK/UDVIKLING**

### **Spørgsmål:** *"Hvordan har reglerne om aktiebeskatning udviklet sig?"*

```
🔍 HOP 1: Søger "aktiebeskatning historik udvikling"
   → Finder overordnet historisk overblik

🧠 ANALYSE: Har historisk oversigt, men mangler:
   - Specifikke lovændringer og årstal
   - Baggrund for ændringerne
   - Sammenligning af gammel vs ny praksis

🔍 HOP 2: Søger "aktieavancebeskatningsloven ændringer 1997 2006"
   → Finder specifikke lovændringer

🔍 HOP 3: Søger "aktiebeskatning før efter ændringer praktisk betydning"
   → Finder praktiske konsekvenser af ændringerne

🤖 SYNTESE: Komplet historisk analyse
   → Historisk oversigt + specifikke ændringer + praktiske konsekvenser
```

**Hvorfor multihop?** Historiske spørgsmål kræver både kronologisk overblik og detaljeret forståelse af specifikke ændringer.

---

## 🎯 **TYPE 6: UNDTAGELSER OG SPECIALTILFÆLDE**

### **Spørgsmål:** *"Hvornår gælder der undtagelser til normal skattepligt?"*

```
🔍 HOP 1: Søger "undtagelser skattepligt Danmark"
   → Finder generelle undtagelsesregler

🧠 ANALYSE: Har generelle undtagelser, men mangler:
   - Specifikke undtagelseskategorier
   - Betingelser for hver undtagelse
   - Procedurer for at anvende undtagelser

🔍 HOP 2: Søger "diplomatisk immunitet skattepligt EU regler"
   → Finder specifikke undtagelseskategorier

🔍 HOP 3: Søger "ansøgning skattefritagelse procedure dokumentation"
   → Finder praktiske procedurer for undtagelser

🤖 SYNTESE: Komplet undtagelsesguide
   → Generelle principper + specifikke kategorier + procedurer
```

**Hvorfor multihop?** Undtagelsesregler er ofte komplekse og kræver forståelse af både hovedreglen og de specifikke undtagelsesbetingelser.

---

## 🧠 **MULTIHOP DECISION LOGIC**

### **Hvordan beslutter systemet hvornår der skal laves flere hops?**

```python
# I document_analysis_template
{
    "key_findings": ["Det vi fandt"],
    "missing_info": ["Det vi mangler"],        # ← Trigger for næste hop
    "references": ["Andre paragraffer nævnt"],  # ← Potentiel nye søgninger
    "needs_more_search": true/false,           # ← Hovedbeslutning
    "next_queries": ["Næste søgning"]          # ← Hvad der skal søges
}
```

### **Kriterier for "needs_more_search":**

1. **Incomplete Information:** Spørgsmålet kun delvist besvaret
2. **Cross-references Found:** Dokumenter henviser til andre love/paragraffer
3. **Complex Concepts:** Juridiske begreber der kræver uddybning
4. **Missing Context:** Mangler baggrund for at forstå sammenhænge
5. **Practical Gaps:** Mangler praktisk anvendelse af juridiske regler

---

## 🎯 **SAMMENLIGNING: SINGLE HOP VS MULTIHOP**

### **Eksempel: "Hvad er skattepligt?"**

**🔥 SINGLE HOP (traditionel RAG):**
```
🔍 Søg: "skattepligt"
📄 Find: En definition af skattepligt
💬 Svar: "Skattepligt betyder at man skal betale skat..."
```
**Resultat:** Overfladisk svar, mangler nuancer og sammenhæng.

**🧠 MULTIHOP RAG:**
```
🔍 HOP 1: Søg "skattepligt definition"
   → Find grundlæggende definition

🧠 ANALYSE: Mangler typer af skattepligt og kriterier

🔍 HOP 2: Søg "fuld begrænset skattepligt forskel"
   → Find forskellige typer skattepligt

🧠 ANALYSE: Mangler praktiske eksempler

🔍 HOP 3: Søg "skattepligt eksempler udlænding bosiddende"
   → Find konkrete eksempler

🤖 SYNTESE: Komplet svar med definition, typer, kriterier og eksempler
```
**Resultat:** Dybdegående, nuanceret svar med praktisk anvendelse.

---

## 📊 **MULTIHOP PATTERNS FOR FORSKELLIGE SPØRGSMÅLSTYPER**

| Spørgsmålstype | Typisk Hop Pattern | Eksempel Progression |
|----------------|-------------------|---------------------|
| **Konceptuel** | Definition → Kriterier → Eksempler | "Hvad er X?" → "Hvordan defineres X?" → "Eksempler på X?" |
| **Sammenligning** | A → B → Forskel | "§ 2" → "§ 7" → "Forskelle" |
| **Praktisk** | Regel → Procedure → Frister | "Regel" → "Hvordan" → "Hvornår" |
| **Cross-law** | Lov A → Lov B → Interaktion | "KSL" → "SSL" → "Sammenhæng" |
| **Historisk** | Oversigt → Detaljer → Konsekvenser | "Udvikling" → "Ændringer" → "Påvirkning" |
| **Undtagelser** | Hovedregel → Undtagelser → Betingelser | "Normal regel" → "Undtagelser" → "Kriterier" |

---

## 🚀 **KONKLUSION**

**Multihop reasoning er ikke bare til paragraf-sammenligning!** 

Det fungerer for **alle komplekse juridiske spørgsmål** hvor:

- 🧠 **Et enkelt hop ikke giver komplet svar**
- 🔗 **Sammenhænge mellem dokumenter er vigtige**
- 📊 **Kontekst og baggrund er nødvendig**
- 🎯 **Praktisk anvendelse kræver flere informationskilder**
- 🌐 **Cross-references mellem love skal følges**

**🎯 Multihop reasoning gør dit juridiske AI system intelligentere ved at tænke som en rigtig jurist - step by step, med sammenhæng og kontekst!** 