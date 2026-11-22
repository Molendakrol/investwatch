"""Polish/English phrase patterns used by the rules.

All patterns run on *normalized* text (lower-case, Polish diacritics folded,
'ł' -> 'l'), so 'ryzyko', 'Ryzyko' and 'ryzyka' share stems like 'ryzyk'.
"""

import re


def rx(*parts: str) -> re.Pattern[str]:
    return re.compile("|".join(f"(?:{p})" for p in parts))


# --- generic marketing content -------------------------------------------------
PROFIT = rx(
    r"\bzysk", r"\bzarob", r"stop[aey] zwrotu", r"\bzwrot\w* (?:z inwestycji|na poziomie)", r"\bdochod",
    r"\boprocentowan", r"\brentownos", r"\bprofit", r"\breturns?\b", r"\+\s?\d+[.,]?\d*\s?%",
    r"\d+[.,]?\d*\s?% (?:rocznie|w skali roku|miesiecznie|dziennie|tygodniowo|r/r|p\.a\.)",
    r"\bpomnoz", r"\bpodwo[ij]", r"\bwyniki? inwestycyjn",
)
RISK = rx(
    r"\bryzyk", r"\bstrat", r"\butrat", r"mozesz straci", r"mozna straci", r"\bstracic",
    r"nie (?:ma|daje|stanowi) gwarancj", r"brak gwarancji", r"kapital (?:jest )?zagrozon",
    r"zlozonymi instrumentami", r"\brisk", r"\blose\b", r"\blosing\b", r"capital at risk",
    r"\bzmiennos", r"wahan",
)
PROMO = rx(
    r"\bzaloz konto", r"\botworz (?:konto|rachunek)", r"\bzarejestruj", r"\bdolacz", r"\bskorzystaj",
    r"\bpromocj", r"\boferta\b", r"\bofert[ayę]", r"\bbonus", r"\bkod(?:em)? (?:rabatowy|promocyjny)",
    r"\bzacznij inwestowac", r"\binwestuj\b", r"\bsprawdz", r"\bsign up", r"\bopen an account",
)
AD_LABEL = rx(
    r"\breklama\b", r"\bmaterial (?:reklamowy|marketingowy|promocyjny)", r"komunikat marketingowy",
    r"#reklama", r"#ad\b", r"#sponsored", r"wspolpraca reklamowa", r"\bsponsorowan", r"marketing communication",
    r"\bplatna wspolpraca", r"\bpartnerstwo platne",
)
COMPANY_FORM = rx(
    r"\bs\.\s?a\.", r"\bsp\.\s?z\s?o\.\s?o\.", r"spolka akcyjna", r"\bdom maklerski", r"\bltd\b",
    r"\bgmbh\b", r"\bs\.\s?p\.\s?a\.", r"\bplc\b", r"\bn\.v\.", r"\binc\.",
)

# --- historical performance, forecasts, tax, comparisons -----------------------
HISTORICAL = rx(
    r"w (?:ciagu )?ostatni\w* \d+ (?:lat|latach|miesiac)", r"\bw 20\d\d\b", r"za (?:rok )?20\d\d",
    r"\bhistoryczn", r"od poczatku roku", r"\bytd\b", r"stop[aey] zwrotu (?:za|w)", r"\bwynik\w* (?:za|w) (?:rok|ostatni)",
    r"osiagnel\w* \+?\d", r"zarobil\w* \+?\d", r"\b20\d\d:\s*[+-]?\d",
)
FIVE_YEARS = rx(r"\b5 lat", r"\bpiec lat", r"\bpieciu lat", r"\b5-letni", r"\bostatnich 5\b")
FULL_PERIODS = rx(r"12[- ]miesiecz", r"pelne? (?:okresy|lata)", r"okres(?:y)? 12 miesiecy", r"okres referencyjny")
SOURCE = rx(r"\bzrodlo\b", r"\bzrodlo:", r"\bsource:", r"\bna podstawie danych", r"\bdane:")
FX = rx(r"\busd\b", r"\beur\b", r"\bchf\b", r"\bgbp\b", r"\bdolar", r"\beuro\b", r"\bwalut")
FX_WARNING = rx(r"(?:zmian|wahan)\w* kurs\w* walut", r"ryzyk\w* walutow", r"kurs\w* walut\w* moze")
FEES = rx(r"\bprowizj", r"\boplat", r"\bkoszt", r"\bobciazen")
PAST_NOT_INDICATOR = rx(
    r"wyniki? historyczn\w* nie (?:sa|stanowi\w*|jest) (?:gwarancj|wiarygodn|wskaznik)",
    r"przeszle wyniki nie", r"past performance is not",
)
FORECAST = rx(
    r"\bprognoz", r"\bprzewidujemy", r"\boczekiwan\w* (?:zysk|zwrot|stop)", r"\bpotencjal wzrostu",
    r"\bcel cenowy", r"\bosiagnie\b", r"\bwzrosnie\b", r"\bbedzie warte?", r"\bw przyszlym roku", r"\bdo konca 20\d\d",
    r"\bpodwoi sie",
)
FORECAST_WARNING = rx(
    r"prognoz\w* nie (?:sa|jest|stanowi\w*) (?:wiarygodn|gwarancj|wskaznik)",
    r"przyszle wyniki (?:moga|nie)", r"forecasts? (?:are|is) not",
)
TAX = rx(r"\bpodat", r"\bbelk", r"\bike\b", r"\bikze\b", r"\bulg[ai] podatk", r"zwolnien\w* (?:z )?podatk", r"\btax")
TAX_CAVEAT_INDIVIDUAL = rx(r"indywidualn\w* sytuacj", r"sytuacji (?:podatkowej )?(?:klienta|inwestora)")
TAX_CAVEAT_CHANGE = rx(r"moze (?:ulec )?zmian", r"moga (?:ulec )?zmian", r"podlega\w* zmian")
COMPARISON = rx(
    r"\bnajlepsz", r"\blepsz\w* niz", r"\btansz\w* niz", r"\bwyzsz\w* niz", r"\bw porownaniu", r"\bvs\.?\b",
    r"\bniz (?:w )?(?:bank|konkurencj|lokat)", r"\bnajtansz", r"\bnajwyzsz", r"\bbije na glowe",
)

