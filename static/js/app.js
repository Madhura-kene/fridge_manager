/* ═══════════════════════════════════════════════════════════════════════
   Fridge Manager — Client-Side Application Logic
   ═══════════════════════════════════════════════════════════════════════ */

// ── State ────────────────────────────────────────────────────────────
let currentTab = 'dashboard';
let stats = {};

// ── Init ─────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  loadDashboard();
  startClock();
  initCursor();
});

function initCursor() {
  const cursor = document.getElementById('custom-cursor');
  const dot = document.getElementById('cursor-dot');
  if (!cursor || !dot) return;

  document.addEventListener('mousemove', e => {
    cursor.style.left = e.clientX + 'px';
    cursor.style.top = e.clientY + 'px';
    dot.style.left = e.clientX + 'px';
    dot.style.top = e.clientY + 'px';
  });

  // Hover effect for all interactive elements
  const addHover = () => cursor.classList.add('hover');
  const removeHover = () => cursor.classList.remove('hover');

  const updateHoverables = () => {
    document.querySelectorAll('button, a, input, select, textarea, .tab-btn, .action-card').forEach(el => {
      el.removeEventListener('mouseenter', addHover);
      el.removeEventListener('mouseleave', removeHover);
      el.addEventListener('mouseenter', addHover);
      el.addEventListener('mouseleave', removeHover);
    });
  };

  updateHoverables();
  
  // Re-run whenever content changes (tabs, modals)
  const observer = new MutationObserver(updateHoverables);
  observer.observe(document.body, { childList: true, subtree: true });
}

// ═══════════════════════════════════════════════════════════════════════
// TABS
// ═══════════════════════════════════════════════════════════════════════

function initTabs() {
  document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });
}

function switchTab(tab) {
  currentTab = tab;

  // Update nav
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelector(`.tab-btn[data-tab="${tab}"]`)?.classList.add('active');

  // Update panels
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById(`tab-${tab}`)?.classList.add('active');

  // Load data for the tab
  const loaders = {
    dashboard:  loadDashboard,
    inventory:  loadInventory,
    restock:    loadRestock,
    expiry:     loadExpiry,
    recipes:    loadRecipes,
    nutrition:  loadNutrition,
  };
  if (loaders[tab]) loaders[tab]();
}

// ═══════════════════════════════════════════════════════════════════════
// CLOCK
// ═══════════════════════════════════════════════════════════════════════

function startClock() {
  const el = document.getElementById('header-time');
  if (!el) return;
  const update = () => {
    const now = new Date();
    el.textContent = now.toLocaleDateString('en-US', {
      weekday: 'short', month: 'short', day: 'numeric'
    }) + '  ' + now.toLocaleTimeString('en-US', {
      hour: '2-digit', minute: '2-digit'
    });
  };
  update();
  setInterval(update, 30000);
}

// ═══════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATIONS
// ═══════════════════════════════════════════════════════════════════════

