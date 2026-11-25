from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
INTERIM = ROOT / "data" / "interim"
FINAL = ROOT / "data" / "final"
DOCS = ROOT / "docs"

PRICE_START = "2009-01-01"

# bank_id, name, bank_type, NSE ticker, in_panel, in_event_study
FIRMS = [
    ("SBI", "State Bank of India", "PSU", "SBIN.NS", True, True),
    ("BOB", "Bank of Baroda", "PSU", "BANKBARODA.NS", True, True),
    ("PNB", "Punjab National Bank", "PSU", "PNB.NS", True, True),
    ("CANARA", "Canara Bank", "PSU", "CANBK.NS", True, True),
    ("UNION", "Union Bank of India", "PSU", "UNIONBANK.NS", True, False),
    ("BOI", "Bank of India", "PSU", "BANKINDIA.NS", True, False),
    ("INDIAN", "Indian Bank", "PSU", "INDIANB.NS", True, False),
    ("CENTRAL", "Central Bank of India", "PSU", "CENTRALBK.NS", True, False),
    ("IOB", "Indian Overseas Bank", "PSU", "IOB.NS", True, False),
    ("UCO", "UCO Bank", "PSU", "UCOBANK.NS", True, False),
    ("BOM", "Bank of Maharashtra", "PSU", "MAHABANK.NS", True, False),
    ("PSB", "Punjab & Sind Bank", "PSU", "PSB.NS", True, False),
    ("HDFC", "HDFC Bank", "Private", "HDFCBANK.NS", True, True),
    ("ICICI", "ICICI Bank", "Private", "ICICIBANK.NS", True, True),
    ("AXIS", "Axis Bank", "Private", "AXISBANK.NS", True, True),
    ("KOTAK", "Kotak Mahindra Bank", "Private", "KOTAKBANK.NS", True, True),
    ("INDUSIND", "IndusInd Bank", "Private", "INDUSINDBK.NS", True, True),
    ("FEDERAL", "Federal Bank", "Private", "FEDERALBNK.NS", True, False),
    ("YES", "Yes Bank", "Private", "YESBANK.NS", True, False),
    ("RBL", "RBL Bank", "Private", "RBLBANK.NS", True, False),
    ("KVB", "Karur Vysya Bank", "Private", "KARURVYSYA.NS", True, False),
    ("CUB", "City Union Bank", "Private", "CUB.NS", True, False),
    ("SIB", "South Indian Bank", "Private", "SOUTHBANK.NS", True, False),
    ("DCB", "DCB Bank", "Private", "DCBBANK.NS", True, False),
    ("IDFCFIRST", "IDFC First Bank", "Private", "IDFCFIRSTB.NS", True, False),
    ("BAJFIN", "Bajaj Finance", "NBFC", "BAJFINANCE.NS", False, True),
    ("BAJFINSV", "Bajaj Finserv", "NBFC", "BAJAJFINSV.NS", False, True),
    ("PAYTM", "One97 Communications", "Fintech", "PAYTM.NS", False, True),
    ("PBFINTECH", "PB Fintech", "Fintech", "POLICYBZR.NS", False, True),
    ("SBICARD", "SBI Cards and Payment Services", "Fintech", "SBICARD.NS", False, True),
]

BSE_CODES = {
    "SBI": "500112", "BOB": "532134", "PNB": "532461", "CANARA": "532483", "UNION": "532477",
    "BOI": "532149", "INDIAN": "532814", "CENTRAL": "532885", "IOB": "532388", "UCO": "532505",
    "BOM": "532525", "PSB": "533295", "HDFC": "500180", "ICICI": "532174", "AXIS": "532215",
    "KOTAK": "500247", "INDUSIND": "532187", "FEDERAL": "500469", "YES": "532648", "RBL": "540065",
    "KVB": "590003", "CUB": "532210", "SIB": "532218", "DCB": "532772", "IDFCFIRST": "539437",
}

BSE_CODES_EVENT_NONBANK = {
    "BAJFIN": "500034", "BAJFINSV": "532978", "PAYTM": "543396", "PBFINTECH": "543390", "SBICARD": "543066",
}

AR_FY = (2011, 2026)

