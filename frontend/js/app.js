// SmartRestrict Shared Application Logic

const App = {
  activeUser: null,
  _toastContainer: null,

  init() {
    this.loadUserSession();
    this.updateNavbarUser();
    this.checkDatabaseHealth();
    this._initToastContainer();
    this._setupHeroSearch();
  },

  // ─── User Session ─────────────────────────────────────────────────────────
  loadUserSession() {
    try {
      const stored = localStorage.getItem("smartrestrict_user");
      if (stored) {
        this.activeUser = JSON.parse(stored);
      }
    } catch (e) {
      console.warn("Failed to load user session:", e);
    }
  },

  saveUserSession(user) {
    this.activeUser = user;
    try {
      localStorage.setItem("smartrestrict_user", JSON.stringify(user));
    } catch (e) {
      console.warn("Failed to save user session:", e);
    }
    this.updateNavbarUser();
  },

  clearUserSession() {
    this.activeUser = null;
    localStorage.removeItem("smartrestrict_user");
    this.updateNavbarUser();
  },

  // ─── Recently Viewed ──────────────────────────────────────────────────────
  addRecentlyViewed(product) {
    try {
      let recent = JSON.parse(localStorage.getItem("sr_recent") || "[]");
      // Remove duplicate if present
      recent = recent.filter(p => p.product_id !== product.product_id);
      // Prepend and cap at 6
      recent.unshift({
        product_id: product.product_id,
        item_name: product.item_name,
        brand_name: product.brand_name,
        category_name: product.category_name,
        calories: product.calories ?? null,
      });
      recent = recent.slice(0, 6);
      localStorage.setItem("sr_recent", JSON.stringify(recent));
    } catch (e) {
      // localStorage unavailable — ignore
    }
  },

  getRecentlyViewed() {
    try {
      return JSON.parse(localStorage.getItem("sr_recent") || "[]");
    } catch {
      return [];
    }
  },

  // ─── Compare List ─────────────────────────────────────────────────────────
  getCompareList() {
    try {
      return JSON.parse(sessionStorage.getItem("sr_compare") || "[]");
    } catch {
      return [];
    }
  },

  toggleCompare(productId, itemName) {
    let list = this.getCompareList();
    const idx = list.findIndex(p => p.id === productId);
    if (idx > -1) {
      list.splice(idx, 1);
      this.showToast(`${itemName} removed from compare`, "secondary");
    } else {
      if (list.length >= 3) {
        this.showToast("Compare supports up to 3 products. Remove one first.", "warning");
        return false;
      }
      list.push({ id: productId, name: itemName });
      this.showToast(`${itemName} added to compare`, "success");
    }
    sessionStorage.setItem("sr_compare", JSON.stringify(list));
    this._updateCompareBar();
    return true;
  },

  _updateCompareBar() {
    const bar = document.getElementById("compare-bar");
    if (!bar) return;
    const list = this.getCompareList();
    if (list.length === 0) {
      bar.style.display = "none";
      return;
    }
    bar.style.display = "flex";
    document.getElementById("compare-bar-items").innerHTML = list.map(p =>
      `<span class="badge bg-white text-dark border me-1">${this.escapeHtml(p.name)}</span>`
    ).join("");
    const goBtn = document.getElementById("compare-bar-go");
    if (goBtn) {
      goBtn.href = `/compare?ids=${list.map(p => p.id).join(",")}`;
    }
  },

  // ─── Navbar ───────────────────────────────────────────────────────────────
  updateNavbarUser() {
    const userBadge = document.getElementById("nav-user-badge");
    if (!userBadge) return;

    if (this.activeUser) {
      const rCount = this.activeUser.restrictions ? this.activeUser.restrictions.length : 0;
      userBadge.innerHTML = `
        <a href="/profile" class="btn btn-outline-success btn-sm d-flex align-items-center gap-2">
          <i class="bi bi-person-circle"></i>
          <span>${this.escapeHtml(this.activeUser.user_name)}</span>
          <span class="badge bg-success rounded-pill">${rCount} restriction${rCount !== 1 ? "s" : ""}</span>
        </a>
      `;
    } else {
      userBadge.innerHTML = `
        <a href="/profile" class="btn btn-outline-secondary btn-sm">
          <i class="bi bi-person"></i> Set Dietary Profile
        </a>
      `;
    }
  },

  async checkDatabaseHealth() {
    const healthBadge = document.getElementById("db-health-badge");
    if (!healthBadge) return;

    try {
      const health = await API.getHealth();
      if (health.status === "healthy") {
        healthBadge.className = "badge bg-success-subtle text-success border border-success-subtle";
        healthBadge.innerHTML = `<i class="bi bi-circle-fill me-1" style="font-size: 8px;"></i> Oracle 26ai Connected (${health.products_count} Products)`;
      } else {
        healthBadge.className = "badge bg-warning-subtle text-warning-emphasis border border-warning-subtle";
        healthBadge.innerHTML = `<i class="bi bi-exclamation-triangle-fill me-1"></i> Oracle Standby Mode`;
      }
    } catch (e) {
      healthBadge.className = "badge bg-secondary-subtle text-secondary border border-secondary-subtle";
      healthBadge.innerHTML = `<i class="bi bi-cloud-slash me-1"></i> Local Offline Mode`;
    }
  },

  // ─── Hero Search (shared across pages that embed it) ───────────────────
  _setupHeroSearch() {
    const searchInput = document.getElementById("hero-search-input");
    const searchBtn = document.getElementById("hero-search-btn");
    if (!searchInput || !searchBtn) return;

    const doSearch = () => {
      const q = searchInput.value.trim();
      if (q) {
        window.location.href = `/catalogue?q=${encodeURIComponent(q)}`;
      }
    };
    searchBtn.addEventListener("click", doSearch);
    searchInput.addEventListener("keypress", e => {
      if (e.key === "Enter") doSearch();
    });
  },

  // ─── Toast Notifications ──────────────────────────────────────────────────
  _initToastContainer() {
    if (document.getElementById("sr-toast-container")) return;
    const container = document.createElement("div");
    container.id = "sr-toast-container";
    container.className = "toast-container position-fixed bottom-0 end-0 p-3";
    container.style.zIndex = "1100";
    document.body.appendChild(container);
    this._toastContainer = container;
  },

  /**
   * Show a toast notification.
   * @param {string} message
   * @param {'success'|'danger'|'warning'|'secondary'|'info'} type
   * @param {number} duration  ms before auto-dismiss (0 = stay)
   */
  showToast(message, type = "success", duration = 3500) {
    if (!this._toastContainer) this._initToastContainer();

    const id = `toast-${Date.now()}`;
    const icons = {
      success: "bi-check-circle-fill",
      danger: "bi-x-circle-fill",
      warning: "bi-exclamation-triangle-fill",
      secondary: "bi-info-circle-fill",
      info: "bi-info-circle-fill",
    };
    const icon = icons[type] || "bi-info-circle-fill";

    const toast = document.createElement("div");
    toast.id = id;
    toast.className = `toast align-items-center text-bg-${type} border-0 show`;
    toast.setAttribute("role", "alert");
    toast.innerHTML = `
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${icon}"></i>
          ${this.escapeHtml(message)}
        </div>
        <button type="button" class="btn-close btn-close-white me-2 m-auto"
                onclick="document.getElementById('${id}').remove()"></button>
      </div>
    `;

    this._toastContainer.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  },

  // ─── Rendering Helpers ────────────────────────────────────────────────────
  renderDietaryBadge(dietaryTypes) {
    if (!dietaryTypes || dietaryTypes.length === 0) return "";
    const isVeg = dietaryTypes.includes("Vegetarian") || dietaryTypes.includes("Vegan-Friendly");
    const isEgg = dietaryTypes.includes("Eggetarian");

    if (isVeg) {
      return `
        <span class="veg-indicator me-1" title="Vegetarian" aria-label="Vegetarian">
          <span class="dot"></span>
        </span>
      `;
    } else if (isEgg) {
      return `
        <span class="egg-indicator me-1" title="Eggetarian" aria-label="Eggetarian">
          <span class="dot"></span>
        </span>
      `;
    }
    return "";
  },

  renderTagBadge(tagName) {
    const concernTags = ["High Sugar", "High Sodium", "High Saturated Fat", "High Calories", "Contains Trans Fat"];
    const positiveTags = ["Low Sugar", "Low Sodium", "Low Fat", "High Fibre", "High Protein", "Low Calories", "Clean Ingredients"];

    if (concernTags.includes(tagName)) {
      return `<span class="badge badge-concern rounded-pill me-1 mb-1">${this.escapeHtml(tagName)}</span>`;
    } else if (positiveTags.includes(tagName)) {
      return `<span class="badge badge-positive rounded-pill me-1 mb-1">${this.escapeHtml(tagName)}</span>`;
    }
    return `<span class="badge badge-info-tag rounded-pill me-1 mb-1">${this.escapeHtml(tagName)}</span>`;
  },

  escapeHtml(str) {
    if (!str) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
};

document.addEventListener("DOMContentLoaded", () => App.init());
