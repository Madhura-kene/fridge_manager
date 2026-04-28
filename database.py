"""
database.py
All database models, session, and seed data.
Every other file imports from here.
"""

from datetime import date
from sqlalchemy import create_engine, Column, Integer, String, Date, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

# ══════════════════════════════════════════════════════════════════════════
# MODELS
# ══════════════════════════════════════════════════════════════════════════

class Inventory(Base):
    __tablename__ = "inventory"
    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(100), nullable=False)
    quantity    = Column(Integer,     nullable=False)
    storage     = Column(String(20),  nullable=False)   # "Fridge" or "Freezer"
    expiry_date = Column(Date,        nullable=True)


class Recipe(Base):
    __tablename__ = "recipes"
    id          = Column(Integer,     primary_key=True, autoincrement=True)
    dish        = Column(String(100), nullable=False)
    ingredients = Column(String(500), nullable=False)   # comma-separated


class MealLog(Base):
    __tablename__ = "meal_log"
    id          = Column(Integer,    primary_key=True, autoincrement=True)
    log_date    = Column(Date,       nullable=False)
    meal_label  = Column(String(50), nullable=False)    # Breakfast / Lunch / Dinner / Snack
    description = Column(Text,       nullable=False)
    calories    = Column(Float,      nullable=True)
    protein_g   = Column(Float,      nullable=True)
    ai_notes    = Column(Text,       nullable=True)


# ══════════════════════════════════════════════════════════════════════════
# SESSION
# ══════════════════════════════════════════════════════════════════════════

engine  = create_engine("sqlite:///fridge.db", echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()


# ══════════════════════════════════════════════════════════════════════════
# SEED DATA
# ══════════════════════════════════════════════════════════════════════════

def seed_example_data():
    if session.query(Inventory).count() == 0:
        today    = date.today()
        safe_day = min(today.day + 2, 28)
        items = [
            ("Milk",   1, "Fridge",  date(today.year, today.month, safe_day)),
            ("Eggs",   6, "Fridge",  None),
            ("Butter", 1, "Fridge",  None),
            ("methi",  2, "Freezer", None),
            ("lasun",  1, "Fridge",  today),
            ("mattar", 2, "Freezer", None),
            ("Tomato", 3, "Fridge",  None),
        ]
        for name, qty, storage, expiry in items:
            session.add(Inventory(name=name, quantity=qty,
                                  storage=storage, expiry_date=expiry))

    if session.query(Recipe).count() == 0:
        recipes = [
            ("Tomato Omelette", "eggs,tomato,butter"),
            ("Pulao",           "rice,peas,spices"),
            ("methi Sandwich",  "methi,bread,butter"),
            ("Milkshake",       "milk,sugar"),
        ]
        for dish, ingredients in recipes:
            session.add(Recipe(dish=dish, ingredients=ingredients))

    session.commit()
