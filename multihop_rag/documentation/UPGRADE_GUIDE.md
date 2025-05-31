# JAILA Database Upgrade Guide

## 🎯 Formål
Denne guide hjælper dig med at opdatere din JAILA-database med de nye forbedringer til paragraf-søgning.

## ⚠️ Vigtig Information
- **Backup anbefales**: Dine eksisterende data bliver slettet
- **Re-import påkrævet**: Alle data skal importeres igen med ny struktur
- **Test først**: Kør test efter upgrade for at sikre alt virker

## 📋 Upgrade Steps

### Trin 1: Forbered Upgrade
```bash
# Sørg for at Weaviate kører
docker-compose up -d

# Verificer forbindelse
python -c "from JAILA import check_weaviate_connection; print('OK' if check_weaviate_connection() else 'FEJL')"
```

### Trin 2: Rens Database (Vælg én metode)

#### Option A: Hurtig Cleanup (Anbefalet)
```bash
python quick_cleanup.py
```

#### Option B: Detaljeret Cleanup (Med backup og valgmuligheder)
```bash
python cleanup_database.py
```

### Trin 3: Re-importer Data
```bash
# Kør det opdaterede import script
python import_simple.py
```

### Trin 4: Test den Nye Funktionalitet
```bash
# Kør omfattende tests
python test_paragraph_search.py
```

### Trin 5: Verificer GUI
```bash
# Start JAILA GUI og test paragraf-spørgsmål
python start_gui.py
```

## 🔍 Test Eksempler

Efter upgrade, test disse spørgsmål i GUI'en:

### Paragraf-Spørgsmål:
- "§ 4 statsskatteloven"
- "Hvad siger § 5 i ligningsloven?"
- "ligningslovens § 9 c om kørselsfradrag"

### Almindelige Spørgsmål:
- "Hvad er reglerne for kørselsfradrag?"
- "Hvilke betingelser skal være opfyldt for skattefradrag?"

## 📊 Forventede Forbedringer

### Før Upgrade:
- ❌ Paragraf-spørgsmål gav ofte irrelevante resultater
- ❌ Søgte kun i begrænsede felter
- ❌ Ingen automatisk noter til paragraffer

### Efter Upgrade:
- ✅ Præcis paragraf-identifikation
- ✅ Automatisk hentning af relaterede noter
- ✅ Søgning i alle relevante felter
- ✅ Intelligent fallback-mekanismer

## 🚨 Fejlfinding

### Problem: "Kunne ikke forbinde til Weaviate"
```bash
# Tjek om Weaviate kører
docker ps | grep weaviate

# Start Weaviate hvis nødvendigt
docker-compose up -d
```

### Problem: "Import fejler"
```bash
# Tjek JSONL-filer eksisterer
ls -la "import embedding/"

# Verificer .env filen
cat .env | grep OPENAI_API_KEY
```

### Problem: "Test fejler"
```bash
# Tjek om data er importeret
python -c "
import weaviate
client = weaviate.Client('http://localhost:8080')
result = client.query.aggregate('LegalDocument').with_meta_count().do()
print(f'Objekter: {result[\"data\"][\"Aggregate\"][\"LegalDocument\"][0][\"meta\"][\"count\"]}')
"
```

## 📁 Filer Involveret i Upgrade

### Opdaterede Filer:
- ✅ `import_simple.py` - Tilpasset til faktisk datastruktur
- ✅ `JAILA/hybrid_search.py` - Ny paragraf-specifik søgning
- ✅ `JAILA/config.py` - Udvidede metadata-felter

### Nye Filer:
- 🆕 `cleanup_database.py` - Detaljeret database cleanup
- 🆕 `quick_cleanup.py` - Hurtig cleanup
- 🆕 `test_paragraph_search.py` - Omfattende test suite
- 🆕 `DATASTRUKTUR_FIX_README.md` - Teknisk dokumentation

## 🎉 Success Kriterier

Din upgrade er succesful når:
- ✅ `test_paragraph_search.py` kører uden fejl
- ✅ Paragraf-spørgsmål i GUI giver præcise resultater
- ✅ Relaterede noter vises automatisk
- ✅ Standard søgning fungerer som før

## 📞 Support

Hvis du støder på problemer:
1. Tjek denne guide igen
2. Kør `python test_paragraph_search.py` for diagnostik
3. Se `DATASTRUKTUR_FIX_README.md` for tekniske detaljer

---

**Bemærk**: Denne upgrade forbedrer specifikt paragraf-søgning og bevarar al eksisterende funktionalitet. Dine juridiske dokumenter får bare bedre og mere præcis søgning! 🎯 