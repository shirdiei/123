from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd, os, glob

EXPECTED = ["Name","Image","Category","where","Marca"]
CSV_ENV = os.getenv("CSV_PATH")

app = FastAPI(title="Items API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

df = None
cat_counts = None

def find_csv():
    if CSV_ENV and os.path.exists(CSV_ENV): return CSV_ENV
    for p in ["data/items.csv", "items.csv"]:
        if os.path.exists(p): return p
    # אם אין—ננסה לקחת כל CSV ראשון שנמצא
    found = glob.glob("data/*.csv")+glob.glob("*.csv")
    return found[0] if found else None

def load_data():
    path = find_csv()
    if not path: return None, None
    _df = pd.read_csv(path).fillna("")
    # ודא עמודות
    missing = [c for c in EXPECTED if c not in _df.columns]
    if missing:
        raise RuntimeError(f"CSV missing columns: {missing}")
    _df = _df[EXPECTED].copy()
