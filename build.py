from pathlib import Path
import re, unicodedata, json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from jinja2 import Environment, FileSystemLoader, select_autoescape

from urllib.parse import urlparse
import os

IN_FILE = "staaten-bpb.xml"
OUT_DIR = Path("dist")
# BASE_URL wird dynamisch gesetzt (für GitHub Pages z.B. https://username.github.io/repo)
BASE_URL = os.getenv("BASE_URL", "http://localhost:8080").rstrip("/")
# SITE_ROOT extrahiert den Pfad-Teil (z. B. /almanach_v1), falls vorhanden
_parsed_url = urlparse(BASE_URL)
SITE_ROOT = _parsed_url.path.rstrip("/")
SITE_NAME = "Der neue Kosmos Welt-Almanach & Atlas 2026"

# ISO 3316-1 alpha-3 to alpha-2 mapping for FlagCDN
ISO3_TO_ISO2 = {
    "AFG": "af", "ALB": "al", "DZA": "dz", "AND": "ad", "AGO": "ao", "ATG": "ag", "ARG": "ar", "ARM": "am", "AUS": "au", "AUT": "at",
    "AZE": "az", "BHS": "bs", "BHR": "bh", "BGD": "bd", "BRB": "bb", "BLR": "by", "BEL": "be", "BLZ": "bz", "BEN": "bj", "BTN": "bt",
    "BOL": "bo", "BIH": "ba", "BWA": "bw", "BRA": "br", "BRN": "bn", "BGR": "bg", "BFA": "bf", "BDI": "bi", "CPV": "cv", "KHM": "kh",
    "CMR": "cm", "CAN": "ca", "CAF": "cf", "TCD": "td", "CHL": "cl", "CHN": "cn", "COL": "co", "COM": "km", "COG": "cg", "COD": "cd",
    "CRI": "cr", "CIV": "ci", "HRV": "hr", "CUB": "cu", "CYP": "cy", "CZE": "cz", "DNK": "dk", "DJI": "dj", "DMA": "dm", "DOM": "do",
    "ECU": "ec", "EGY": "eg", "SLV": "sv", "GNQ": "gq", "ERI": "er", "EST": "ee", "SWZ": "sz", "ETH": "et", "FJI": "fj", "FIN": "fi",
    "FRA": "fr", "GAB": "ga", "GMB": "gm", "GEO": "ge", "DEU": "de", "GHA": "gh", "GRC": "gr", "GRD": "gd", "GTM": "gt", "GIN": "gn",
    "GNB": "gw", "GUY": "gy", "HTI": "ht", "HND": "hn", "HUN": "hu", "ISL": "is", "IND": "in", "IDN": "id", "IRN": "ir", "IRQ": "iq",
    "IRL": "ie", "ISR": "il", "ITA": "it", "JAM": "jm", "JPN": "jp", "JOR": "jo", "KAZ": "kz", "KEN": "ke", "KIR": "ki", "PRK": "kp",
    "KOR": "kr", "KWT": "kw", "KGZ": "kg", "LAO": "la", "LVA": "lv", "LBN": "lb", "LSO": "ls", "LBR": "lr", "LBY": "ly", "LIE": "li",
    "LTU": "lt", "LUX": "lu", "MDG": "mg", "MWI": "mw", "MYS": "my", "MDV": "mv", "MLI": "ml", "MLT": "mt", "MHL": "mh", "MRT": "mr",
    "MUS": "mu", "MEX": "mx", "FSM": "fm", "MDA": "md", "MCO": "mc", "MNG": "mn", "MNE": "me", "MAR": "ma", "MOZ": "mz", "MMR": "mm",
    "NAM": "na", "NRU": "nr", "NPL": "np", "NLD": "nl", "NZL": "nz", "NIC": "ni", "NER": "ne", "NGA": "ng", "MKD": "mk", "NOR": "no",
    "OMN": "om", "PAK": "pk", "PLW": "pw", "PAN": "pa", "PNG": "pg", "PRY": "py", "PER": "pe", "PHL": "ph", "POL": "pl", "PRT": "pt",
    "QAT": "qa", "ROU": "ro", "RUS": "ru", "RWA": "rw", "KNA": "kn", "LCA": "lc", "VCT": "vc", "WSM": "ws", "SMR": "sm", "STP": "st",
    "SAU": "sa", "SEN": "sn", "SRB": "rs", "SYC": "sc", "SLE": "sl", "SGP": "sg", "SVK": "sk", "SVN": "si", "SLB": "sb", "SOM": "so",
    "ZAF": "za", "SSD": "ss", "ESP": "es", "LKA": "lk", "SDN": "sd", "SUR": "sr", "SWE": "se", "CHE": "ch", "SYR": "sy", "TWN": "tw",
    "TJK": "tj", "TZA": "tz", "THA": "th", "TLS": "tl", "TGO": "tg", "TON": "to", "TTO": "tt", "TUN": "tn", "TUR": "tr", "TKM": "tm",
    "TUV": "tv", "UGA": "ug", "UKR": "ua", "ARE": "ae", "GBR": "gb", "USA": "us", "URY": "uy", "UZB": "uz", "VUT": "vu", "VAT": "va",
    "VEN": "ve", "VNM": "vn", "YEM": "ye", "ZMB": "zm", "ZWE": "zw"
}

