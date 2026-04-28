"""
web_app.py
Flask web server for Fridge Manager.
Reuses business logic from inventory.py, recipes_recommendation.py,
nutrition_calculator.py, and database.py.

Run:  python web_app.py
Open:  http://localhost:5000
"""

from flask import Flask, render_template, request, jsonify
from datetime import date, datetime
import numpy as np

from database import session, seed_example_data, Inventory, Recipe, MealLog
from inventory import (
    days_until_expiry, add_item, delete_item, update_item,
    get_restock_list, get_expiring_items, get_available_ingredients,
)
from recipes_recommendation import (
    suggest_recipes, get_all_recipes, add_recipe,
    delete_recipe_by_id, find_recipe_by_name,
)
from nutrition_calculator import (
    add_meal_log, get_meal_logs_for_date,
    delete_meal_log, get_daily_summary, get_nutrition_history,
)
from telegram_bot import (
    telegram_send, telegram_configured,
    build_restock_message, build_expiry_message,
)
from scan import detect_veggies, ollama_is_running
import base64
import io
from PIL import Image

app = Flask(__name__)

# Seed example data on first run
seed_example_data()


# ═══════════════════════════════════════════════════════════════════════════
# PAGES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html")


# ═══════════════════════════════════════════════════════════════════════════
# API: INVENTORY
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/inventory", methods=["GET"])
def api_get_inventory():
    items = session.query(Inventory).all()
    result = []
    for it in items:
        d = days_until_expiry(it.expiry_date)
        result.append({
            "id":          it.id,
            "name":        it.name,
            "quantity":    it.quantity,
            "storage":     it.storage,
            "expiry_date": it.expiry_date.isoformat() if it.expiry_date else "",
            "days_left":   None if d == np.inf else int(d),
        })
    return jsonify(result)


