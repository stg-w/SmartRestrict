// SmartRestrict Shared Application Logic

const App = {
  activeUser: null,

  init() {
    this.loadUserSession();
    this.updateNavbarUser();
    this.checkDatabaseHealth();
  },

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

  updateNavbarUser() {
    const userBadge = document.getElementById("nav-user-badge");
    if (!userBadge) return;

    if (this.activeUser) {
      const rCount = this.activeUser.restrictions ? this.activeUser.restrictions.length : 0;
      userBadge.innerHTML = `
        <a href="/profile" class="btn btn-outline-success btn-sm d-flex align-items-center gap-2">
          <i class="bi bi-person-circle"></i>
          <span>${this.escapeHtml(this.activeUser.user_name)}</span>
          <span class="badge bg-success rounded-pill">${rCount} restrictions</span>
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