# Mapping von XML-Tag zu lesbarem Label (alle bekannten Felder)
FIELD_LABELS = {
    "id": None,  # Nicht anzeigen
    "hname": None,  # Wird als H1 verwendet
    "sname": "Staatenname",
    "tzone": "Zeitzone",
    "flaeche": "Fläche in km²",
    "einwzahl": "Anzahl der Einwohner",
    "einwdicht": "Einwohner pro km²",
    "hauptstadt": "Hauptstadt",
    "amtssprache": "Amtssprache",
    "gliederung": "Verwaltungsgliederung",
    "staedte": "Wichtige Städte",
    "autokennz": "Autokennzeichen | ISO-Code",
    "waehrung": "Währung",
    "natfeier": "Nationalfeiertag",
    "geolage": "Geografische Lage",
    "hoechpunkt": "Höchster Punkt",
    "klima": "Klima",
    "staatsform": "Staatsform",
    "oberhaupt": "Staatsoberhaupt",
    "regchef": "Regierungschef",
    "aussen": "Außenminister",
    "botschaft": "Botschaft",
    "parteireg": "Regierungskoalition",
    "legislative": "Legislative",
    "verfassung": "Jahr der Verfassung",
    "wahlrecht": "Wahlrecht",
    "bevanteil": "Alter",
    "bevverteil": "Verteilung",
    "bevwachst": "Wachstum",
    "altmedian": "Altersmedian",
    "lebenserw": "Lebenserwartung",
    "alpharate": "Alphabetenrate",
    "ethgruppen": "Gruppen",
    "religion": "Religionen",
    "sprache": "Sprachen",
    "gesamtbip": "BIP",
    "wachstbip": "BIP-Wachstum",
    "einwbne": "BIP/Kopf",
    "inflation": "Inflation",
    "ausshandel": "Außenhandel",
    "sektorbip": "Anteil BIP nach Sektoren",
    "arblos": "Arbeitslosenquote",
    "energverbr": "CO₂-Emission/Kopf",
    "erneuerbar": "Stromerzeugung aus Erneuerbarer Energie",
    # Gebiet-Felder (für Außengebiete)
    "gid": None,  # Nicht anzeigen
    "ghname": "Name",
    "gflaeche": "Fläche in km²",
    "geinwzahl": "Anzahl der Einwohner",
    "ghauptstadt": "Hauptstadt",
    "gstatus": "Status",
    "gregierung": "Regierungschef",
}

