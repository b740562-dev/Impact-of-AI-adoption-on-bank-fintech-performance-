"""ai_patents (proxy 3): ln(1 + AI patent applications filed in the FY), same search for all panel banks; none = 0.

Source: Google Patents Public Datasets on BigQuery (`patents-public-data.patents.publications`).
AI patent = CPC class G06N* OR a CLAUDE.md dictionary term in the English title/abstract.
Applications are counted once (distinct application_number) by filing date -> FY.

Setup (once): Google Cloud project with the BigQuery API enabled, then either
  gcloud auth application-default login         (no key file), or
  a service-account key JSON with GOOGLE_APPLICATION_CREDENTIALS=<path> in .env
and GCP_PROJECT=<your-project-id> in .env (.env is gitignored; never commit keys).
Run:  python 11_patents.py --dry-run   (prints bytes the query would scan; free tier = 1 TB/month)
      python 11_patents.py --run       (executes; writes data/interim/patents.csv, logs/patents.log)
"""
import os
import re
import sys

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from google.cloud import bigquery

from ai_terms import count_terms
from config import FIRMS, INTERIM, RAW

ROOT = RAW.parent.parent
load_dotenv(ROOT / ".env")
LOG = ROOT / "logs" / "patents.log"
LOG.parent.mkdir(exist_ok=True)
PANEL = [f[0] for f in FIRMS if f[4]]
ASSIGNEE = {
    "SBI": r"^STATE BANK OF INDIA", "BOB": r"^BANK OF BARODA", "PNB": r"^PUNJAB NATIONAL BANK", "CANARA": r"^CANARA BANK",
    "UNION": r"^UNION BANK OF INDIA", "BOI": r"^BANK OF INDIA", "INDIAN": r"^INDIAN BANK( LTD| LIMITED)?$",
    "CENTRAL": r"^CENTRAL BANK OF INDIA", "IOB": r"^INDIAN OVERSEAS BANK", "UCO": r"^UCO BANK", "BOM": r"^BANK OF MAHARASHTRA",
    "PSB": r"^PUNJAB (AND|&) SIND BANK", "HDFC": r"^HDFC BANK", "ICICI": r"^ICICI BANK", "AXIS": r"^AXIS BANK",
    "KOTAK": r"^KOTAK MAHINDRA BANK", "INDUSIND": r"^INDUSIND BANK", "FEDERAL": r"^(THE )?FEDERAL BANK( LTD| LIMITED)?$",
    "YES": r"^YES BANK", "RBL": r"^(RBL BANK|RATNAKAR BANK)", "KVB": r"^(THE )?KARUR VYSYA BANK", "CUB": r"^CITY UNION BANK",
    "SIB": r"^(THE )?SOUTH INDIAN BANK", "DCB": r"^(DCB BANK|DEVELOPMENT CREDIT BANK)", "IDFCFIRST": r"^IDFC (FIRST )?BANK"}
PATTERN = "|".join(f"({p})" for p in ASSIGNEE.values())

SQL = """
SELECT p.publication_number, p.application_number, p.filing_date, p.country_code, a.name AS assignee,
  (SELECT LOGICAL_OR(c.code LIKE 'G06N%') FROM UNNEST(p.cpc) c) AS cpc_g06n,
  (SELECT STRING_AGG(t.text, ' ') FROM UNNEST(p.title_localized) t WHERE t.language = 'en') AS title,
  (SELECT STRING_AGG(x.text, ' ') FROM UNNEST(p.abstract_localized) x WHERE x.language = 'en') AS abstract
FROM `patents-public-data.patents.publications` p, UNNEST(p.assignee_harmonized) a
WHERE REGEXP_CONTAINS(UPPER(a.name), @pattern) AND p.filing_date >= 20090401
"""

client = bigquery.Client(project=os.environ.get("GCP_PROJECT"))
cfg = bigquery.QueryJobConfig(query_parameters=[bigquery.ScalarQueryParameter("pattern", "STRING", PATTERN)])
if "--run" not in sys.argv:
    dry = client.query(SQL, job_config=bigquery.QueryJobConfig(dry_run=True, use_query_cache=False,
                                                               query_parameters=cfg.query_parameters))
    print(f"dry run: query would scan {dry.total_bytes_processed / 1e9:.1f} GB (free tier 1,000 GB/month). "
          f"Re-run with --run to execute.")
    sys.exit(0)

df = client.query(SQL, job_config=cfg).to_dataframe()
df.to_csv(RAW / "patents_bigquery_raw.csv", index=False)  # gitignored raw pull
df["bank_id"] = df["assignee"].map(lambda n: next((b for b, p in ASSIGNEE.items() if re.search(p, str(n).upper())), None))
df = df[df["bank_id"].notna()].copy()
text = (df["title"].fillna("") + " " + df["abstract"].fillna(""))
df["kw_ai"] = text.map(lambda t: sum(count_terms(t).values()) > 0)
df["ai"] = df["cpc_g06n"].fillna(False) | df["kw_ai"]
fd = pd.to_datetime(df["filing_date"].astype(int).astype(str), format="%Y%m%d")
df["fy"] = fd.dt.year + (fd.dt.month >= 4).astype(int)
apps = df[df["ai"]].drop_duplicates(["bank_id", "application_number"])
n = apps.groupby(["bank_id", "fy"]).size().rename("n_ai_patent_apps").reset_index()

grid = pd.MultiIndex.from_product([PANEL, range(2011, 2027)], names=["bank_id", "fy"]).to_frame(index=False)
out = grid.merge(n, on=["bank_id", "fy"], how="left", validate="one_to_one").fillna({"n_ai_patent_apps": 0})
out["n_ai_patent_apps"] = out["n_ai_patent_apps"].astype(int)
out["ai_patents"] = np.log1p(out["n_ai_patent_apps"])
out.to_csv(INTERIM / "patents.csv", index=False)

with open(LOG, "w", encoding="utf-8") as f:
    print("assignee name variants matched per bank (check for wrong matches):", file=f)
    print(df.groupby("bank_id")["assignee"].unique().to_string(), file=f)
    print("\nAI applications by bank and country of filing:", file=f)
    print(apps.groupby(["bank_id", "country_code"]).size().to_string(), file=f)
print(f"rows pulled: {len(df)}; AI applications: {len(apps)}; banks with >= 1: {apps.bank_id.nunique()} of {len(PANEL)}")
print(out.groupby("bank_id")["n_ai_patent_apps"].sum().sort_values(ascending=False).head(12).to_string())
print(f"details (assignee variants): {LOG}")