# Face value (Rs per share) today, and the Yahoo "splits" records that were face-value sub-divisions
# (date -> factor). All other Yahoo split records are bonus issues, which raise paid-up capital but leave
# face value unchanged (e.g. Kotak 2015-07-08, Federal 2015-07-08, ICICI 2017-06-20, HDFC 2025-08-26, CUB, KVB).
FACE_VALUE_NOW = {
    "SBI": 1, "BOB": 2, "PNB": 2, "CANARA": 2, "UNION": 10, "BOI": 10, "INDIAN": 10, "CENTRAL": 10,
    "IOB": 10, "UCO": 10, "BOM": 10, "PSB": 10, "HDFC": 1, "ICICI": 2, "AXIS": 2, "KOTAK": 1,
    "INDUSIND": 10, "FEDERAL": 2, "YES": 2, "RBL": 10, "KVB": 2, "CUB": 1, "SIB": 1, "DCB": 10, "IDFCFIRST": 10,
}
# RBI Table 1 "Capital" includes perpetual non-cumulative preference share capital (PNCPS) for these
# bank-years (evidence: annual report Schedule 1 and/or share-count breaks); equity share count unknown -> NA.
PREF_CAPITAL = {
    "CENTRAL": (2009, 2014, "AR Sch.1 FY2011-14: PNCPS Rs 1,617 cr held by GoI; gone by FY2015"),
    "INDIAN": (2009, 2013, "AR Sch.1 FY2011-13: PNCPS Rs 400 cr (GoI); converted to equity in FY2014"),
    "UCO": (2009, 2013, "AR Sch.1 FY2012: PNCPS held by GoI; capital falls 61% in FY2014"),
    "PSB": (2009, 2021, "AR Sch.1 FY2011-12, FY2015-17, FY2020-21: separate Preference Share Capital line"),
    "BOM": (2009, 2015, "AR Sch.1 FY2011, FY2013-15 paid-up section mentions preference capital"),
    "KOTAK": (2019, 2023, "PNCPS Rs 500 cr issued FY2019 (capital +53%, no bonus), redeemed FY2024 (-33%)"),
}
FV_SPLITS = {
    "SBI": {"2014-11-20": 10}, "BOB": {"2015-01-22": 5}, "PNB": {"2014-12-18": 5}, "CANARA": {"2024-05-15": 5},
    "HDFC": {"2011-07-14": 5, "2019-09-19": 2}, "ICICI": {"2014-12-04": 5}, "AXIS": {"2014-07-28": 5},
    "KOTAK": {"2010-09-13": 2, "2026-01-14": 5}, "FEDERAL": {"2013-10-17": 5}, "YES": {"2017-09-21": 5},
    "KVB": {"2016-11-17": 5}, "SIB": {"2010-09-23": 10},
}

# Bank names exactly as in RBI Statistical Tables Relating to Banks in India (DBIE export)
RBI_NAMES = {
    "STATE BANK OF INDIA": "SBI",
    "BANK OF BARODA": "BOB",
    "PUNJAB NATIONAL BANK": "PNB",
    "CANARA BANK": "CANARA",
    "UNION BANK OF INDIA": "UNION",
    "BANK OF INDIA": "BOI",
    "INDIAN BANK": "INDIAN",
    "CENTRAL BANK OF INDIA": "CENTRAL",
    "INDIAN OVERSEAS BANK": "IOB",
    "UCO BANK": "UCO",
    "BANK OF MAHARASHTRA": "BOM",
    "PUNJAB AND SIND BANK": "PSB",
    "HDFC BANK LTD.": "HDFC",
    "ICICI BANK LIMITED": "ICICI",
    "AXIS BANK LIMITED": "AXIS",
    "KOTAK MAHINDRA BANK LTD.": "KOTAK",
    "INDUSIND BANK LTD": "INDUSIND",
    "FEDERAL BANK LTD": "FEDERAL",
    "YES BANK LTD.": "YES",
    "RBL BANK LTD": "RBL",
    "KARUR VYSYA BANK LTD": "KVB",
    "CITY UNION BANK LIMITED": "CUB",
    "SOUTH INDIAN BANK LTD": "SIB",
    "DCB BANK LIMITED": "DCB",
    "IDFC BANK LIMITED": "IDFCFIRST",  # pre-merger entity; panel keeps FY2019+
    "IDFC FIRST BANK LIMITED": "IDFCFIRST",
}

RBI_GROUPS = {
    "PUBLIC SECTOR BANKS": "PSU",
    "PRIVATE SECTOR BANKS": "Private",
    "NATIONALISED BANKS": "Nationalised",
    "STATE BANK OF INDIA AND ITS ASSOCIATES": "SBI_group",
    "FOREIGN BANKS": "Foreign",
    "SMALL FINANCE BANKS": "SFB",
    "PAYMENTS BANKS": "Payments",
    "ALL SCHEDULED COMMERCIAL BANKS": "All_SCB",
}

# Company names as written in data/raw/events.csv
EVENT_COMPANIES = {
    "HDFC Bank": "HDFC", "ICICI Bank": "ICICI", "Axis Bank": "AXIS", "Kotak Mahindra Bank": "KOTAK",
    "IndusInd Bank": "INDUSIND", "SBI": "SBI", "Bank of Baroda": "BOB", "Punjab National Bank": "PNB",
    "Canara Bank": "CANARA", "Bajaj Finance": "BAJFIN", "Bajaj Finserv": "BAJFINSV",
    "One97 Communications (Paytm)": "PAYTM", "PB Fintech": "PBFINTECH", "SBI Cards": "SBICARD",
    "City Union Bank": "CUB", "Yes Bank": "YES", "Indian Bank": "INDIAN", "Federal Bank": "FEDERAL",
    "Union Bank of India": "UNION", "RBL Bank": "RBL", "IDFC First Bank": "IDFCFIRST",
    "South Indian Bank": "SIB", "Karur Vysya Bank": "KVB", "Bank of India": "BOI",
}

EVENT_CATEGORIES = {
    "product/service launch", "partnership/vendor deal", "ai investment/acquisition", "internal deployment",
}

# index_id, name, Yahoo ticker
INDICES = [
    ("NIFTY500", "Nifty 500", "^CRSLDX"),
    ("NIFTYBANK", "Nifty Bank", "^NSEBANK"),
]


def fiscal_year(dates):
    """FY2017 = 1 Apr 2016 to 31 Mar 2017."""
    return dates.year + (dates.month >= 4).astype(int)