# Gliederung für Sektionen (Gruppierung der Felder)
SECTION_ORDER = [
    ("Basisdaten", ["sname", "tzone", "flaeche", "einwzahl", "einwdicht", "hauptstadt", "amtssprache", "gliederung", "staedte", "autokennz", "waehrung", "natfeier"]),
    ("Geografie", ["geolage", "hoechpunkt", "klima"]),
    ("Politik", ["staatsform", "oberhaupt", "regchef", "aussen", "botschaft", "parteireg", "legislative", "verfassung", "wahlrecht"]),
    ("Bevölkerung", ["bevanteil", "bevverteil", "bevwachst", "altmedian", "lebenserw", "alpharate", "ethgruppen", "religion", "sprache"]),
    ("Wirtschaft", ["gesamtbip", "wachstbip", "einwbne", "inflation", "ausshandel", "sektorbip", "arblos", "energverbr", "erneuerbar"]),
]


def parse_element(elem):
    """
    Rekursive Funktion, um ein XML-Element in ein Python-Objekt (Dict, List, Str) umzuwandeln.
    """
    # Wenn das Element Kinder hat
    if len(elem) > 0:
        out = {}
        for child in elem:
            val = parse_element(child)
            tag = child.tag
            
            if tag in out:
                # Mehrfache Tags gleichen Namens -> Liste
                if not isinstance(out[tag], list):
                    out[tag] = [out[tag]]
                out[tag].append(val)
            else:
                out[tag] = val
        return out
    else:
        # Blatt-Knoten: Text zurückgeben
        return (elem.text or "").strip()

def recursive_render(key, val, level=0):
    """
    Erzeugt eine flache Liste von (Label, Value)-Tupeln aus verschachtelten Strukturen.
    Visualisiert die Hierarchie (Einrückung etc.).
    Spezialbehandlung für gueber1 und gueber2 als Überschriften.
    """
    items = []
    
    # Spezialbehandlung für Überschriften-Tags
    if key == "ghname":
        if isinstance(val, str) and val.strip():
            items.append(("───2", val.strip()))
        return items
    if key == "gueber2":
        if isinstance(val, str) and val.strip():
            items.append(("───1", val.strip()))
        return items
    if key == "gueber1":
        # gueber1 wird jetzt als Sektionstitel verwendet, 
        # wir überspringen es im rekursiven Body
        return items

    # Helper für Label
    label_raw = FIELD_LABELS.get(key, key)
    if label_raw is None:
        # Explizit ausgeblendet (z.B. id)
        return items
        
    label_text = label_raw if label_raw else key.capitalize()
    
    # Einrückung / Symbolik (User requested removal of prefix ▸)
    indent = "  " * level
    display_label = f"{indent}{label_text}"
    
    if isinstance(val, str):
        if val.strip():
            items.append((display_label, val.strip()))
            
    elif isinstance(val, list):
        # Liste von Elementen (z.B. mehrere 'gebiet' Einträge)
        # Wenn wir auf Level 0 sind (z.B. der 'gebiete'-Block selbst)
        # zeigen wir keinen Label-Header an, wenn der Inhalt selbst Überschriften liefert
        # Aber hier bleiben wir generisch.
        
        # Falls die Liste nur aus Gebieten besteht, wollen wir vielleicht keinen Extra-Header
        if key not in ["gebiet", "gebiete"]:
             items.append((display_label, "")) 

        for i, sub_item in enumerate(val):
            # Rekursiver Aufruf für Listenelemente
            if isinstance(sub_item, dict):
                # Wir sortieren die Keys innerhalb des Gebiets
                # Wir sortieren die Keys nur, wenn wir spezielle Prioritäten haben, 
                # sonst bewahren wir die XML-Reihenfolge (Dict insertion order).
                keys_to_render = sub_item.keys()
                    
                for k in keys_to_render:
                    items.extend(recursive_render(k, sub_item[k], level + 1))
            else:
                items.append((f"{indent}  •", str(sub_item).strip()))
                
    elif isinstance(val, dict):
        # Dict (z.B. ein <gebiete>-Container)
        if key != "gebiete": # Container-Tags oft redundant, wenn sie gueberX enthalten
            items.append((display_label, ""))
        
        keys_to_render = val.keys()
            
        for k in keys_to_render:
            items.extend(recursive_render(k, val[k], level + 1 if key != "gebiete" else level))
    return items

