const CompareCtrl = {
  async init() {
    const params = new URLSearchParams(window.location.search);
    const queryIds = (params.get("ids") || "").split(",").map(Number).filter(Number.isInteger);
    const storedIds = App.getCompareList().map((item) => Number(item.id)).filter(Number.isInteger);
    const ids = (queryIds.length ? queryIds : storedIds).slice(0, 3);
    const loading = document.getElementById("compare-loading");
    const content = document.getElementById("compare-content");

    if (!ids.length) {
      loading.style.display = "none";
      content.innerHTML = '<div class="alert alert-light border">No products selected. <a href="/catalogue">Choose products from the catalogue</a>.</div>';
      return;
    }

    try {
      const products = await Promise.all(ids.map((id) => API.getProductDetail(id)));
      loading.style.display = "none";
      const rows = [
        ["Brand", (p) => p.brand_name || "N/A"],
        ["Category", (p) => p.category_name || "N/A"],
        ["Serving size", (p) => p.serving_size_g == null ? "N/A" : `${p.serving_size_g} g`],
        ["Calories", (p) => this.nutrient(p, "Calories", "kcal")],
        ["Sugar", (p) => this.nutrient(p, "Sugar", "g")],
        ["Sodium", (p) => this.nutrient(p, "Sodium", "mg")],
        ["Saturated fat", (p) => this.nutrient(p, "Saturated Fat", "g")],
        ["Protein", (p) => this.nutrient(p, "Protein", "g")],
        ["Dietary fibre", (p) => this.nutrient(p, "Dietary Fibre", "g")],
        ["Tags", (p) => p.tags?.join(", ") || "N/A"],
        ["Allergens", (p) => p.allergens?.join(", ") || "None recorded"]
      ];
      content.innerHTML = `<div class="table-responsive"><table class="table table-bordered align-middle compare-table"><thead><tr><th>Nutrition fact</th>${products.map((p) => `<th>${App.escapeHtml(p.item_name)}</th>`).join("")}</tr></thead><tbody>${rows.map(([label, getter]) => `<tr><th>${label}</th>${products.map((p) => `<td>${App.escapeHtml(String(getter(p)))}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    } catch (error) {
      loading.style.display = "none";
      content.innerHTML = `<div class="alert alert-warning">Unable to load comparison: ${App.escapeHtml(error.message)}</div>`;
    }
  },

  nutrient(product, name, unit) {
    const fact = product.nutrition_facts?.find((item) => item.nutrient_name?.toLowerCase() === name.toLowerCase());
    return !fact || fact.amount == null ? "N/A" : `${fact.amount} ${unit}`;
  }
};

document.addEventListener("DOMContentLoaded", () => CompareCtrl.init());