# --- supervisory authority -----------------------------------------------------
KNF = rx(r"\bknf\b", r"\buknf\b", r"komisj\w* nadzoru finansowego", r"\bnadzor\w* (?:finansow|knf)")
APPROVAL = rx(
    r"zatwierdz", r"\baprob", r"rekomend\w* (?:przez )?(?:knf|komisj)", r"\bcertyfik", r"\bpoparci",
    r"zaakceptowan", r"zatwierdzon", r"autoryzowan\w* produkt", r"\bpoleca(?:ny|na) przez",
)
SAFETY = rx(r"\bbezpieczn", r"\bpewn\w* inwestycj", r"\bbez ryzyka", r"\bochron\w* (?:kapitalu|srodkow)", r"\bgwarant", r"\bspokojn")

# --- module 1: third-party promotion -------------------------------------------
AFFILIATE = rx(
    r"\bkod\w* (?:rabatowy|promocyjny|polecajacy)", r"\blink\w* (?:w bio|polecajac|afiliacyjn|partnersk|ponizej)",
    r"\breflink", r"z mojego linku", r"przez moj link", r"\bmoj kod", r"#wspolpraca", r"#partner", r"#ad\b",
    r"\bpartner\w* (?:kanalu|odcinka|materialu)", r"\bsponsor\w* (?:odcinka|filmu|kanalu)", r"\bwspolpraca reklamowa",
    r"\bbonus\w* na start", r"\bodbierz bonus", r"\bdarmow\w* akcj",
)

# --- module 3: investment advice -----------------------------------------------
ADVICE_STRONG = rx(
    r"\brekomendujemy (?:zakup|kupn|sprzedaz|nabyc)", r"\brekomenduje (?:zakup|kupn|sprzedaz|nabyc)",
    r"\bdoradzamy\b", r"\bdoradztw\w* inwestycyjn", r"\bindywidualn\w* (?:strategi|rekomendac|porad|portfel)",
    r"\bspersonalizowan\w* (?:portfel|rekomendac|strategi|porad)", r"\bdobierzemy\b.*\bportfel",
    r"\bportfel\w* (?:modelow|szyt\w* na miar)", r"\bsygnal\w* (?:transakcyjn|kupna|sprzedazy)", r"\bbuy signal",
    r"\bkupuj\b", r"\bsprzedaj\b", r"\bpowiemy ci\b.*\b(?:kupic|sprzedac)", r"\bco kupic\b", r"\bdla ciebie (?:akcje|spolki|fundusze)",
    r"\bzarzadzani\w* (?:twoim )?(?:majatkiem|portfelem|aktywami)", r"\bwealth management", r"\bfamily office",
    r"\binvestment (?:consulting|advisory)", r"\bkonsultacj\w* inwestycyjn", r"\bopiek\w* inwestycyjn",
)
ADVICE_CONTEXT = rx(
    r"\bdopasow\w* do (?:twoich|twojej|potrzeb|profilu|sytuacji)", r"\bna podstawie (?:twojej|twoich|analizy twoj)",
    r"\bprofil\w* ryzyka", r"\bcele inwestycyjn", r"\bumow\w* (?:konsultacj|spotkan)", r"\bpierwsza konsultacja",
    r"\bkonsultacj\w* (?:1:1|indywidualn|online)", r"\bspotkani\w* z doradc", r"\bwyceni\w* portfel",
)
INSTRUMENT = rx(
    r"\bakcj", r"\bobligacj", r"\betf", r"\bfundusz", r"\bkontrakt", r"\bcfd\b", r"\bopcj", r"\bforex\b",
    r"\bkryptowalut", r"\bpapier\w* wartosciow", r"\bspolk\w* (?:gieldow|z gpw)", r"\binstrument\w* finansow", r"\bgpw\b",
    r"\bcertyfikat\w* inwestycyjn", r"\bwarrant",
)
FEE_FOR_ADVICE = rx(
    r"\bzl\s?/\s?(?:mies|miesiac|h|godz)", r"\babonament", r"\bsubskrypcj", r"\bwynagrodzeni\w* (?:od|za) (?:wyniku|sukces)",
    r"\bsuccess fee", r"\bprowizj\w* od zysku", r"\bcena konsultacji", r"\bpakiet\w* (?:premium|vip|gold)", r"\bdostep vip",
)
EDUCATION_ONLY = rx(
    r"\bnie stanowi\w* (?:porady|rekomendacji|doradztwa)", r"\bmaterial (?:ma )?charakter\w* edukacyjn",
    r"\bnie (?:jest|sa) (?:porada|rekomendacja)", r"\bnot investment advice",
)

GUARANTEE = rx(r"\bgwarant\w* (?:zysk|zwrot)", r"\bbez ryzyka\b", r"\bpewny zysk", r"\b100% bezpieczn", r"\bzero ryzyka")

JARGON = rx(
    r"\bdelta\b", r"\bgamma\b", r"\bkontango", r"\bbackwardation", r"\blewarowan", r"\bdepozyt zabezpieczajac",
    r"\bmarza wstepna", r"\bwezwanie do uzupelnienia depozytu", r"\bmargin call", r"\bsuperpozycj", r"\bkowarianc",
    r"\bvar\b", r"\bdurati", r"\bwolumen", r"\bstochast",
)
