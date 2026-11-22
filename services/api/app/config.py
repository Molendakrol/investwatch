import os
from pathlib import Path

_here = Path(__file__).resolve()
# Repository root when run from source; inside the container the app lives in /srv/app.
ROOT = _here.parents[3] if len(_here.parents) > 3 else _here.parents[1]

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{ROOT / 'data' / 'investwatch.db'}")
OBJECT_STORE_DIR = Path(os.getenv("OBJECT_STORE_DIR", str(ROOT / "data" / "objects")))
INTERNAL_TOKEN = os.getenv("INTERNAL_TOKEN", "dev-internal-token")
DEMO_SITE_URL = os.getenv("DEMO_SITE_URL", "http://localhost:8080").rstrip("/")
DEMO_MANIFEST = Path(os.getenv("DEMO_MANIFEST", str(ROOT / "demo-sites" / "site" / "manifest.json")))
SWEEP_INTERVAL_MINUTES = float(os.getenv("SWEEP_INTERVAL_MINUTES", "30"))
REGISTER_INTERVAL_HOURS = float(os.getenv("REGISTER_INTERVAL_HOURS", "24"))
CORS_ORIGINS = [o for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o]
DEFAULT_THRESHOLD = float(os.getenv("DEFAULT_THRESHOLD", "50"))

KNF_REGISTER_SOURCES = [
    ("Rejestr UKNF — domy maklerskie",
     "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych/domy_maklerskie"),
    ("Rejestr UKNF — banki prowadzące działalność maklerską",
     "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych/Banki_prowadzace_dzialalnosc_maklerska"),
    ("Rejestr UKNF — oddziały zagranicznych firm inwestycyjnych",
     "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych/notyfikowane_firmy_inwestycyjne_oddzialy"),
    ("Rejestr UKNF — zagraniczne firmy inwestycyjne bez oddziału",
     "https://www.knf.gov.pl/podmioty/Podmioty_rynku_kapitalowego/Firmy_inwestycyjne_i_Agenci_firm_inwestycyjnych/notyfikowane_zagraniczne_firmy_inwestycyjne"),
]
