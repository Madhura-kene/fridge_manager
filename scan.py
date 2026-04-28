"""
scan.py
Camera scan + Ollama llava vision detection.
Handles:
  - ollama_is_running()
  - detect_veggies(image_bytes)
  - pil_image_to_bytes()
  - QuantityDialog  (Tkinter popup to confirm detected items)
  - CameraScanWindow (live webcam preview)
Imported by fridge.py for the Scan Items tab.
"""

import base64
import io
import os
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

# ── Config (loaded from .env) ─────────────────────────────────────────────────
OLLAMA_URL          = os.getenv("OLLAMA_URL",          "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "llava")


# ══════════════════════════════════════════════════════════════════════════
# OLLAMA HELPERS
# ══════════════════════════════════════════════════════════════════════════

def ollama_is_running() -> bool:
    if not REQUESTS_AVAILABLE:
        return False
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
        return r.status_code == 200
    except Exception:
        return False


def detect_veggies(image_bytes: bytes) -> list:
    """Send image to llava. Return list of detected food item names."""
    if not REQUESTS_AVAILABLE:
        return []
    b64 = base64.b64encode(image_bytes).decode()
    payload = {
        "model": OLLAMA_VISION_MODEL,
        "prompt": (
            "Look at this image carefully. "
            "List ONLY the food items, vegetables, fruits, or grocery ingredients you can see. "
            "Return a simple comma-separated list and nothing else. "
            "Example: tomato, eggs, milk, spinach\n"
            "If you see no food items, return: none"
        ),
        "images": [b64],
        "stream": False,
    }
    try:
        resp = requests.post(f"{OLLAMA_URL}/api/generate",
                             json=payload, timeout=90)
        resp.raise_for_status()
        text = resp.json().get("response", "").strip().lower()
        if text == "none" or not text:
            return []
        items = []
        for part in text.split(","):
            clean = part.strip().strip(".-*\n ")
            if clean and len(clean) < 50:
                items.append(clean)
        return items
    except Exception as e:
        print(f"[scan.py vision error] {e}")
        return []


def pil_image_to_bytes(pil_img, fmt="JPEG") -> bytes:
    buf = io.BytesIO()
    pil_img.save(buf, format=fmt)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════
# QUANTITY CONFIRMATION DIALOG
# ══════════════════════════════════════════════════════════════════════════

class QuantityDialog(tk.Toplevel):
    """
    Shows detected items one by one.
    User confirms name, quantity, storage, optional expiry.
    Calls on_done_callback(list_of_tuples) when finished.
    """
    def __init__(self, parent, detected_items: list, on_done_callback):
        super().__init__(parent)
        self.title("Confirm Detected Items")
        self.geometry("420x330")
        self.resizable(False, False)
        self.grab_set()

        self.items   = detected_items[:]
        self.idx     = 0
        self.on_done = on_done_callback
        self.to_add  = []

        ttk.Label(self, text="Confirm each detected item",
                  font=("", 11, "bold")).pack(pady=(16, 2))
        self.progress_lbl = ttk.Label(self, text="", foreground="gray")
        self.progress_lbl.pack()

        frm = ttk.Frame(self)
        frm.pack(padx=24, pady=10, fill="x")

        ttk.Label(frm, text="Item name:").grid(row=0, column=0, sticky="w", pady=4)
        self.name_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.name_var, width=26).grid(row=0, column=1, sticky="w")

        ttk.Label(frm, text="Quantity:").grid(row=1, column=0, sticky="w", pady=4)
        self.qty_var = tk.IntVar(value=1)
        ttk.Spinbox(frm, from_=1, to=999, textvariable=self.qty_var,
                    width=6).grid(row=1, column=1, sticky="w")

        ttk.Label(frm, text="Storage:").grid(row=2, column=0, sticky="w", pady=4)
        self.storage_var = tk.StringVar(value="Fridge")
        sf = ttk.Frame(frm)
        sf.grid(row=2, column=1, sticky="w")
        ttk.Radiobutton(sf, text="Fridge",  variable=self.storage_var,
                        value="Fridge").pack(side="left")
        ttk.Radiobutton(sf, text="Freezer", variable=self.storage_var,
                        value="Freezer").pack(side="left", padx=8)

        ttk.Label(frm, text="Expiry (YYYY-MM-DD):").grid(row=3, column=0, sticky="w", pady=4)
        self.expiry_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.expiry_var, width=14).grid(row=3, column=1, sticky="w")

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=8)
        ttk.Button(btn_row, text="Add  →",    command=self._add,    width=10).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Skip  →",   command=self._skip,   width=10).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Cancel all",command=self._cancel, width=10).pack(side="left", padx=4)

        self._load_item()

    def _load_item(self):
        if self.idx >= len(self.items):
            self._finish()
            return
        self.progress_lbl.config(text=f"Item {self.idx + 1} of {len(self.items)}")
        self.name_var.set(self.items[self.idx].title())
        self.qty_var.set(1)
        self.storage_var.set("Fridge")
        self.expiry_var.set("")

    def _add(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Required", "Please enter a name.", parent=self)
            return
        self.to_add.append((name, int(self.qty_var.get()),
                            self.storage_var.get(), self.expiry_var.get().strip()))
        self.idx += 1
        self._load_item()

    def _skip(self):
        self.idx += 1
        self._load_item()

    def _cancel(self):
        self.to_add = []
        self.destroy()
        self.on_done([])

    def _finish(self):
        results = self.to_add[:]
        self.destroy()
        self.on_done(results)


# ══════════════════════════════════════════════════════════════════════════
# CAMERA SCAN WINDOW
# ══════════════════════════════════════════════════════════════════════════

class CameraScanWindow(tk.Toplevel):
    """
    Live webcam preview at ~33fps.
    Capture & Scan → sends frame to Ollama llava in background thread
    → detected items go to QuantityDialog.
    """
    PREVIEW_W = 480
    PREVIEW_H = 360

    def __init__(self, parent, on_items_confirmed):
        super().__init__(parent)
        self.title("Camera Scan — Veggie Detector")
        self.geometry(f"{self.PREVIEW_W + 40}x{self.PREVIEW_H + 160}")
        self.resizable(False, False)
        self.grab_set()

        self.on_items_confirmed = on_items_confirmed
        self.cap       = None
        self._running  = False
        self._after_id = None

        self.canvas = tk.Canvas(self, width=self.PREVIEW_W,
                                height=self.PREVIEW_H, bg="black")
        self.canvas.pack(padx=20, pady=(16, 8))
        self.status_lbl = ttk.Label(self, text="Starting camera…")
        self.status_lbl.pack()

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=8)
        self.capture_btn = ttk.Button(btn_row, text="Capture & Scan",
                                      command=self._capture_and_scan,
                                      state="disabled")
        self.capture_btn.pack(side="left", padx=8)
        ttk.Button(btn_row, text="Close",
                   command=self._close).pack(side="left", padx=8)
        self.protocol("WM_DELETE_WINDOW", self._close)

        if not CV2_AVAILABLE:
            self.status_lbl.config(text="opencv-python not installed.\npip install opencv-python")
            return
        if not PIL_AVAILABLE:
            self.status_lbl.config(text="Pillow not installed.\npip install pillow")
            return
        self._start_camera()

    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.status_lbl.config(text="No camera found. Use 'Upload Photo' instead.")
            return
        self._running = True
        self.capture_btn.config(state="normal")
        self.status_lbl.config(text="Camera ready — point at your fridge contents")
        self._update_preview()

    def _update_preview(self):
        if not self._running or self.cap is None:
            return
        ret, frame = self.cap.read()
        if ret:
            rgb  = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil  = Image.fromarray(rgb).resize(
                (self.PREVIEW_W, self.PREVIEW_H), Image.LANCZOS)
            self._tk_img = ImageTk.PhotoImage(pil)
            self.canvas.create_image(0, 0, anchor="nw", image=self._tk_img)
        self._after_id = self.after(30, self._update_preview)

    def _capture_and_scan(self):
        ret, frame = self.cap.read()
        if not ret:
            messagebox.showerror("Error", "Could not read from camera.", parent=self)
            return
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
        self.capture_btn.config(state="disabled")
        self.status_lbl.config(text="Scanning with Ollama llava… please wait")
        self.update()

        rgb       = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img_bytes = pil_image_to_bytes(Image.fromarray(rgb))

        def _worker():
            if not ollama_is_running():
                self.after(0, lambda: self._on_error(
                    "Ollama is not running.\nRun: ollama serve"))
                return
            detected = detect_veggies(img_bytes)
            self.after(0, lambda: self._on_done(detected))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_done(self, detected: list):
        self._close_camera()
        if not detected:
            messagebox.showinfo("Nothing detected",
                                "No food items found. Try better lighting.",
                                parent=self)
            self.destroy()
            return
        QuantityDialog(self.master, detected, self.on_items_confirmed)
        self.destroy()

    def _on_error(self, msg: str):
        self._close_camera()
        messagebox.showerror("Scan error", msg, parent=self)
        self.destroy()

    def _close_camera(self):
        self._running = False
        if self._after_id:
            self.after_cancel(self._after_id)
        if self.cap:
            self.cap.release()
            self.cap = None

    def _close(self):
        self._close_camera()
        self.destroy()