function toast(message, type = 'success') {
  const container = document.getElementById('toast-container');
  const icons = { success: '', error: '', info: '' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(el);
  setTimeout(() => {
    el.classList.add('leaving');
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ═══════════════════════════════════════════════════════════════════════
// MODAL HELPERS
// ═══════════════════════════════════════════════════════════════════════

function openModal(id) {
  document.getElementById(id)?.classList.add('active');
}

function closeModal(id) {
  document.getElementById(id)?.classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('click', e => {
  if (e.target.classList.contains('modal-overlay')) {
    e.target.classList.remove('active');
  }
});

// ═══════════════════════════════════════════════════════════════════════
// API HELPERS
// ═══════════════════════════════════════════════════════════════════════

async function api(endpoint, options = {}) {
  try {
    const res = await fetch(endpoint, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    return await res.json();
  } catch (err) {
    toast('Network error: ' + err.message, 'error');
    return null;
  }
}

// ═══════════════════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════════════════

async function loadDashboard() {
  const data = await api('/api/stats');
  if (!data) return;
  stats = data;

  document.getElementById('stat-total').textContent      = data.total_items;
  document.getElementById('stat-lowstock').textContent    = data.low_stock;
  document.getElementById('stat-expiring').textContent    = data.expiring_soon;
  document.getElementById('stat-recipes').textContent     = data.total_recipes;
  document.getElementById('stat-calories').textContent    = Math.round(data.today_calories);
  document.getElementById('stat-protein').textContent     = Math.round(data.today_protein) + 'g';

  // Update badges
  const expiryBadge = document.getElementById('badge-expiring');
  if (expiryBadge) expiryBadge.textContent = data.expiring_soon;
  if (expiryBadge) expiryBadge.style.display = data.expiring_soon > 0 ? 'inline' : 'none';

  const restockBadge = document.getElementById('badge-restock');
  if (restockBadge) restockBadge.textContent = data.low_stock;
  if (restockBadge) restockBadge.style.display = data.low_stock > 0 ? 'inline' : 'none';

  // Load recent expiring for dashboard quick-view
  const expiring = await api('/api/expiring?days=5');
  const quickList = document.getElementById('dash-expiring-list');
  if (quickList && expiring) {
    if (expiring.length === 0) {
      quickList.innerHTML = '<div class="empty-state"><div class="empty-text">Nothing expiring soon!</div></div>';
    } else {
      quickList.innerHTML = expiring.slice(0, 5).map(it => `
        <div class="meal-entry">
          <div>
            <strong>${esc(it.name)}</strong>
            <div class="meal-desc">${storageBadge(it.storage)}</div>
          </div>
          <div>${daysBadge(it.days_left)}</div>
        </div>
      `).join('');
    }
  }

  // Load low-stock for dashboard
  const restock = await api('/api/restock?threshold=2');
  const restockList = document.getElementById('dash-restock-list');
  if (restockList && restock) {
    if (restock.length === 0) {
      restockList.innerHTML = '<div class="empty-state"><div class="empty-text">Everything stocked!</div></div>';
    } else {
      restockList.innerHTML = restock.slice(0, 5).map(it => `
        <div class="meal-entry">
          <div>
            <strong>${esc(it.name)}</strong>
            <div class="meal-desc">${storageBadge(it.storage)}</div>
          </div>
          <div style="font-size: 1.1rem; font-weight: 700; color: var(--accent-warm)">${it.quantity}</div>
        </div>
      `).join('');
    }
  }
}

// ═══════════════════════════════════════════════════════════════════════
// INVENTORY
// ═══════════════════════════════════════════════════════════════════════

async function loadInventory() {
  const items = await api('/api/inventory');
  if (!items) return;
  const tbody = document.getElementById('inventory-body');
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="6" class="empty-state"><div class="empty-text">No items in inventory</div></td></tr>';
    return;
  }

  tbody.innerHTML = items.map(it => {
    const rowClass = it.days_left !== null && it.days_left <= 1 ? 'expiry-danger'
                   : it.days_left !== null && it.days_left <= 3 ? 'expiry-warning' : '';
    return `<tr class="${rowClass}">
      <td><strong>${esc(it.name)}</strong></td>
      <td style="text-align:center">${it.quantity}</td>
      <td>${storageBadge(it.storage)}</td>
      <td>${it.expiry_date || '—'}</td>
      <td>${daysBadge(it.days_left)}</td>
      <td style="text-align:center">
        <button class="btn-icon" onclick="deleteInventoryItem(${it.id})" title="Delete">Delete</button>
      </td>
    </tr>`;
  }).join('');
}

async function addInventoryItem() {
  const name    = document.getElementById('add-name').value.trim();
  const qty     = document.getElementById('add-qty').value.trim();
  const storage = document.getElementById('add-storage').value;
  const expiry  = document.getElementById('add-expiry').value;

  if (!name || !qty) {
    toast('Name and quantity are required', 'error');
    return;
  }

  const res = await api('/api/inventory', {
    method: 'POST',
    body: JSON.stringify({
      name, quantity: parseInt(qty), storage, expiry_date: expiry
    })
  });

  if (res && res.ok) {
    toast(`Added ${name}`);
    document.getElementById('add-name').value = '';
    document.getElementById('add-qty').value = '';
    document.getElementById('add-expiry').value = '';
    closeModal('modal-add-item');
    loadInventory();
    loadDashboard();
  } else {
    toast(res?.error || 'Failed to add item', 'error');
  }
}

async function deleteInventoryItem(id) {
  if (!confirm('Delete this item?')) return;
  const res = await api(`/api/inventory/${id}`, { method: 'DELETE' });
  if (res && res.ok) {
    toast('Item deleted');
    loadInventory();
    loadDashboard();
  } else {
    toast('Failed to delete', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════
// RESTOCK
// ═══════════════════════════════════════════════════════════════════════

async function loadRestock() {
  const threshold = document.getElementById('restock-threshold')?.value || 2;
  const items = await api(`/api/restock?threshold=${threshold}`);
  if (!items) return;
  const tbody = document.getElementById('restock-body');
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><div class="empty-text">All items are well-stocked!</div></td></tr>';
    return;
  }

  tbody.innerHTML = items.map(it => `
    <tr>
      <td><strong>${esc(it.name)}</strong></td>
      <td style="text-align:center; color: var(--accent-warm); font-weight: 700">${it.quantity}</td>
      <td>${storageBadge(it.storage)}</td>
      <td style="text-align:center">
        <button class="btn btn-sm btn-primary" onclick="quickRestock(${it.id}, '${esc(it.name)}')">+ Restock</button>
      </td>
    </tr>
  `).join('');
}

async function quickRestock(id, name) {
  const qty = prompt(`New quantity for ${name}:`);
  if (qty === null || qty.trim() === '') return;
  const res = await api(`/api/inventory/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ quantity: parseInt(qty) })
  });
  if (res && res.ok) {
    toast(`${name} restocked to ${qty}`);
    loadRestock();
    loadDashboard();
  } else {
    toast('Update failed', 'error');
  }
}

// ═══════════════════════════════════════════════════════════════════════
// EXPIRY
// ═══════════════════════════════════════════════════════════════════════

async function loadExpiry() {
  const days = document.getElementById('expiry-days')?.value || 3;
  const items = await api(`/api/expiring?days=${days}`);
  if (!items) return;
  const tbody = document.getElementById('expiry-body');
  if (!tbody) return;

  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" class="empty-state"><div class="empty-text">Nothing expiring within ' + days + ' days!</div></td></tr>';
    return;
  }

  tbody.innerHTML = items.map(it => {
    const rowClass = it.days_left <= 0 ? 'expiry-danger' : it.days_left <= 1 ? 'expiry-warning' : '';
    return `<tr class="${rowClass}">
      <td><strong>${esc(it.name)}</strong></td>
      <td>${storageBadge(it.storage)}</td>
      <td>${it.expiry_date}</td>
      <td>${daysBadge(it.days_left)}</td>
    </tr>`;
  }).join('');
}

// ═══════════════════════════════════════════════════════════════════════
// RECIPES
// ═══════════════════════════════════════════════════════════════════════

async function loadRecipes() {
  const filter = document.getElementById('recipe-filter')?.value || 'Both';
  const recipes = await api(`/api/recipes?filter=${filter}`);
  if (!recipes) return;
  const grid = document.getElementById('recipe-grid');
  if (!grid) return;

  if (recipes.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="empty-text">No recipes yet. Add one!</div></div>';
    return;
  }

  grid.innerHTML = recipes.map(r => `
    <div class="recipe-card ${r.can_cook ? 'can-cook' : ''}">
      <div class="recipe-name">
        ${r.can_cook ? '' : ''} ${esc(r.dish)}
        <span class="recipe-status ${r.can_cook ? 'ready' : 'missing'}">
          ${r.can_cook ? 'Ready' : 'Missing items'}
        </span>
      </div>
      <div class="recipe-ingredients">
        ${r.ingredients.split(',').map(i => `<span style="display:inline-block; margin: 2px 4px 2px 0; padding: 2px 8px; background: rgba(255,255,255,0.06); border-radius: 12px; font-size: 0.78rem;">${esc(i.trim())}</span>`).join('')}
      </div>
      <div class="recipe-actions">
        <button class="btn-icon" onclick="deleteRecipe(${r.id})" title="Delete recipe">Delete</button>
      </div>
    </div>
  `).join('');
}

async function addRecipe() {
  const dish = document.getElementById('recipe-dish').value.trim();
  const ingredients = document.getElementById('recipe-ingredients').value.trim();

  if (!dish || !ingredients) {
    toast('Dish name and ingredients required', 'error');
    return;
  }

  const res = await api('/api/recipes', {
    method: 'POST',
    body: JSON.stringify({ dish, ingredients })
  });

  if (res && res.ok) {
    toast(`Recipe "${dish}" added!`);
    document.getElementById('recipe-dish').value = '';
    document.getElementById('recipe-ingredients').value = '';
    closeModal('modal-add-recipe');
    loadRecipes();
    loadDashboard();
  } else {
    toast(res?.error || 'Failed to add recipe', 'error');
  }
}

async function deleteRecipe(id) {
  if (!confirm('Delete this recipe?')) return;
  const res = await api(`/api/recipes/${id}`, { method: 'DELETE' });
  if (res && res.ok) {
    toast('Recipe deleted');
    loadRecipes();
    loadDashboard();
  }
}

// ═══════════════════════════════════════════════════════════════════════
// NUTRITION
// ═══════════════════════════════════════════════════════════════════════

async function loadNutrition() {
  const dateStr = document.getElementById('nutrition-date')?.value || new Date().toISOString().slice(0, 10);

  // Load meals for selected date
  const logs = await api(`/api/nutrition/log?date=${dateStr}`);
  const mealsList = document.getElementById('meals-list');
  if (mealsList && logs) {
    if (logs.length === 0) {
      mealsList.innerHTML = '<div class="empty-state"><div class="empty-text">No meals logged for this date</div></div>';
    } else {
      mealsList.innerHTML = logs.map(e => `
        <div class="meal-entry">
          <div style="flex:1">
            <div class="meal-label-badge">${esc(e.meal_label)}</div>
            <div class="meal-desc">${esc(e.description)}</div>
            ${e.ai_notes ? `<div style="font-size:0.75rem; color: var(--text-muted); margin-top: 4px; font-style: italic;">AI: ${esc(e.ai_notes)}</div>` : ''}
          </div>
          <div class="meal-nutrition">
            <div class="meal-calories">${e.calories ? Math.round(e.calories) + ' kcal' : '—'}</div>
            <div class="meal-protein">${e.protein_g ? e.protein_g.toFixed(1) + 'g protein' : ''}</div>
          </div>
          <button class="btn-icon" style="margin-left: 8px; align-self: center" onclick="deleteMealLog(${e.id})" title="Delete">Delete</button>
        </div>
      `).join('');
    }
  }

  // Load summary
  const summary = await api(`/api/nutrition/summary?date=${dateStr}`);
  if (summary) {
    document.getElementById('nut-total-cal').textContent = Math.round(summary.calories);
    document.getElementById('nut-total-protein').textContent = Math.round(summary.protein_g) + 'g';
    document.getElementById('nut-total-meals').textContent = summary.meals;
  }

  // Load 7-day history
  const history = await api('/api/nutrition/history?days=7');
  const barsEl = document.getElementById('nutrition-bars');
  if (barsEl && history) {
    const maxCal = Math.max(...history.map(h => h.calories), 1);
    barsEl.innerHTML = history.map(h => {
      const pct = Math.max((h.calories / maxCal) * 100, 3);
      const d = new Date(h.date);
      const label = d.toLocaleDateString('en-US', { weekday: 'short' });
      return `
        <div class="history-bar">
          <div class="bar-value">${h.calories > 0 ? Math.round(h.calories) : ''}</div>
          <div class="bar-fill" style="height: ${pct}%" title="${Math.round(h.calories)} kcal"></div>
          <div class="bar-label">${label}</div>
        </div>
      `;
    }).join('');
  }
}

async function addMealLog() {
  const logDate     = document.getElementById('meal-log-date').value;
  const mealLabel   = document.getElementById('meal-label').value;
  const description = document.getElementById('meal-description').value.trim();

  if (!description) {
    toast('Please describe what you ate', 'error');
    return;
  }

  const res = await api('/api/nutrition/log', {
    method: 'POST',
    body: JSON.stringify({
      log_date: logDate,
      meal_label: mealLabel,
      description: description,
      calories: null,
      protein_g: null,
      ai_notes: null,
    })
  });

  if (res && res.ok) {
    toast('Meal logged!');
    document.getElementById('meal-description').value = '';
    closeModal('modal-add-meal');
    loadNutrition();
    loadDashboard();
  } else {
    toast(res?.error || 'Failed to log meal', 'error');
  }
}

async function deleteMealLog(id) {
  if (!confirm('Delete this meal log?')) return;
  const res = await api(`/api/nutrition/log/${id}`, { method: 'DELETE' });
  if (res && res.ok) {
    toast('Meal log deleted');
    loadNutrition();
    loadDashboard();
  }
}

// ═══════════════════════════════════════════════════════════════════════
// HELPERS
// ═══════════════════════════════════════════════════════════════════════

function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function daysBadge(days) {
  if (days === null || days === undefined) {
    return '<span class="days-badge none">No date</span>';
  }
  if (days <= 0) {
    return `<span class="days-badge danger">Expired${days < 0 ? ' ' + Math.abs(days) + 'd ago' : ''}</span>`;
  }
  if (days <= 2) {
    return `<span class="days-badge danger">${days}d left</span>`;
  }
  if (days <= 5) {
    return `<span class="days-badge warning">${days}d left</span>`;
  }
  return `<span class="days-badge safe">${days}d left</span>`;
}

function storageBadge(storage) {
  const cls = storage?.toLowerCase() === 'freezer' ? 'freezer' : 'fridge';
  const icon = cls === 'freezer' ? '' : '';
  return `<span class="storage-badge ${cls}">${icon} ${esc(storage)}</span>`;
}

// ═══════════════════════════════════════════════════════════════════════
// CAMERA SCAN
// ═══════════════════════════════════════════════════════════════════════

let scanStream = null;

async function startCamera() {
  const video = document.getElementById('scan-video');
  if (!video) return;

  try {
    if (scanStream) {
      scanStream.getTracks().forEach(track => track.stop());
    }
    scanStream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    video.srcObject = scanStream;
  } catch (err) {
    console.error("Camera error:", err);
    toast("Could not access camera: " + err.message, "error");
  }
}

async function captureAndScan() {
  const video = document.getElementById('scan-video');
  const canvas = document.getElementById('scan-canvas');
  if (!video || !canvas) return;

  const btn = document.getElementById('btn-capture');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Analyzing...';

  // Draw frame to canvas
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0);

  // Convert to base64
  const imageData = canvas.toDataURL('image/jpeg', 0.8);

  const res = await api('/api/scan', {
    method: 'POST',
    body: JSON.stringify({ image: imageData })
  });

  btn.disabled = false;
  btn.innerHTML = 'Capture & Analyze';

  if (res && res.ok) {
    showScanResults(res.items);
  } else {
    toast(res?.error || "Scan failed", "error");
  }
}

function showScanResults(items) {
  const card = document.getElementById('scan-results-card');
  const list = document.getElementById('scan-results-list');
  if (!card || !list) return;

  if (!items || items.length === 0) {
    list.innerHTML = '<div class="empty-state">No items detected. Try again with better lighting.</div>';
  } else {
    list.innerHTML = items.map((item, idx) => `
      <div class="detected-item">
        <input type="checkbox" checked id="scan-item-${idx}" data-name="${esc(item)}">
        <label for="scan-item-${idx}" style="flex:1">${esc(item)}</label>
        <input type="number" value="1" min="1" style="width: 50px;" class="form-input" id="scan-qty-${idx}">
      </div>
    `).join('');
  }
  card.style.display = 'block';
}

async function addDetectedItems() {
  const items = [];
  document.querySelectorAll('.detected-item input[type="checkbox"]:checked').forEach(cb => {
    const idx = cb.id.split('-').pop();
    const name = cb.dataset.name;
    const qty = document.getElementById(`scan-qty-${idx}`).value;
    items.push({ name, quantity: parseInt(qty) });
  });

  if (items.length === 0) {
    toast("No items selected", "info");
    return;
  }

  let successCount = 0;
  for (const item of items) {
    const res = await api('/api/inventory', {
      method: 'POST',
      body: JSON.stringify({ ...item, storage: 'Fridge' })
    });
    if (res && res.ok) successCount++;
  }

  toast(`Added ${successCount} items to inventory`);
  document.getElementById('scan-results-card').style.display = 'none';
  loadInventory();
}

// ═══════════════════════════════════════════════════════════════════════
// TELEGRAM
// ═══════════════════════════════════════════════════════════════════════

async function sendTelegram(type) {
  const customMsgEl = document.getElementById('tg-custom-msg');
  const payload = { type };
  
  if (type === 'custom') {
    payload.text = customMsgEl.value.trim();
    if (!payload.text) {
      toast("Please enter a message", "error");
      return;
    }
  }

  toast("Sending to Telegram...", "info");
  const res = await api('/api/telegram/send', {
    method: 'POST',
    body: JSON.stringify(payload)
  });

  if (res && res.ok) {
    toast("Message sent!");
    if (type === 'custom') customMsgEl.value = '';
  } else {
    toast(res?.detail || "Failed to send", "error");
  }
}

// Update switchTab to handle camera start
const originalSwitchTab = switchTab;
switchTab = (tab) => {
  originalSwitchTab(tab);
  if (tab === 'scan') {
    startCamera();
  } else if (scanStream) {
    scanStream.getTracks().forEach(track => track.stop());
    scanStream = null;
  }
};