def build_sections(d):
    """Baut Sektionen dynamisch aus allen vorhandenen Feldern."""
    sections = []
    used_keys = set()
    
    # 1. Definierte Sektionen (Standard-Felder)
    for section_title, field_keys in SECTION_ORDER:
        facts = []
        for key in field_keys:
            val = d.get(key)
            if isinstance(val, str) and val.strip():
                label = FIELD_LABELS.get(key, key)
                if label:
                    facts.append((label, val.strip()))
                    used_keys.add(key)
        if facts:
            sections.append((section_title, facts))
            
    # 2. Alles andere (außer 'gebiete' und bereits benutzte)
    extra_facts = []
    # Hier bewahren wir die Reihenfolge der restlichen Keys aus dem Original-Dict
    remaining_keys = [k for k in d.keys() if k not in used_keys and k not in ["id", "gebiete"]]
    
    for key in remaining_keys:
        val = d[key]
        if val:
            extra_facts.extend(recursive_render(key, val, level=0))
            
    if extra_facts:
        sections.append(("Weitere Informationen", extra_facts))
        
    # 3. 'gebiete' Blöcke als EIGENE Sektionen
    gebiete_raw = d.get("gebiete")
    if gebiete_raw:
        # Sicherstellen, dass es eine Liste ist (fals nur ein <gebiete> existiert)
        gebiete_list = gebiete_raw if isinstance(gebiete_raw, list) else [gebiete_raw]
        
        for block in gebiete_list:
            if not isinstance(block, dict):
                continue
                
            # Titel aus gueber1 nehmen
            block_title = str(get_single_value(block.get("gueber1")) or "Gebiete").strip()
            
            # Den Blockinhalt rendern
            block_facts = []
            
            # Erst gueber2 (Kategorie-Header)
            if "gueber2" in block:
                block_facts.extend(recursive_render("gueber2", block["gueber2"], level=0))
                
            # Dann die einzelnen Gebiete
            gebiet_items = block.get("gebiet", [])
            if not isinstance(gebiet_items, list):
                gebiet_items = [gebiet_items]
            
            for item in gebiet_items:
                if isinstance(item, dict):
                    # Den Namen (ghname) als Subheader level 2 rendern
                    # plus alle anderen Felder
                    for k in item.keys():
                        block_facts.extend(recursive_render(k, item[k], level=0))
                elif item:
                    block_facts.append(("Info", str(item)))
            
            if block_facts:
                if sections and sections[-1][0] == block_title:
                    # An bestehende Sektion anhängen, wenn Titel identisch
                    sections[-1][1].extend(block_facts)
                else:
                    # Neue Sektion erstellen
                    sections.append((block_title, block_facts))
    
    return sections


def decode_xml(path: str) -> str:
    b = Path(path).read_bytes()
    try:
        return b.decode("utf-16")
    except UnicodeError:
        return b.decode("utf-8")

def slugify(s: str) -> str:
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s or "unbekannt"

# Templates
env = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html"])
)
tpl_state = env.get_template("state.html")
tpl_index = env.get_template("index.html")

# Daten lesen (Generisch)
root = ET.fromstring(decode_xml(IN_FILE))
states = []

root_elem = ET.fromstring(decode_xml(IN_FILE))
found_states = root_elem.findall("./staat")
if not found_states:
    print(f"WARNUNG: Keine <staat> Einträge in {IN_FILE} gefunden!")

for st in found_states:
    # Nutze generischen Parser für den ganzen Staat
    d = parse_element(st)
    if d and isinstance(d, dict):
        states.append(d)
    else:
        print(f"WARNUNG: Konnte Staat-Element nicht parsen oder ungültiges Format: {st.get('id', 'unbekannt')}")

OUT_DIR.mkdir(parents=True, exist_ok=True)
(OUT_DIR / "assets").mkdir(parents=True, exist_ok=True)
(OUT_DIR / "staaten").mkdir(parents=True, exist_ok=True)

# CSS kopieren
if Path("assets/style.css").exists():
    (OUT_DIR / "assets" / "style.css").write_text(
        Path("assets/style.css").read_text(encoding="utf-8"),
        encoding="utf-8"
    )

