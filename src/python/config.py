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

# index_id, name, Yahoo ticker
INDICES = [
    ("NIFTY500", "Nifty 500", "^CRSLDX"),
    ("NIFTYBANK", "Nifty Bank", "^NSEBANK"),
]


def fiscal_year(dates):
    """FY2017 = 1 Apr 2016 to 31 Mar 2017."""
    return dates.year + (dates.month >= 4).astype(int)
