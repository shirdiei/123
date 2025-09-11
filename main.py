from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import os

CSV_PATH = os.getenv("CSV_PATH", "data/items.csv")

# --- טוענים את ה-CSV פעם אחת ---
df = pd.read_csv(CSV_PATH).fillna("")
expected = ["Name", "Image", "Category", "where", "Marca"]
missing = [c for c in expected if c not in df.columns]
if missing:
    raise RuntimeError(f"CSV missing columns: {missing}")
df = df[expected].copy()
df.insert(0, "id", range(1, len(df) + 1))  # מזהה סינטטי

# קטגוריות עם ספירה
cat_counts = (
    df.groupby("Category", dropna=False)
      .size()
      .reset_index(name="count")
      .sort_values(["Category"])
)

app = FastAPI(title="Items API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    id: int
    Name: str
    Image: str
    Category: str
    where: str
    Marca: str

class PagedItems(BaseModel):
    total: int
    items: list[Item]

@app.get("/")
def health():
    return {"ok": True, "rows": len(df)}

@app.get("/categories")
def categories():
    return [{"category": r.Category, "count": int(r["count"])} for _, r in cat_counts.iterrows()]

@app.get("/items", response_model=PagedItems)
def list_items(
    q: str | None = Query(None, description="חיפוש בשם/מותג/מיקום"),
    category: str | None = None,
    where: str | None = None,
    marca: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    view = df
    if category:
        view = view[view["Category"].str.contains(category, case=False, na=False)]
    if where:
        view = view[view["where"].str.contains(where, case=False, na=False)]
    if marca:
        view = view[view["Marca"].str.contains(marca, case=False, na=False)]
    if q:
        mask = (
            view["Name"].str.contains(q, case=False, na=False) |
            view["Marca"].str.contains(q, case=False, na=False) |
            view["where"].str.contains(q, case=False, na=False) |
            view["Category"].str.contains(q, case=False, na=False)
        )
        view = view[mask]

    total = len(view)
    page = view.iloc[offset: offset + limit]
    items = [Item(**row.to_dict()) for _, row in page.iterrows()]
    return {"total": total, "items": items}

@app.get("/items/{item_id}", response_model=Item)
def get_item(item_id: int):
    row = df[df["id"] == item_id]
    if row.empty:
        return Item(id=item_id, Name="", Image="", Category="", where="", Marca="")
    return Item(**row.iloc[0].to_dict())
