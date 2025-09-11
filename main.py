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
    _df.insert(0, "id", range(1, len(_df)+1))
    _cats = (_df.groupby("Category", dropna=False).size()
             .reset_index(name="count").sort_values(["Category"]))
    return _df, _cats

@app.on_event("startup")
def _startup():
    global df, cat_counts
    df, cat_counts = load_data()

class Item(BaseModel):
    id:int; Name:str; Image:str; Category:str; where:str; Marca:str
class PagedItems(BaseModel):
    total:int; items:list[Item]

@app.get("/")
def health():
    return {"ok": df is not None, "rows": 0 if df is None else int(len(df))}

@app.get("/categories")
def categories():
    if df is None: raise HTTPException(503, "CSV not loaded")
    return [{"category": r.Category, "count": int(r["count"])} for _, r in cat_counts.iterrows()]

@app.get("/items", response_model=PagedItems)
def list_items(q: str|None=None, category:str|None=None, where:str|None=None,
               marca:str|None=None, limit:int=50, offset:int=0):
    if df is None: raise HTTPException(503, "CSV not loaded")
    view = df
    if category: view = view[view["Category"].str.contains(category, case=False, na=False)]
    if where:    view = view[view["where"].str.contains(where, case=False, na=False)]
    if marca:    view = view[view["Marca"].str.contains(marca, case=False, na=False)]
    if q:
        mask = (view["Name"].str.contains(q, case=False, na=False) |
                view["Marca"].str.contains(q, case=False, na=False) |
                view["where"].str.contains(q, case=False, na=False) |
                view["Category"].str.contains(q, case=False, na=False))
        view = view[mask]
    total = len(view)
    page = view.iloc[offset: offset+limit]
    items = [Item(**row.to_dict()) for _, row in page.iterrows()]
    return {"total": total, "items": items}

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id:int):
    if df is None: raise HTTPException(503, "CSV not loaded")
    row = df[df["id"]==item_id]
    if row.empty: raise HTTPException(404, "Not found")
    return Item(**row.iloc[0].to_dict())