# Slugs bauen
used_slugs = {}
def unique_slug(name: str) -> str:
    base = slugify(name)
    if base not in used_slugs:
        used_slugs[base] = 1
        return base
    used_slugs[base] += 1
    return f"{base}-{used_slugs[base]}"

def get_single_value(val):
    """Hilfsfunktion: Gibt den ersten Wert zurück, falls es eine Liste ist, sonst den Wert selbst."""
    if isinstance(val, list):
        return val[0] if val else ""
    return val

# Seiten generieren
today = datetime.now(timezone.utc).date().isoformat()
index_cards = []

for d in states:
    # Safely get name
    name = get_single_value(d.get("hname"))
    if not name: name = "Unbekannt"
    
    slug = unique_slug(name)
    url_path = f"/staaten/{slug}/"
    canonical = f"{BASE_URL}{url_path}"

    # Sektionen bauen
    sections = build_sections(d)

    subtitle = get_single_value(d.get("sname"))
    hauptstadt = get_single_value(d.get("hauptstadt"))
    einw = get_single_value(d.get("einwzahl"))

    description_parts = []
    if hauptstadt: description_parts.append(f"Hauptstadt: {hauptstadt}")
    if einw: description_parts.append(f"Einwohner: {einw}")
    description = (subtitle or f"Fakten und Steckbrief zu {name}.")
    if description_parts:
        description = (description + " – " + " · ".join(description_parts))[:160]

    # FAQPage Schema (Sehr gut für "People also ask" Boxen in Google)
    faq_items = []
    
    # Helper für FAQ
    def add_faq(question_tmpl, key, label_in_answer=None):
        val = get_single_value(d.get(key))
        if val:
            ans = f"{val}."
            if label_in_answer:
                ans = f"{label_in_answer} {ans}"
            faq_items.append({
                "@type": "Question",
                "name": question_tmpl.format(name),
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": ans
                }
            })

    add_faq("Wie viele Einwohner hat {}?", "einwzahl", "Die Einwohnerzahl beträgt ca.")
    add_faq("Was ist die Hauptstadt von {}?", "hauptstadt", "Die Hauptstadt ist")
    add_faq("Welche Währung hat {}?", "waehrung", "Die Währung ist")
    add_faq("Welche Sprache spricht man in {}?", "amtssprache", "Die Amtssprache ist")
    add_faq("Wie groß ist {}?", "flaeche", "Die Fläche beträgt")

    # Flagge bestimmen
    autokennz = d.get("autokennz", "")
    iso3 = ""
    if "|" in autokennz:
        iso3 = autokennz.split("|")[-1].strip()
    elif autokennz:
        iso3 = autokennz.strip()
    flag_code = ISO3_TO_ISO2.get(iso3, "").lower()

    # Flaggen-URL für og:image und Schema
    flag_url = f"https://flagcdn.com/w640/{flag_code}.png" if flag_code else None

    # JSON-LD (WebPage + Country + Breadcrumb + FAQPage)
    country_schema = {
        "@type": "Country",
        "@id": f"{canonical}#country",
        "name": name,
        "alternateName": subtitle or None,
        "description": description,
        "identifier": get_single_value(d.get("id")) or None,
    }
    # Enriched Country properties
    if hauptstadt:
        country_schema["capital"] = {"@type": "City", "name": hauptstadt}
    if einw:
        country_schema["population"] = einw
    flaeche = get_single_value(d.get("flaeche"))
    if flaeche:
        country_schema["areaServed"] = flaeche
    amtssprache = get_single_value(d.get("amtssprache"))
    if amtssprache:
        country_schema["knowsLanguage"] = amtssprache
    if flag_url:
        country_schema["image"] = flag_url

    graph_nodes = [
        {
            "@type": "WebPage",
            "@id": canonical,
            "url": canonical,
            "name": f"{name} – {SITE_NAME}",
            "description": description,
            "inLanguage": "de",
            "breadcrumb": {"@id": f"{canonical}#breadcrumb"},
            "mainEntity": {"@id": f"{canonical}#country"}
        },
        country_schema,
        {
            "@type": "BreadcrumbList",
            "@id": f"{canonical}#breadcrumb",
            "itemListElement": [
                {
                    "@type": "ListItem",
                    "position": 1,
                    "name": "Alle Länder",
                    "item": BASE_URL + "/"
                },
                {
                    "@type": "ListItem",
                    "position": 2,
                    "name": name,
                    "item": canonical
                }
            ]
        }
    ]

    if faq_items:
        graph_nodes.append({
            "@type": "FAQPage",
            "mainEntity": faq_items
        })

    jsonld_obj = {
        "@context": "https://schema.org",
        "@graph": graph_nodes
    }
    # Clean up None values
    def clean_obj(obj):
        if isinstance(obj, dict):
            return {k: clean_obj(v) for k, v in obj.items() if v is not None}
        elif isinstance(obj, list):
            return [clean_obj(i) for i in obj]
        return obj

    json_ld = json.dumps(clean_obj(jsonld_obj), ensure_ascii=False)


    
    # Render State
    html = tpl_state.render(
        title=f"{name} – {SITE_NAME}",
        description=description,
        canonical=f"{BASE_URL}{url_path}",
        name=name,
        subtitle=str(d.get("sname") or ""),
        sections=sections,
        updated=str(d.get("stand") or ""),
        SITE_ROOT=SITE_ROOT,
        SITE_NAME=SITE_NAME,
        jsonld=json_ld,
        flag_code=flag_code,
        og_image=flag_url,
    )
    out_file = OUT_DIR / url_path.lstrip("/") / "index.html"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(html, encoding="utf-8")
    
    # Metadata for index
    hint = d.get("hauptstadt") or d.get("flaeche") or ""
    if isinstance(hint, list): hint = hint[0]
    index_cards.append({
        "name": name, 
        "url": url_path, 
        "hint": str(hint),
        "flag_code": flag_code
    })

