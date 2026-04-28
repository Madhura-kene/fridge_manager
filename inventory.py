"""
inventory.py
All inventory CRUD operations and query helpers.
Imported by fridge.py (UI) and telegram_bot.py.
"""

import numpy as np
import pandas as pd
from datetime import date, datetime
from database import session, Inventory


def days_until_expiry(expiry_date) -> float:
    if expiry_date is None:
        return np.inf
    today = np.datetime64(date.today())
    exp   = np.datetime64(expiry_date)
    return int((exp - today).astype("timedelta64[D]").astype(int))


def get_all_inventory_dataframe() -> pd.DataFrame:
    rows = [
        {
            "id":          it.id,
            "name":        it.name,
            "quantity":    it.quantity,
            "storage":     it.storage,
            "expiry_date": it.expiry_date.isoformat() if it.expiry_date else "",
        }
        for it in session.query(Inventory).all()
    ]
    return pd.DataFrame(rows)


def add_item(name: str, quantity: int, storage: str, expiry_str: str = "") -> Inventory:
    expiry = None
    if expiry_str:
        try:
            expiry = datetime.strptime(expiry_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Expiry date must be YYYY-MM-DD")
    item = Inventory(name=name.strip(), quantity=int(quantity),
                     storage=storage, expiry_date=expiry)
    session.add(item)
    session.commit()
    return item


def delete_item(item_id: int) -> bool:
    it = session.query(Inventory).filter_by(id=item_id).first()
    if it:
        session.delete(it)
        session.commit()
        return True
    return False


def update_item(item_id: int, quantity=None, expiry_str=None) -> bool:
    it = session.query(Inventory).filter_by(id=item_id).first()
    if not it:
        return False
    if quantity is not None:
        it.quantity = int(quantity)
    if expiry_str is not None:
        it.expiry_date = (None if expiry_str == ""
                          else datetime.strptime(expiry_str, "%Y-%m-%d").date())
    session.commit()
    return True


def export_inventory_csv(filename: str):
    get_all_inventory_dataframe().to_csv(filename, index=False)


def get_restock_list(threshold: int = 2) -> list:
    return session.query(Inventory).filter(Inventory.quantity < threshold).all()


def get_expiring_items(within_days: int = 3) -> list:
    result = []
    for it in session.query(Inventory).all():
        d = days_until_expiry(it.expiry_date)
        if d <= within_days:
            result.append((it, d))
    return result


def get_available_ingredients(filter_storage: str = "Both") -> list:
    inv = session.query(Inventory)
    if filter_storage == "Fridge":
        inv = inv.filter(Inventory.storage == "Fridge")
    elif filter_storage == "Freezer":
        inv = inv.filter(Inventory.storage == "Freezer")
    return [it.name for it in inv if it.quantity > 0]
