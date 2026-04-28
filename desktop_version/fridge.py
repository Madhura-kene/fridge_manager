"""
fridge.py
FULL UI — all Tkinter tabs wired together.
Imports logic from:
  database.py              — models, session
  inventory.py             — CRUD, restock, expiry
  scan.py                  — camera, Ollama vision, QuantityDialog
  recipes_recommendation.py — exact match + AI suggest
  telegram_bot.py          — send messages, scheduler
  nutrition_calculator.py  — meal log, estimate, history
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from datetime import date, datetime
import threading
import numpy as np

# ── local modules ──────────────────────────────────────────────────────────
from database              import session, seed_example_data
from inventory             import (
    days_until_expiry, add_item, delete_item, update_item,
    export_inventory_csv, get_restock_list, get_expiring_items,
    get_available_ingredients,
)
from scan                  import (
    ollama_is_running, detect_veggies, pil_image_to_bytes,
    QuantityDialog, CameraScanWindow,
)
from recipes_recommendation import (
    suggest_recipes, get_all_recipes, add_recipe,
    delete_recipe_by_id, find_recipe_by_name,
    ai_recipe_suggest, ollama_is_running as recipe_ollama_check,
)
from telegram_bot          import (
    telegram_configured, telegram_send, EveningScheduler,
    build_restock_message, build_expiry_message, build_evening_prompt,
    EVENING_HOUR, EVENING_MINUTE, SCHEDULER_AVAILABLE,
)
from nutrition_calculator  import (
    ollama_is_running as nut_ollama_check,
    estimate_nutrition, add_meal_log, get_meal_logs_for_date,
    delete_meal_log, get_daily_summary, get_nutrition_history,
)

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════
# MAIN APP
# ══════════════════════════════════════════════════════════════════════════

class FridgeApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Fridge & Freezer Manager")
        self.geometry("980x680")
        self.style = ttk.Style(self)

        seed_example_data()

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # create all tabs
        self.tab_inventory = ttk.Frame(self.nb)
        self.tab_add       = ttk.Frame(self.nb)
        self.tab_scan      = ttk.Frame(self.nb)
        self.tab_restock   = ttk.Frame(self.nb)
        self.tab_expiry    = ttk.Frame(self.nb)
        self.tab_recipes   = ttk.Frame(self.nb)
        self.tab_ai        = ttk.Frame(self.nb)
        self.tab_telegram  = ttk.Frame(self.nb)
        self.tab_nutrition = ttk.Frame(self.nb)

        self.nb.add(self.tab_inventory, text="Inventory")
        self.nb.add(self.tab_add,       text="Add / Update")
        self.nb.add(self.tab_scan,      text="📷 Scan Items")
        self.nb.add(self.tab_restock,   text="Needs Restocking")
        self.nb.add(self.tab_expiry,    text="Expiry Reminders")
        self.nb.add(self.tab_recipes,   text="Recipe Suggestions")
        self.nb.add(self.tab_ai,        text="🤖 AI Recipes")
        self.nb.add(self.tab_telegram,  text="📱 Telegram")
        self.nb.add(self.tab_nutrition, text="🥗 Nutrition")

        # build each tab
        self._build_inventory_tab()
        self._build_add_tab()
        self._build_scan_tab()
        self._build_restock_tab()
        self._build_expiry_tab()
        self._build_recipes_tab()
        self._build_ai_tab()
        self._build_telegram_tab()
        self._build_nutrition_tab()

        # start evening scheduler
        self._scheduler = EveningScheduler()
        self._scheduler.start(EVENING_HOUR, EVENING_MINUTE)

        self._refresh_all()

    # ══════════════════════════════════════════════════════════════════════
    # TAB: INVENTORY
    # ══════════════════════════════════════════════════════════════════════
    def _build_inventory_tab(self):
        frame = self.tab_inventory
        top   = ttk.Frame(frame)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Button(top, text="Refresh",
                   command=self._refresh_inventory).pack(side="left")
        ttk.Button(top, text="Export CSV",
                   command=self._export_csv).pack(side="left", padx=6)
        ttk.Button(top, text="Delete Selected",
                   command=self._delete_selected_inventory).pack(side="left", padx=6)

        cols = ("id", "name", "quantity", "storage", "expiry_date", "days_left")
        self.inv_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            self.inv_tree.heading(col, text=col.title())
            self.inv_tree.column(col, width=120, anchor="center")
        self.inv_tree.column("name", width=200, anchor="w")
        self.inv_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_inventory(self):
        from database import session as db_session, Inventory
        for r in self.inv_tree.get_children():
            self.inv_tree.delete(r)
        for it in db_session.query(Inventory).all():
            dleft  = days_until_expiry(it.expiry_date)
            dl_str = "N/A" if dleft == np.inf else str(dleft)
            vals   = (it.id, it.name, it.quantity, it.storage,
                      it.expiry_date.isoformat() if it.expiry_date else "", dl_str)
            iid = self.inv_tree.insert("", "end", values=vals)
            if dleft <= 3:
                self.inv_tree.tag_configure("expiring", background="#ffcccc")
                self.inv_tree.item(iid, tags=("expiring",))

    def _delete_selected_inventory(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select an item first")
            return
        if not messagebox.askyesno("Confirm", "Delete selected items?"):
            return
        for s in sel:
            delete_item(int(self.inv_tree.item(s, "values")[0]))
        self._refresh_all()

    def _export_csv(self):
        f = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if f:
            export_inventory_csv(f)
            messagebox.showinfo("Export", f"Exported to {f}")

    # ══════════════════════════════════════════════════════════════════════
    # TAB: ADD / UPDATE
    # ══════════════════════════════════════════════════════════════════════
    def _build_add_tab(self):
        frame = self.tab_add
        frm   = ttk.Frame(frame)
        frm.pack(padx=16, pady=16, anchor="nw")

        ttk.Label(frm, text="Name:").grid(row=0, column=0, sticky="w")
        self.ent_name = ttk.Entry(frm, width=30)
        self.ent_name.grid(row=0, column=1, pady=4)

        ttk.Label(frm, text="Quantity:").grid(row=1, column=0, sticky="w")
        self.ent_qty = ttk.Entry(frm, width=10)
        self.ent_qty.grid(row=1, column=1, pady=4, sticky="w")

        ttk.Label(frm, text="Storage:").grid(row=2, column=0, sticky="w")
        self.storage_var = tk.StringVar(value="Fridge")
        ttk.Radiobutton(frm, text="Fridge",  variable=self.storage_var,
                        value="Fridge").grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(frm, text="Freezer", variable=self.storage_var,
                        value="Freezer").grid(row=2, column=1, sticky="e")

        ttk.Label(frm, text="Expiry (YYYY-MM-DD) optional:").grid(row=3, column=0, sticky="w")
        self.ent_expiry = ttk.Entry(frm, width=15)
        self.ent_expiry.grid(row=3, column=1, pady=4, sticky="w")

        ttk.Button(frm, text="Add Item",
                   command=self._handle_add_item).grid(row=4, column=0, pady=8)
        ttk.Button(frm, text="Update Selected",
                   command=self._handle_update_selected).grid(row=4, column=1, pady=8)

        ttk.Label(frame,
                  text="Select item in Inventory tab, then click Update Selected.").pack(
                  anchor="w", padx=16)

    def _handle_add_item(self):
        name    = self.ent_name.get().strip()
        qty     = self.ent_qty.get().strip()
        storage = self.storage_var.get()
        expiry  = self.ent_expiry.get().strip()
        if not name or not qty:
            messagebox.showerror("Error", "Name and quantity required")
            return
        try:
            add_item(name, int(qty), storage, expiry)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        messagebox.showinfo("Added", f"Added {name}")
        self.ent_name.delete(0, tk.END)
        self.ent_qty.delete(0, tk.END)
        self.ent_expiry.delete(0, tk.END)
        self._refresh_all()

    def _handle_update_selected(self):
        sel = self.inv_tree.selection()
        if not sel:
            messagebox.showinfo("Update", "Select an item in Inventory tab first")
            return
        item_id = int(self.inv_tree.item(sel[0], "values")[0])
        new_qty = simpledialog.askstring("Quantity", "New quantity (blank to keep):")
        new_exp = simpledialog.askstring("Expiry",   "New expiry YYYY-MM-DD (blank to clear):")
        if new_qty is None and new_exp is None:
            return
        q = int(new_qty) if new_qty and new_qty.strip() else None
        e = new_exp.strip() if new_exp is not None else None
        update_item(item_id, quantity=q, expiry_str=e)
        messagebox.showinfo("Updated", "Item updated")
        self._refresh_all()

    # ══════════════════════════════════════════════════════════════════════
    # TAB: SCAN ITEMS
    # ══════════════════════════════════════════════════════════════════════
    def _build_scan_tab(self):
        frame = self.tab_scan

        hdr = ttk.Frame(frame)
        hdr.pack(fill="x", padx=20, pady=(14, 0))
        ttk.Label(hdr, text="Scan food items into inventory",
                  font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(hdr,
                  text="Use your webcam or upload a photo — Ollama llava detects food items.",
                  foreground="gray").pack(anchor="w")

        self.scan_ollama_lbl = ttk.Label(frame, text="Checking Ollama…")
        self.scan_ollama_lbl.pack(anchor="w", padx=20, pady=(4, 0))
        self._check_ollama_async(self.scan_ollama_lbl)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(padx=20, pady=8)
        ttk.Button(btn_frame, text="📷  Open Camera",
                   command=self._open_camera,
                   width=22).grid(row=0, column=0, padx=12, ipady=10)
        ttk.Button(btn_frame, text="🖼  Upload Photo",
                   command=self._upload_photo,
                   width=22).grid(row=0, column=1, padx=12, ipady=10)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)
        ttk.Label(frame, text="Last scan result:",
                  font=("", 10, "bold")).pack(anchor="w", padx=20)
        self.scan_result_text = tk.Text(frame, height=8, state="disabled",
                                        wrap="word", font=("Courier", 10))
        self.scan_result_text.pack(fill="both", padx=20, pady=(4, 8), expand=True)

        tip = ("Tips for best results:\n"
               "  • Spread items on a clean bright surface\n"
               "  • ollama pull llava    (first time only)\n"
               "  • ollama serve         (keep running)")
        ttk.Label(frame, text=tip, foreground="gray",
                  justify="left").pack(anchor="w", padx=20, pady=(0, 12))

    def _check_ollama_async(self, label):
        def _check():
            ok  = ollama_is_running()
            msg = "✅  Ollama is running" if ok else "⚠️  Ollama not detected — run: ollama serve"
            col = "green" if ok else "orange"
            self.after(0, lambda: label.config(text=msg, foreground=col))
        threading.Thread(target=_check, daemon=True).start()

    def _set_scan_result(self, text: str):
        self.scan_result_text.config(state="normal")
        self.scan_result_text.delete("1.0", tk.END)
        self.scan_result_text.insert(tk.END, text)
        self.scan_result_text.config(state="disabled")

    def _open_camera(self):
        if not CV2_AVAILABLE:
            messagebox.showwarning("Missing", "pip install opencv-python")
            return
        CameraScanWindow(self, self._on_scan_confirmed)

    def _upload_photo(self):
        if not PIL_AVAILABLE:
            messagebox.showwarning("Missing", "pip install pillow")
            return
        path = filedialog.askopenfilename(
            title="Select a photo",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not path:
            return
        self._set_scan_result("Sending to Ollama llava…")
        self.update()

        def _worker():
            try:
                pil_img = Image.open(path).convert("RGB")
                pil_img.thumbnail((1024, 1024), Image.LANCZOS)
                img_bytes = pil_image_to_bytes(pil_img)
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Image error", str(e)))
                return
            if not ollama_is_running():
                self.after(0, lambda: messagebox.showerror(
                    "Ollama not running", "Run: ollama serve"))
                return
            detected = detect_veggies(img_bytes)
            if not detected:
                self.after(0, lambda: self._set_scan_result(
                    "Nothing detected. Try a clearer photo."))
                return
            self.after(0, lambda: [
                self._set_scan_result(
                    "Detected:\n" + "\n".join(f"  • {i}" for i in detected)),
                QuantityDialog(self, detected, self._on_scan_confirmed)
            ])

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_confirmed(self, items_to_add: list):
        if not items_to_add:
            self._set_scan_result(
                self.scan_result_text.get("1.0", tk.END).strip() + "\n\n(No items added)")
            return
        added = []
        for name, qty, storage, expiry_str in items_to_add:
            try:
                add_item(name, qty, storage, expiry_str)
                added.append(f"{name} × {qty} ({storage})")
            except Exception as e:
                messagebox.showerror("Add error", f"Could not add {name}: {e}")
        self._set_scan_result(
            "Added to inventory:\n" + "\n".join(f"  ✓ {n}" for n in added))
        self._refresh_all()
        messagebox.showinfo("Done", f"{len(added)} item(s) added!")

    # ══════════════════════════════════════════════════════════════════════
    # TAB: NEEDS RESTOCKING
    # ══════════════════════════════════════════════════════════════════════
    def _build_restock_tab(self):
        frame = self.tab_restock
        top   = ttk.Frame(frame)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Restock threshold:").pack(side="left")
        self.restock_threshold_var = tk.IntVar(value=2)
        ttk.Spinbox(top, from_=1, to=100,
                    textvariable=self.restock_threshold_var, width=5,
                    command=self._refresh_restock).pack(side="left", padx=6)
        ttk.Button(top, text="Refresh",
                   command=self._refresh_restock).pack(side="left", padx=6)

        cols = ("id", "name", "quantity", "storage")
        self.restock_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            self.restock_tree.heading(c, text=c.title())
            self.restock_tree.column(c, width=130, anchor="center")
        self.restock_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_restock(self):
        th = int(self.restock_threshold_var.get())
        for r in self.restock_tree.get_children():
            self.restock_tree.delete(r)
        for it in get_restock_list(threshold=th):
            self.restock_tree.insert("", "end",
                values=(it.id, it.name, it.quantity, it.storage))

    # ══════════════════════════════════════════════════════════════════════
    # TAB: EXPIRY REMINDERS
    # ══════════════════════════════════════════════════════════════════════
    def _build_expiry_tab(self):
        frame = self.tab_expiry
        top   = ttk.Frame(frame)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Show items expiring within (days):").pack(side="left")
        self.expiry_within_var = tk.IntVar(value=3)
        ttk.Spinbox(top, from_=0, to=365,
                    textvariable=self.expiry_within_var, width=5,
                    command=self._refresh_expiry).pack(side="left", padx=6)
        ttk.Button(top, text="Refresh",
                   command=self._refresh_expiry).pack(side="left", padx=6)

        cols = ("id", "name", "storage", "expiry_date", "days_left")
        self.expiry_tree = ttk.Treeview(frame, columns=cols, show="headings")
        for c in cols:
            self.expiry_tree.heading(c, text=c.title())
            self.expiry_tree.column(c, width=140, anchor="center")
        self.expiry_tree.pack(fill="both", expand=True, padx=8, pady=8)

    def _refresh_expiry(self):
        within = int(self.expiry_within_var.get())
        for r in self.expiry_tree.get_children():
            self.expiry_tree.delete(r)
        for it, d in get_expiring_items(within_days=within):
            self.expiry_tree.insert("", "end",
                values=(it.id, it.name, it.storage,
                        it.expiry_date.isoformat() if it.expiry_date else "", d))

    # ══════════════════════════════════════════════════════════════════════
    # TAB: RECIPE SUGGESTIONS (exact match)
    # ══════════════════════════════════════════════════════════════════════
    def _build_recipes_tab(self):
        frame = self.tab_recipes
        top   = ttk.Frame(frame)
        top.pack(fill="x", padx=8, pady=8)
        ttk.Label(top, text="Filter:").pack(side="left")
        self.recipe_filter_var = tk.StringVar(value="Both")
        ttk.Combobox(top, values=["Fridge", "Freezer", "Both"],
                     textvariable=self.recipe_filter_var,
                     state="readonly", width=10).pack(side="left", padx=6)
        ttk.Button(top, text="Refresh",
                   command=self._refresh_recipes).pack(side="left", padx=6)

        self.recipe_listbox = tk.Listbox(frame)
        self.recipe_listbox.pack(fill="both", expand=True, padx=8, pady=8)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", padx=8, pady=8)
        ttk.Button(btn_frame, text="Show Ingredients",
                   command=self._show_recipe_ingredients).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Add Recipe",
                   command=self._add_recipe_dialog).pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Delete Recipe",
                   command=self._delete_recipe_dialog).pack(side="left", padx=6)

    def _refresh_recipes(self):
        flt         = self.recipe_filter_var.get()
        suggestions = suggest_recipes(filter_storage=flt)
        self.recipe_listbox.delete(0, tk.END)
        for dish, _ in suggestions:
            self.recipe_listbox.insert(tk.END, dish)
        if not suggestions:
            for r in get_all_recipes():
                self.recipe_listbox.insert(tk.END, f"{r.dish} (missing ingredients)")

    def _show_recipe_ingredients(self):
        sel = self.recipe_listbox.curselection()
        if not sel:
            messagebox.showinfo("Recipe", "Select a recipe")
            return
        name = self.recipe_listbox.get(sel[0])
        r = find_recipe_by_name(name)
        if r:
            messagebox.showinfo(r.dish, f"Ingredients: {r.ingredients}")
        else:
            messagebox.showinfo("Recipe", "Recipe not found")

    def _add_recipe_dialog(self):
        dish = simpledialog.askstring("New Recipe", "Recipe name:")
        if not dish:
            return
        ing = simpledialog.askstring("Ingredients",
                                     "Comma-separated (e.g. eggs,tomato,butter):")
        if not ing:
            return
        add_recipe(dish, ing)
        messagebox.showinfo("Added", f"Added {dish}")
        self._refresh_recipes()

    def _delete_recipe_dialog(self):
        sel = self.recipe_listbox.curselection()
        if not sel:
            messagebox.showinfo("Delete", "Select a recipe first")
            return
        name = self.recipe_listbox.get(sel[0])
        r = find_recipe_by_name(name)
        if not r:
            messagebox.showerror("Error", "Recipe not found")
            return
        session.delete(r)
        session.commit()
        messagebox.showinfo("Deleted", f"Deleted {r.dish}")
        self._refresh_recipes()

    # ══════════════════════════════════════════════════════════════════════
    # TAB: AI RECIPES (Ollama llama3)
    # ══════════════════════════════════════════════════════════════════════
    def _build_ai_tab(self):
        frame = self.tab_ai

        hdr = ttk.Frame(frame)
        hdr.pack(fill="x", padx=20, pady=(14, 0))
        ttk.Label(hdr, text="AI Recipe Suggestions",
                  font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(hdr,
                  text="Ollama llama3 checks your inventory against every recipe in the DB.\n"
                       "It will never suggest a recipe not saved in the system.",
                  foreground="gray", justify="left").pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)

        ctrl = ttk.Frame(frame)
        ctrl.pack(fill="x", padx=20, pady=4)
        ttk.Label(ctrl, text="Use ingredients from:").pack(side="left")
        self.ai_filter_var = tk.StringVar(value="Both")
        ttk.Combobox(ctrl, values=["Fridge", "Freezer", "Both"],
                     textvariable=self.ai_filter_var,
                     state="readonly", width=10).pack(side="left", padx=8)
        self.ai_ask_btn = ttk.Button(ctrl, text="Ask AI  ▶",
                                     command=self._run_ai_recipes)
        self.ai_ask_btn.pack(side="left", padx=8)
        self.ai_status_lbl = ttk.Label(ctrl, text="", foreground="gray")
        self.ai_status_lbl.pack(side="left", padx=8)

        ttk.Label(frame, text="Ingredients being sent to AI:",
                  font=("", 10, "bold")).pack(anchor="w", padx=20, pady=(8, 0))
        self.ai_inventory_lbl = ttk.Label(frame, text="", foreground="gray",
                                          wraplength=920, justify="left")
        self.ai_inventory_lbl.pack(anchor="w", padx=20, pady=(2, 6))

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=4)
        ttk.Label(frame, text="AI response:",
                  font=("", 10, "bold")).pack(anchor="w", padx=20)

        res_frame = ttk.Frame(frame)
        res_frame.pack(fill="both", expand=True, padx=20, pady=(4, 16))
        self.ai_result_text = tk.Text(res_frame, wrap="word", font=("Courier", 11),
                                      state="disabled", relief="flat", borderwidth=1)
        sb = ttk.Scrollbar(res_frame, command=self.ai_result_text.yview)
        self.ai_result_text.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.ai_result_text.pack(side="left", fill="both", expand=True)

        self.ai_result_text.tag_configure(
            "section", font=("Courier", 12, "bold"), foreground="#1a5276")
        self.ai_result_text.tag_configure(
            "ready",   font=("Courier", 11), foreground="#1a7a1a")
        self.ai_result_text.tag_configure(
            "almost",  font=("Courier", 11), foreground="#7d6608")
        self.ai_result_text.tag_configure(
            "normal",  font=("Courier", 11))

        self.ai_filter_var.trace_add("write",
            lambda *_: self._update_ai_inventory_label())
        self._update_ai_inventory_label()

    def _update_ai_inventory_label(self):
        items = get_available_ingredients(self.ai_filter_var.get())
        self.ai_inventory_lbl.config(
            text=", ".join(items) if items else "(no items in inventory)",
            foreground="gray" if items else "red")

    def _set_ai_result(self, text: str):
        self.ai_result_text.config(state="normal")
        self.ai_result_text.delete("1.0", tk.END)
        in_almost = False
        for line in text.splitlines():
            up = line.strip().upper()
            if "READY TO COOK" in up or "ALMOST READY" in up:
                in_almost = "ALMOST" in up
                self.ai_result_text.insert(tk.END, line + "\n", "section")
            elif line.strip() in ("", "NONE"):
                self.ai_result_text.insert(tk.END, line + "\n", "normal")
            elif in_almost:
                self.ai_result_text.insert(tk.END, line + "\n", "almost")
            else:
                self.ai_result_text.insert(tk.END, line + "\n", "ready")
        self.ai_result_text.config(state="disabled")

    def _run_ai_recipes(self):
        available = get_available_ingredients(self.ai_filter_var.get())
        if not available:
            messagebox.showwarning("No ingredients",
                                   "Inventory is empty or all quantities are zero.")
            return
        self._update_ai_inventory_label()
        self.ai_ask_btn.config(state="disabled")
        self.ai_status_lbl.config(text="⏳  Asking Ollama llama3…", foreground="gray")
        self._set_ai_result("Sending to Ollama llama3… (10–30 seconds)\nUI stays responsive.")
        self.update()
        flt = self.ai_filter_var.get()

        def _worker():
            if not recipe_ollama_check():
                msg = "Ollama not running.\nRun: ollama serve\nPull: ollama pull llama3"
                self.after(0, lambda: self._on_ai_done(msg, error=True))
                return
            result = ai_recipe_suggest(available, flt)
            self.after(0, lambda: self._on_ai_done(result))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_ai_done(self, result: str, error: bool = False):
        self.ai_ask_btn.config(state="normal")
        if error:
            self.ai_status_lbl.config(text="⚠️  Not reachable", foreground="orange")
        else:
            self.ai_status_lbl.config(text="✅  Done", foreground="green")
            self.after(4000, lambda: self.ai_status_lbl.config(
                text="", foreground="gray"))
        self._set_ai_result(result)

    # ══════════════════════════════════════════════════════════════════════
    # TAB: TELEGRAM
    # ══════════════════════════════════════════════════════════════════════
    def _build_telegram_tab(self):
        frame = self.tab_telegram

        hdr = ttk.Frame(frame)
        hdr.pack(fill="x", padx=20, pady=(14, 0))
        ttk.Label(hdr, text="Telegram Alerts",
                  font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(hdr,
                  text="Send restock list and expiry warnings to your phone.",
                  foreground="gray").pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)

        cfg_lf = ttk.LabelFrame(frame, text="  Configuration  ")
        cfg_lf.pack(fill="x", padx=20, pady=4)
        if telegram_configured():
            cfg_text = "✅  Telegram is configured."
            cfg_col  = "green"
        else:
            cfg_text = (
                "⚠️  Not configured.\n"
                "Open telegram_bot.py and fill in:\n"
                "  TELEGRAM_TOKEN   = \"your_token\"\n"
                "  TELEGRAM_CHAT_ID = \"your_chat_id\""
            )
            cfg_col = "orange"
        ttk.Label(cfg_lf, text=cfg_text, foreground=cfg_col,
                  justify="left").pack(anchor="w", padx=12, pady=8)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)
        ttk.Label(frame, text="Send now:", font=("", 10, "bold")).pack(anchor="w", padx=20)

        row1 = ttk.Frame(frame)
        row1.pack(fill="x", padx=20, pady=2)
        ttk.Label(row1, text="Restock threshold:").pack(side="left")
        self.tg_restock_var = tk.IntVar(value=2)
        ttk.Spinbox(row1, from_=1, to=50, textvariable=self.tg_restock_var,
                    width=4).pack(side="left", padx=4)
        ttk.Button(row1, text="📱 Send Restock List",
                   command=lambda: self._tg_dispatch(
                       build_restock_message(self.tg_restock_var.get()),
                       "Restock list"),
                   width=22).pack(side="left", padx=12)

        row2 = ttk.Frame(frame)
        row2.pack(fill="x", padx=20, pady=2)
        ttk.Label(row2, text="Expiry within (days):").pack(side="left")
        self.tg_expiry_var = tk.IntVar(value=3)
        ttk.Spinbox(row2, from_=0, to=30, textvariable=self.tg_expiry_var,
                    width=4).pack(side="left", padx=4)
        ttk.Button(row2, text="📱 Send Expiry Warning",
                   command=lambda: self._tg_dispatch(
                       build_expiry_message(self.tg_expiry_var.get()),
                       "Expiry warning"),
                   width=22).pack(side="left", padx=12)

        row3 = ttk.Frame(frame)
        row3.pack(fill="x", padx=20, pady=2)
        ttk.Button(row3, text="📱 Send Test Message",
                   command=lambda: self._tg_dispatch(
                       "🧪 Test from Fridge Manager!", "Test"),
                   width=22).pack(side="left")
        ttk.Button(row3, text="📱 Send Evening Prompt Now",
                   command=lambda: self._tg_dispatch(
                       build_evening_prompt(), "Evening prompt"),
                   width=26).pack(side="left", padx=12)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)
        ttk.Label(frame, text="Daily evening reminder:",
                  font=("", 10, "bold")).pack(anchor="w", padx=20)

        sched_row = ttk.Frame(frame)
        sched_row.pack(fill="x", padx=20, pady=2)
        ttk.Label(sched_row, text="Send at:").pack(side="left")
        self.tg_hour_var   = tk.IntVar(value=EVENING_HOUR)
        self.tg_minute_var = tk.IntVar(value=EVENING_MINUTE)
        ttk.Spinbox(sched_row, from_=0, to=23, textvariable=self.tg_hour_var,
                    width=4, format="%02.0f").pack(side="left", padx=4)
        ttk.Label(sched_row, text=":").pack(side="left")
        ttk.Spinbox(sched_row, from_=0, to=59, textvariable=self.tg_minute_var,
                    width=4, format="%02.0f").pack(side="left", padx=4)
        ttk.Label(sched_row, text="(24h)").pack(side="left", padx=4)
        ttk.Button(sched_row, text="Apply",
                   command=self._reschedule_evening).pack(side="left", padx=8)

        self.sched_status_lbl = ttk.Label(frame, text="", foreground="gray")
        self.sched_status_lbl.pack(anchor="w", padx=20, pady=2)
        self._update_sched_status()

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)
        ttk.Label(frame, text="Send log:", font=("", 10, "bold")).pack(anchor="w", padx=20)
        self.tg_log_text = tk.Text(frame, height=6, state="disabled",
                                   wrap="word", font=("Courier", 10))
        self.tg_log_text.pack(fill="both", padx=20, pady=(2, 12), expand=True)

    def _tg_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.tg_log_text.config(state="normal")
        self.tg_log_text.insert(tk.END, f"[{ts}] {msg}\n")
        self.tg_log_text.see(tk.END)
        self.tg_log_text.config(state="disabled")

    def _tg_dispatch(self, message: str, label: str):
        self._tg_log(f"Sending: {label}…")
        def _worker():
            ok, detail = telegram_send(message)
            result = f"{label} → {'✅ OK' if ok else '❌ FAILED'}: {detail}"
            self.after(0, lambda: self._tg_log(result))
        threading.Thread(target=_worker, daemon=True).start()

    def _reschedule_evening(self):
        h = int(self.tg_hour_var.get())
        m = int(self.tg_minute_var.get())
        self._scheduler.reschedule(h, m)
        self._update_sched_status()
        messagebox.showinfo("Schedule updated",
                            f"Evening reminder set for {h:02d}:{m:02d} daily.")

    def _update_sched_status(self):
        if not SCHEDULER_AVAILABLE:
            self.sched_status_lbl.config(
                text="⚠️  apscheduler not installed.  pip install apscheduler",
                foreground="orange")
            return
        h = int(self.tg_hour_var.get())
        m = int(self.tg_minute_var.get())
        self.sched_status_lbl.config(
            text=f"⏰  Reminder scheduled daily at {h:02d}:{m:02d}",
            foreground="green" if telegram_configured() else "gray")

    # ══════════════════════════════════════════════════════════════════════
    # TAB: NUTRITION TRACKER
    # ══════════════════════════════════════════════════════════════════════
    def _build_nutrition_tab(self):
        frame = self.tab_nutrition

        hdr = ttk.Frame(frame)
        hdr.pack(fill="x", padx=20, pady=(14, 0))
        ttk.Label(hdr, text="Nutrition Tracker",
                  font=("", 13, "bold")).pack(anchor="w")
        ttk.Label(hdr, text="Log what you eat. Ollama estimates calories & protein.",
                  foreground="gray").pack(anchor="w")

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=8)

        entry_lf = ttk.LabelFrame(frame, text="  Log a meal  ")
        entry_lf.pack(fill="x", padx=20, pady=4)

        form = ttk.Frame(entry_lf)
        form.pack(padx=12, pady=8, fill="x")

        ttk.Label(form, text="Date (YYYY-MM-DD):").grid(row=0, column=0, sticky="w", pady=3)
        self.nut_date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(form, textvariable=self.nut_date_var, width=14).grid(
            row=0, column=1, sticky="w", padx=8)
        ttk.Button(form, text="Today",
                   command=lambda: self.nut_date_var.set(date.today().isoformat()),
                   width=6).grid(row=0, column=2, sticky="w")

        ttk.Label(form, text="Meal:").grid(row=1, column=0, sticky="w", pady=3)
        self.nut_label_var = tk.StringVar(value="Lunch")
        ttk.Combobox(form, textvariable=self.nut_label_var,
                     values=["Breakfast", "Lunch", "Dinner", "Snack", "Other"],
                     state="readonly", width=12).grid(row=1, column=1, sticky="w", padx=8)

        ttk.Label(form, text="What you ate:").grid(row=2, column=0, sticky="nw", pady=3)
        self.nut_desc_text = tk.Text(form, width=48, height=3, wrap="word")
        self.nut_desc_text.grid(row=2, column=1, columnspan=2, sticky="w", padx=8, pady=3)
        ttk.Label(form, text="e.g.  2 rotis, dal tadka, rice, salad",
                  foreground="gray").grid(row=3, column=1, columnspan=2, sticky="w", padx=8)

        btn_row = ttk.Frame(entry_lf)
        btn_row.pack(pady=(4, 10))
        self.nut_log_btn = ttk.Button(btn_row, text="Log + Ask AI  ▶",
                                      command=self._nut_log_and_estimate, width=20)
        self.nut_log_btn.pack(side="left", padx=6)
        ttk.Button(btn_row, text="Log without AI",
                   command=self._nut_log_no_ai, width=18).pack(side="left", padx=6)
        self.nut_ai_status = ttk.Label(btn_row, text="", foreground="gray")
        self.nut_ai_status.pack(side="left", padx=8)

        ttk.Separator(frame, orient="horizontal").pack(fill="x", padx=20, pady=6)

        panes = ttk.Frame(frame)
        panes.pack(fill="both", expand=True, padx=20, pady=(0, 12))

        # Left: today
        left = ttk.LabelFrame(panes, text="  Today's meals  ")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        ctrl = ttk.Frame(left)
        ctrl.pack(fill="x", padx=8, pady=4)
        ttk.Button(ctrl, text="Refresh",
                   command=self._nut_refresh_today).pack(side="left")
        ttk.Button(ctrl, text="Delete selected",
                   command=self._nut_delete_selected).pack(side="left", padx=6)

        self.nut_summary_lbl = ttk.Label(left, text="",
                                         font=("", 10, "bold"), foreground="#1a5276")
        self.nut_summary_lbl.pack(anchor="w", padx=8)

        cols = ("id", "meal", "description", "cal", "protein")
        self.nut_tree = ttk.Treeview(left, columns=cols, show="headings", height=6)
        self.nut_tree.heading("id",          text="ID")
        self.nut_tree.heading("meal",        text="Meal")
        self.nut_tree.heading("description", text="Description")
        self.nut_tree.heading("cal",         text="kcal")
        self.nut_tree.heading("protein",     text="Protein g")
        self.nut_tree.column("id",          width=30,  anchor="center")
        self.nut_tree.column("meal",        width=70,  anchor="center")
        self.nut_tree.column("description", width=200, anchor="w")
        self.nut_tree.column("cal",         width=55,  anchor="center")
        self.nut_tree.column("protein",     width=70,  anchor="center")
        self.nut_tree.pack(fill="both", expand=True, padx=8, pady=4)

        # Right: 7-day history
        right = ttk.LabelFrame(panes, text="  7-day history  ")
        right.pack(side="left", fill="both", expand=True)
        ttk.Button(right, text="Refresh history",
                   command=self._nut_refresh_history).pack(anchor="w", padx=8, pady=4)

        hist_cols = ("date", "meals", "calories", "protein")
        self.nut_hist_tree = ttk.Treeview(right, columns=hist_cols,
                                          show="headings", height=8)
        self.nut_hist_tree.heading("date",     text="Date")
        self.nut_hist_tree.heading("meals",    text="Meals")
        self.nut_hist_tree.heading("calories", text="kcal")
        self.nut_hist_tree.heading("protein",  text="Protein g")
        for c in hist_cols:
            self.nut_hist_tree.column(c, width=80, anchor="center")
        self.nut_hist_tree.column("date", width=100)
        self.nut_hist_tree.pack(fill="both", expand=True, padx=8, pady=4)

        self._nut_refresh_today()
        self._nut_refresh_history()

    def _nut_get_form(self):
        try:
            log_date = datetime.strptime(
                self.nut_date_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            messagebox.showerror("Date error", "Date must be YYYY-MM-DD")
            return None
        desc = self.nut_desc_text.get("1.0", tk.END).strip()
        if not desc:
            messagebox.showwarning("Empty", "Please describe what you ate.")
            return None
        return log_date, self.nut_label_var.get() or "Other", desc

    def _nut_log_no_ai(self):
        data = self._nut_get_form()
        if not data:
            return
        log_date, label, desc = data
        add_meal_log(log_date, label, desc)
        self.nut_desc_text.delete("1.0", tk.END)
        self._nut_refresh_today()
        self._nut_refresh_history()
        messagebox.showinfo("Logged", f"{label} logged (no AI estimate).")

    def _nut_log_and_estimate(self):
        data = self._nut_get_form()
        if not data:
            return
        log_date, label, desc = data
        self.nut_log_btn.config(state="disabled")
        self.nut_ai_status.config(text="⏳ Estimating…", foreground="gray")
        self.update()

        def _worker():
            if not nut_ollama_check():
                entry = add_meal_log(log_date, label, desc)
                self.after(0, lambda: self._nut_on_done(
                    entry, "Ollama not running — logged without estimate."))
                return
            result = estimate_nutrition(label, desc)
            entry  = add_meal_log(
                log_date, label, desc,
                calories  = result["calories"]  if not result["error"] else None,
                protein_g = result["protein_g"] if not result["error"] else None,
                ai_notes  = result["ai_notes"]  if not result["error"] else result["error"],
            )
            self.after(0, lambda: self._nut_on_done(entry, result["error"]))

        threading.Thread(target=_worker, daemon=True).start()

    def _nut_on_done(self, entry, error=None):
        self.nut_log_btn.config(state="normal")
        if error:
            self.nut_ai_status.config(
                text=f"⚠️ {str(error)[:60]}", foreground="orange")
        else:
            self.nut_ai_status.config(
                text=f"✅ ~{entry.calories:.0f} kcal  |  ~{entry.protein_g:.1f}g protein",
                foreground="green")
            self.after(6000, lambda: self.nut_ai_status.config(
                text="", foreground="gray"))
        self.nut_desc_text.delete("1.0", tk.END)
        self._nut_refresh_today()
        self._nut_refresh_history()

    def _nut_refresh_today(self):
        try:
            target = datetime.strptime(
                self.nut_date_var.get().strip(), "%Y-%m-%d").date()
        except ValueError:
            target = date.today()
        for r in self.nut_tree.get_children():
            self.nut_tree.delete(r)
        summ = get_daily_summary(target)
        for e in summ["entries"]:
            self.nut_tree.insert("", "end", values=(
                e.id, e.meal_label,
                e.description[:50] + ("…" if len(e.description) > 50 else ""),
                f"{e.calories:.0f}"  if e.calories  is not None else "—",
                f"{e.protein_g:.1f}" if e.protein_g is not None else "—",
            ))
        self.nut_summary_lbl.config(
            text=f"Total {target}:   {summ['calories']:.0f} kcal    |    "
                 f"{summ['protein_g']:.1f} g protein")

    def _nut_delete_selected(self):
        sel = self.nut_tree.selection()
        if not sel:
            messagebox.showinfo("Delete", "Select a meal entry first.")
            return
        if not messagebox.askyesno("Confirm", "Delete selected entry?"):
            return
        for s in sel:
            delete_meal_log(int(self.nut_tree.item(s, "values")[0]))
        self._nut_refresh_today()
        self._nut_refresh_history()

    def _nut_refresh_history(self):
        for r in self.nut_hist_tree.get_children():
            self.nut_hist_tree.delete(r)
        for day in get_nutrition_history(days=7):
            self.nut_hist_tree.insert("", "end", values=(
                day["date"].strftime("%a %d %b"),
                day["meals"],
                f"{day['calories']:.0f}" if day["calories"] else "—",
                f"{day['protein_g']:.1f}" if day["protein_g"] else "—",
            ))

    # ══════════════════════════════════════════════════════════════════════
    # SHARED REFRESH — called after any data change
    # ══════════════════════════════════════════════════════════════════════
    def _refresh_all(self):
        self._refresh_inventory()
        self._refresh_restock()
        self._refresh_expiry()
        self._refresh_recipes()
        self._update_ai_inventory_label()
