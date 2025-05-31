"""
Entity-typer til kategorisering af juridiske begreber i lovtekst.
Dette modul indeholder definitioner på entitetstyper og deres relaterede søgeord,
som bruges til automatisk genkendelse og kategorisering.
"""

# Generelle juridiske entity-typer
ENTITY_TYPES = {
    # Generelle entity-typer
    "lovhenvisning": {
        "beskrivelse": "Henvisninger til paragraffer, bekendtgørelser og love",
        "nøgleord": [
            "§", "stk", "nr", "litra", "kapitel", "afsnit", 
            "lov nr", "lovbekendtgørelse", "LBK nr", 
            "direktiv", "forordning"
        ]
    },
    "retskilde": {
        "beskrivelse": "Kilder der danner grundlag for retsanvendelse",
        "nøgleord": [
            "lovforarbejder", "betænkning", "cirkulære", "vejledning", 
            "EU-ret", "bekendtgørelse", "lovgivning"
        ]
    },
    "domshenvisning": {
        "beskrivelse": "Referencer til domme og administrative afgørelser",
        "nøgleord": [
            "dom", "kendelse", "SKM", "TfS", "U.", "LSR", 
            "Højesterets dom", "Landsrettens dom", "afgørelse"
        ]
    },
    "myndighed": {
        "beskrivelse": "Offentlige institutioner og organer",
        "nøgleord": [
            "ministerium", "styrelse", "nævn", "råd", "tilsyn", "kommune",
            "forvaltning", "kommission", "direktorat", "departement"
        ]
    },
    "juridisk_person": {
        "beskrivelse": "Virksomheder, organisationer og andre juridiske enheder",
        "nøgleord": [
            "selskab", "fond", "forening", "organisation", "virksomhed", 
            "A/S", "ApS", "I/S", "koncern", "datterselskab", "moderselskab"
        ]
    },
    "fysisk_person": {
        "beskrivelse": "Roller og kategorier af fysiske personer",
        "nøgleord": [
            "borger", "part", "person", "ægtefælle", "arving", 
            "debitor", "kreditor", "ansatte", "arbejdsgiver", "arbejdstager"
        ]
    },
    "juridisk_begreb": {
        "beskrivelse": "Centrale juridiske begreber og principper",
        "nøgleord": [
            "pligt", "ret", "erstatning", "aftalefrihed", "god tro", 
            "passivitet", "hæftelse", "ansvar", "forpligtelse"
        ]
    },
    "tidsangivelse": {
        "beskrivelse": "Tidsperioder og frister",
        "nøgleord": [
            "frist", "periode", "ikrafttræden", "ophør", "termin", 
            "indkomstår", "kalenderår", "regnskabsår", "dato"
        ]
    },
    "økonomisk_begreb": {
        "beskrivelse": "Beløb, værdier og økonomiske begreber",
        "nøgleord": [
            "beløb", "grænse", "værdi", "rente", "afgift", "skat", "moms",
            "grundbeløb", "beløbsgrænse", "værdiansættelse", "kurs"
        ]
    },
    "område": {
        "beskrivelse": "Fagområder og retsområder",
        "nøgleord": [
            "skatteret", "selskabsret", "arveret", "obligationsret", "miljøret",
            "forvaltningsret", "familieret", "aftaleret", "strafferet"
        ]
    },
    "retsvirkning": {
        "beskrivelse": "Konsekvenser og virkninger",
        "nøgleord": [
            "sanktion", "bøde", "straf", "tilladelse", "forbud", "godkendelse",
            "konsekvens", "virkning", "hjemmel", "gyldighed"
        ]
    },
    "processuelt_begreb": {
        "beskrivelse": "Begreber relateret til retsprocesser og sagsbehandling",
        "nøgleord": [
            "klage", "anke", "sag", "bevis", "forlig", "påstand",
            "procedure", "sagsbehandling", "høring", "indsigelse"
        ]
    },
    
    # Skattespecifikke entity-typer
    "skattestatus": {
        "beskrivelse": "Begreber om subjekters skattemæssige status",
        "nøgleord": [
            "skattepligt", "fuld skattepligt", "begrænset skattepligt", 
            "skattefritagelse", "skattepligtig", "skattefri"
        ]
    },
    "indkomsttype": {
        "beskrivelse": "Kategorier af indkomst",
        "nøgleord": [
            "personlig indkomst", "kapitalindkomst", "aktieindkomst", 
            "erhvervsindkomst", "CFC-indkomst", "lønindkomst", "udbytte"
        ]
    },
    "fradragstype": {
        "beskrivelse": "Typer af fradrag og fradragsberettigede udgifter",
        "nøgleord": [
            "ligningsmæssige fradrag", "driftsomkostninger", "tab", 
            "afskrivninger", "fradragsberettiget", "fradragsret"
        ]
    },
    "skatteberegningselement": {
        "beskrivelse": "Elementer i skatteberegning",
        "nøgleord": [
            "skattegrundlag", "bundskat", "topskat", "sundhedsbidrag", 
            "personfradrag", "skattesats", "skatteloft", "skatteværdi"
        ]
    },
    "skattemyndighedsaktør": {
        "beskrivelse": "Specifikke skattemyndigheder",
        "nøgleord": [
            "Skattestyrelsen", "Skatteankestyrelsen", "Landsskatteretten", 
            "Skatterådet", "Vurderingsstyrelsen", "Gældsstyrelsen"
        ]
    },
    
    # Skatteforvaltningslov-specifikke entity-typer
    "forvaltningsmyndighed": {
        "beskrivelse": "Skattemyndigheder og deres organisatoriske enheder",
        "nøgleord": [
            "Skatteforvaltningen", "Skatteankestyrelsen", "Landsskatteretten",
            "Skatterådet", "Motorankenævn", "Vurderingsankenævn"
        ]
    },
    "kompetencefordeling": {
        "beskrivelse": "Begreber relateret til myndigheders kompetence",
        "nøgleord": [
            "saglig kompetence", "territorial kompetence", "delegation", 
            "bemyndigelse", "ressortområde", "kompetent myndighed"
        ]
    },
    "sagsbehandlingsskridt": {
        "beskrivelse": "Processer og procedurer i sagsbehandlingen",
        "nøgleord": [
            "partshøring", "vejledning", "afgørelse", "sagsoplysning", 
            "begrundelse", "journalisering", "underretning"
        ]
    },
    "klagemulighed": {
        "beskrivelse": "Klageinstanser og klageprocesser",
        "nøgleord": [
            "klage", "anke", "genoptagelse", "revision", "omgørelse",
            "påklage", "rekurs", "administrativ rekurs"
        ]
    },
    "fristrelateret": {
        "beskrivelse": "Tidsfrister og deres beregning",
        "nøgleord": [
            "klagefrist", "forældelsesfrist", "ansættelsesfrist", 
            "genoptagelsesfrist", "reaktionsfrist", "fristberegning"
        ]
    },
    "kontrolaktivitet": {
        "beskrivelse": "Myndigheders kontrolbeføjelser",
        "nøgleord": [
            "kontrol", "eftersyn", "indhentelse af oplysninger", "kontrolbesøg",
            "ransagning", "edition", "oplysningspligt", "undersøgelse"
        ]
    },
    "retssikkerhedselement": {
        "beskrivelse": "Retssikkerhedsgarantier for borgerne",
        "nøgleord": [
            "begrundelsespligt", "aktindsigt", "partsrepræsentation", 
            "officialprincip", "legalitetsprincip", "partshøring"
        ]
    },
    "sanktion": {
        "beskrivelse": "Konsekvenser ved overtrædelser",
        "nøgleord": [
            "bøde", "tillægsskat", "strafsanktion", "tvangsbøde",
            "straf", "skattetillæg", "administrative sanktioner"
        ]
    },
    "afgiftstype": {
        "beskrivelse": "Forskellige typer af afgifter",
        "nøgleord": [
            "registreringsafgift", "punktafgift", "miljøafgift", "energiafgift",
            "vægtafgift", "importafgift", "forbrugsafgift"
        ]
    },
    "digital_forvaltning": {
        "beskrivelse": "Elementer relateret til digital kommunikation",
        "nøgleord": [
            "digital post", "e-Boks", "sikker digital kommunikation", 
            "digital signatur", "TastSelv", "NemID", "MitID"
        ]
    },
    "international_skattesamarbejde": {
        "beskrivelse": "Elementer relateret til internationalt samarbejde",
        "nøgleord": [
            "udveksling af oplysninger", "dobbeltbeskatningsoverenskomst", 
            "bistandsaftale", "international sambeskatning", "transferpricing"
        ]
    },
    "skattesubjekt": {
        "beskrivelse": "Personer og enheder omfattet af lovgivningen",
        "nøgleord": [
            "skattepligtig", "afgiftspligtig", "tredjemand", "indberetningspligtig",
            "skatteyder", "skattesubjekt", "selvanmelder"
        ]
    }
}

def find_entity_type(text):
    """
    Finder den mest sandsynlige entity-type for en given tekst.
    
    Args:
        text: Tekst der skal kategoriseres
        
    Returns:
        Entity-type som string, eller "ukendt" hvis ingen match
    """
    if not text or not isinstance(text, str):
        return "ukendt"
    
    text_lower = text.lower()
    
    # Tjek for lovhenvisninger med regex-lignende mønster først
    if text.startswith('§') or ('§' in text and any(c.isdigit() for c in text)):
        return "lovhenvisning"
    
    # Tjek for domshenvisninger
    for prefix in ["SKM", "TfS", "U.", "LSR"]:
        if prefix in text and any(c.isdigit() for c in text):
            return "domshenvisning"
    
    # Gennemgå alle entity-typer og deres nøgleord
    best_match = None
    max_matches = 0
    
    for entity_type, info in ENTITY_TYPES.items():
        matches = 0
        for keyword in info["nøgleord"]:
            if keyword.lower() in text_lower:
                matches += 1
                
        if matches > max_matches:
            max_matches = matches
            best_match = entity_type
    
    return best_match if best_match and max_matches > 0 else "ukendt"