# Index JSON-LD
index_jsonld_obj = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "url": BASE_URL + "/",
    "name": SITE_NAME,
    "description": "Umfassende Fakten zu allen Staaten der Welt.",
    "potentialAction": {
        "@type": "SearchAction",
        "target": {
            "@type": "EntryPoint",
            "urlTemplate": BASE_URL + "/?q={search_term_string}"
        },
        "query-input": "required name=search_term_string"
    }
}
index_jsonld = json.dumps(index_jsonld_obj, ensure_ascii=False)

# Index
index_description = f"Steckbriefe, Fakten und Daten zu allen {len(index_cards)} Staaten der Welt – Hauptstädte, Einwohnerzahlen, Wirtschaft, Geografie und mehr."
index_html = tpl_index.render(
    title=f"Alle Staaten der Welt – {SITE_NAME}",
    description=index_description,
    canonical=f"{BASE_URL}/",
    states=sorted(index_cards, key=lambda x: x["name"].lower()),
    SITE_ROOT=SITE_ROOT,
    SITE_NAME=SITE_NAME,
    jsonld=index_jsonld
)
(OUT_DIR / "index.html").write_text(index_html, encoding="utf-8")

# sitemap.xml + robots.txt (Google empfiehlt Sitemaps bauen & einreichen)
# lastmod wird bewusst weggelassen – Google empfiehlt: nur echte Änderungsdaten verwenden
urls = [f"{BASE_URL}/"] + [f"{BASE_URL}{c['url']}" for c in index_cards]
sitemap_items = "\n".join(
    f"<url><loc>{u}</loc></url>"
    for u in sorted(urls)
)
sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{sitemap_items}
</urlset>"""
(OUT_DIR / "sitemap.xml").write_text(sitemap, encoding="utf-8")
(OUT_DIR / "robots.txt").write_text(
    f"User-agent: *\nAllow: /\nSitemap: {BASE_URL}/sitemap.xml\n",
    encoding="utf-8"
)

print(f"OK: {len(index_cards)} Seiten gebaut → {OUT_DIR}/")