@app.route("/api/inventory", methods=["POST"])
def api_add_item():
    data = request.json
    try:
        item = add_item(
            data["name"],
            int(data["quantity"]),
            data.get("storage", "Fridge"),
            data.get("expiry_date", ""),
        )
        return jsonify({"ok": True, "id": item.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/inventory/<int:item_id>", methods=["PUT"])
def api_update_item(item_id):
    data = request.json
    qty = data.get("quantity")
    exp = data.get("expiry_date")
    if qty is not None:
        qty = int(qty)
    ok = update_item(item_id, quantity=qty, expiry_str=exp)
    return jsonify({"ok": ok})


@app.route("/api/inventory/<int:item_id>", methods=["DELETE"])
def api_delete_item(item_id):
    ok = delete_item(item_id)
    return jsonify({"ok": ok})


# ═══════════════════════════════════════════════════════════════════════════
# API: RESTOCK & EXPIRY
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/restock", methods=["GET"])
def api_restock():
    threshold = request.args.get("threshold", 2, type=int)
    items = get_restock_list(threshold=threshold)
    return jsonify([
        {"id": it.id, "name": it.name, "quantity": it.quantity, "storage": it.storage}
        for it in items
    ])


@app.route("/api/expiring", methods=["GET"])
def api_expiring():
    within = request.args.get("days", 3, type=int)
    items = get_expiring_items(within_days=within)
    return jsonify([
        {
            "id":          it.id,
            "name":        it.name,
            "storage":     it.storage,
            "expiry_date": it.expiry_date.isoformat() if it.expiry_date else "",
            "days_left":   int(d),
        }
        for it, d in items
    ])


# ═══════════════════════════════════════════════════════════════════════════
# API: RECIPES
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/recipes", methods=["GET"])
def api_recipes():
    flt = request.args.get("filter", "Both")
    suggestions = suggest_recipes(filter_storage=flt)
    all_recipes = get_all_recipes()

    suggested_names = {dish for dish, _ in suggestions}
    result = []
    for r in all_recipes:
        result.append({
            "id":          r.id,
            "dish":        r.dish,
            "ingredients": r.ingredients,
            "can_cook":    r.dish in suggested_names,
        })
    return jsonify(result)


@app.route("/api/recipes", methods=["POST"])
def api_add_recipe():
    data = request.json
    try:
        r = add_recipe(data["dish"], data["ingredients"])
        return jsonify({"ok": True, "id": r.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/recipes/<int:recipe_id>", methods=["DELETE"])
def api_delete_recipe(recipe_id):
    ok = delete_recipe_by_id(recipe_id)
    return jsonify({"ok": ok})


# ═══════════════════════════════════════════════════════════════════════════
# API: NUTRITION
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/nutrition/log", methods=["GET"])
def api_get_nutrition():
    d = request.args.get("date", date.today().isoformat())
    target = datetime.strptime(d, "%Y-%m-%d").date()
    logs = get_meal_logs_for_date(target)
    return jsonify([
        {
            "id":          e.id,
            "log_date":    e.log_date.isoformat(),
            "meal_label":  e.meal_label,
            "description": e.description,
            "calories":    e.calories,
            "protein_g":   e.protein_g,
            "ai_notes":    e.ai_notes,
        }
        for e in logs
    ])


@app.route("/api/nutrition/log", methods=["POST"])
def api_add_nutrition():
    data = request.json
    try:
        d = datetime.strptime(data.get("log_date", date.today().isoformat()), "%Y-%m-%d").date()
        entry = add_meal_log(
            log_date=d,
            meal_label=data["meal_label"],
            description=data["description"],
            calories=data.get("calories"),
            protein_g=data.get("protein_g"),
            ai_notes=data.get("ai_notes"),
        )
        return jsonify({"ok": True, "id": entry.id})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/nutrition/log/<int:entry_id>", methods=["DELETE"])
def api_delete_nutrition(entry_id):
    ok = delete_meal_log(entry_id)
    return jsonify({"ok": ok})


@app.route("/api/nutrition/summary", methods=["GET"])
def api_nutrition_summary():
    d = request.args.get("date", date.today().isoformat())
    target = datetime.strptime(d, "%Y-%m-%d").date()
    s = get_daily_summary(target)
    return jsonify({
        "date":      d,
        "calories":  s["calories"],
        "protein_g": s["protein_g"],
        "meals":     len(s["entries"]),
    })


@app.route("/api/nutrition/history", methods=["GET"])
def api_nutrition_history():
    days = request.args.get("days", 7, type=int)
    hist = get_nutrition_history(days)
    return jsonify([
        {
            "date":      h["date"].isoformat(),
            "calories":  h["calories"],
            "protein_g": h["protein_g"],
            "meals":     h["meals"],
        }
        for h in hist
    ])


# ═══════════════════════════════════════════════════════════════════════════
# API: TELEGRAM
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/telegram/status", methods=["GET"])
def api_telegram_status():
    return jsonify({
        "configured": telegram_configured(),
    })


@app.route("/api/telegram/send", methods=["POST"])
def api_telegram_send():
    data = request.json
    msg_type = data.get("type", "custom")
    text = data.get("text", "")

    if msg_type == "restock":
        text = build_restock_message()
    elif msg_type == "expiry":
        text = build_expiry_message()

    if not text:
        return jsonify({"ok": False, "error": "No message text"}), 400

    ok, detail = telegram_send(text)
    return jsonify({"ok": ok, "detail": detail})


# ═══════════════════════════════════════════════════════════════════════════
# API: CAMERA SCAN
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/scan", methods=["POST"])
def api_scan():
    data = request.json
    if not data or "image" not in data:
        return jsonify({"ok": False, "error": "No image data"}), 400

    try:
        # Image is base64
        header, encoded = data["image"].split(",", 1)
        image_data = base64.b64decode(encoded)

        if not ollama_is_running():
            return jsonify({"ok": False, "error": "Ollama is not running. Start 'ollama serve' with llava model."}), 503

        detected = detect_veggies(image_data)
        return jsonify({"ok": True, "items": detected})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ═══════════════════════════════════════════════════════════════════════════
# API: DASHBOARD STATS
# ═══════════════════════════════════════════════════════════════════════════

@app.route("/api/stats", methods=["GET"])
def api_stats():
    total = session.query(Inventory).count()
    low_stock = len(get_restock_list(threshold=2))
    expiring = len(get_expiring_items(within_days=3))
    recipes = session.query(Recipe).count()
    today_summary = get_daily_summary(date.today())
    return jsonify({
        "total_items":    total,
        "low_stock":      low_stock,
        "expiring_soon":  expiring,
        "total_recipes":  recipes,
        "today_calories": today_summary["calories"],
        "today_protein":  today_summary["protein_g"],
        "today_meals":    len(today_summary["entries"]),
    })


if __name__ == "__main__":
    print("=" * 50)
    print("  Fridge Manager Web App")
    print("  Open: http://localhost:5000")
    print("=" * 50)
    app.run(debug=True, port=5000)
