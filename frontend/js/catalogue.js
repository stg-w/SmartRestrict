// SmartRestrict Catalogue Controller

const Catalogue = {
  currentPage: 1,
  pageSize: 24,
  metadata: null,

  init() {
    this.parseUrlParams();
    this.loadMetadata();
    this.bindEvents();
    this.fetchProducts();
    App._updateCompareBar();
  },

  parseUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("q")) {
      document.getElementById("filter-search").value = params.get("q");
    }
    if (params.get("category_id")) {
      this.pendingCategoryId = params.get("category_id");
    }
    if (params.get("sort_by")) {
      document.getElementById("filter-sort").value = params.get("sort_by");
    }
    if (params.get("page")) {
      this.currentPage = parseInt(params.get("page"), 10) || 1;
    }
  },

  async loadMetadata() {
    try {
      this.metadata = await API.getMetadata();

      // Populate Categories
      const catSelect = document.getElementById("filter-category");
      this.metadata.categories.forEach(c => {
        const opt = document.createElement("option");
        opt.value = c.category_id;
        opt.textContent = c.category_name;
        if (this.pendingCategoryId && this.pendingCategoryId == c.category_id) {
          opt.selected = true;
        }
        catSelect.appendChild(opt);
      });

      // Populate Brands
      const brandSelect = document.getElementById("filter-brand");
      this.metadata.brands.forEach(b => {
        const opt = document.createElement("option");
        opt.value = b.brand_id;
        opt.textContent = b.brand_name;
        brandSelect.appendChild(opt);
      });

      // Populate Dietary Types
      const dietSelect = document.getElementById("filter-dietary");
      this.metadata.dietary_types.forEach(d => {
        const opt = document.createElement("option");
        opt.value = d.dietary_type_id;
        opt.textContent = d.type_name;
        dietSelect.appendChild(opt);
      });

      // Populate Tags
      const tagSelect = document.getElementById("filter-tag");
      this.metadata.tags.forEach(t => {
        const opt = document.createElement("option");
        opt.value = t.tag_id;
        opt.textContent = `${t.tag_name} (${t.tag_type})`;
        tagSelect.appendChild(opt);
      });

      // If category was pending, trigger fetch after options are loaded
      if (this.pendingCategoryId) {
        this.fetchProducts();
        this.pendingCategoryId = null;
      }

    } catch (e) {
      console.warn("Could not load catalogue filter metadata:", e);
    }
  },

  bindEvents() {
    const searchInput = document.getElementById("filter-search");
    const searchBtn = document.getElementById("btn-apply-search");
    const catSelect = document.getElementById("filter-category");
    const brandSelect = document.getElementById("filter-brand");
    const dietSelect = document.getElementById("filter-dietary");
    const tagSelect = document.getElementById("filter-tag");
    const sortSelect = document.getElementById("filter-sort");
    const pageSizeSelect = document.getElementById("page-size-select");
    const resetBtn = document.getElementById("btn-reset-filters");

    const onFilterChange = () => {
      this.currentPage = 1;
      this.fetchProducts();
    };

    searchBtn.addEventListener("click", onFilterChange);
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") onFilterChange();
    });

    catSelect.addEventListener("change", onFilterChange);
    brandSelect.addEventListener("change", onFilterChange);
    dietSelect.addEventListener("change", onFilterChange);
    tagSelect.addEventListener("change", onFilterChange);
    sortSelect.addEventListener("change", onFilterChange);

    pageSizeSelect.addEventListener("change", () => {
      this.pageSize = parseInt(pageSizeSelect.value, 10);
      this.currentPage = 1;
      this.fetchProducts();
    });

    resetBtn.addEventListener("click", () => {
      searchInput.value = "";
      catSelect.value = "";
      brandSelect.value = "";
      dietSelect.value = "";
      tagSelect.value = "";
      sortSelect.value = "name_asc";
      this.currentPage = 1;
      this.fetchProducts();
    });
  },

  getFilterValues() {
    return {
      q: document.getElementById("filter-search").value.trim(),
      category_id: document.getElementById("filter-category").value,
      brand_id: document.getElementById("filter-brand").value,
      dietary_type_id: document.getElementById("filter-dietary").value,
      tag_id: document.getElementById("filter-tag").value,
      sort_by: document.getElementById("filter-sort").value,
      page: this.currentPage,
      page_size: this.pageSize
    };
  },

  renderActiveFilters(filters) {
    const container = document.getElementById("active-filters-container");
    if (!container) return;

    const pills = [];

    if (filters.q) {
      pills.push(`
        <span class="badge bg-success-subtle text-success border border-success-subtle d-inline-flex align-items-center gap-1 px-2 py-1">
          <i class="bi bi-search"></i> "${App.escapeHtml(filters.q)}"
          <button class="btn-close btn-close-sm" style="font-size:0.6rem;" aria-label="Remove"
            onclick="document.getElementById('filter-search').value=''; Catalogue.currentPage=1; Catalogue.fetchProducts();"></button>
        </span>
      `);
    }

    if (filters.category_id && this.metadata) {
      const cat = this.metadata.categories.find(c => c.category_id == filters.category_id);
      if (cat) {
        pills.push(`
          <span class="badge bg-primary-subtle text-primary border border-primary-subtle d-inline-flex align-items-center gap-1 px-2 py-1">
            <i class="bi bi-grid"></i> ${App.escapeHtml(cat.category_name)}
            <button class="btn-close btn-close-sm" style="font-size:0.6rem;" aria-label="Remove"
              onclick="document.getElementById('filter-category').value=''; Catalogue.currentPage=1; Catalogue.fetchProducts();"></button>
          </span>
        `);
      }
    }

    if (filters.brand_id && this.metadata) {
      const brand = this.metadata.brands.find(b => b.brand_id == filters.brand_id);
      if (brand) {
        pills.push(`
          <span class="badge bg-secondary-subtle text-secondary border d-inline-flex align-items-center gap-1 px-2 py-1">
            <i class="bi bi-building"></i> ${App.escapeHtml(brand.brand_name)}
            <button class="btn-close btn-close-sm" style="font-size:0.6rem;" aria-label="Remove"
              onclick="document.getElementById('filter-brand').value=''; Catalogue.currentPage=1; Catalogue.fetchProducts();"></button>
          </span>
        `);
      }
    }

    if (filters.dietary_type_id && this.metadata) {
      const dt = this.metadata.dietary_types.find(d => d.dietary_type_id == filters.dietary_type_id);
      if (dt) {
        pills.push(`
          <span class="badge bg-info-subtle text-info border border-info-subtle d-inline-flex align-items-center gap-1 px-2 py-1">
            <i class="bi bi-leaf"></i> ${App.escapeHtml(dt.type_name)}
            <button class="btn-close btn-close-sm" style="font-size:0.6rem;" aria-label="Remove"
              onclick="document.getElementById('filter-dietary').value=''; Catalogue.currentPage=1; Catalogue.fetchProducts();"></button>
          </span>
        `);
      }
    }

    if (filters.tag_id && this.metadata) {
      const tag = this.metadata.tags.find(t => t.tag_id == filters.tag_id);
      if (tag) {
        const colorClass = tag.tag_type === "CONCERN" ? "badge-concern" : "badge-positive";
        pills.push(`
          <span class="badge ${colorClass} d-inline-flex align-items-center gap-1 px-2 py-1">
            <i class="bi bi-tag"></i> ${App.escapeHtml(tag.tag_name)}
            <button class="btn-close btn-close-sm" style="font-size:0.6rem;" aria-label="Remove"
              onclick="document.getElementById('filter-tag').value=''; Catalogue.currentPage=1; Catalogue.fetchProducts();"></button>
          </span>
        `);
      }
    }

    container.innerHTML = pills.length > 0
      ? `<div class="d-flex flex-wrap gap-2 mb-3">${pills.join("")}</div>`
      : "";
  },

  async fetchProducts() {
    const grid = document.getElementById("products-grid");
    const countBox = document.getElementById("results-count");
    grid.innerHTML = `
      <div class="col-12 loading-spinner">
        <div class="spinner-border text-success" role="status"></div>
        <p class="mt-2 small text-muted">Retrieving products from Oracle Database...</p>
      </div>
    `;

    const filters = this.getFilterValues();
    this.renderActiveFilters(filters);

    // Update browser URL query without reloading
    const query = new URLSearchParams();
    for (const [k, v] of Object.entries(filters)) {
      if (v) query.set(k, v);
    }
    history.replaceState(null, "", `${window.location.pathname}?${query.toString()}`);

    try {
      const data = await API.getProducts(filters);
      this.renderProducts(data);
      this.renderPagination(data);

      const start = (data.page - 1) * data.page_size + 1;
      const end = Math.min(data.page * data.page_size, data.total);
      countBox.textContent = data.total > 0
        ? `Showing ${start}–${end} of ${data.total} products`
        : "No matching products found";
    } catch (e) {
      grid.innerHTML = `
        <div class="col-12 empty-state">
          <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
          <h5 class="mt-3">Unable to fetch products</h5>
          <p class="text-muted small">Please verify database connectivity or network settings.</p>
          <button class="btn btn-outline-success btn-sm mt-2" onclick="Catalogue.fetchProducts()">Retry</button>
        </div>
      `;
      countBox.textContent = "Error loading products";
    }
  },

  renderProducts(data) {
    const grid = document.getElementById("products-grid");
    if (!data.items || data.items.length === 0) {
      grid.innerHTML = `
        <div class="col-12 empty-state">
          <i class="bi bi-search fs-1"></i>
          <h5 class="mt-3">No products matched your criteria</h5>
          <p class="text-muted small">Try broadening your search term or clearing one of the filters.</p>
          <button class="btn btn-outline-secondary btn-sm" onclick="document.getElementById('btn-reset-filters').click()">
            Reset all filters
          </button>
        </div>
      `;
      return;
    }

    const compareList = App.getCompareList();

    grid.innerHTML = data.items.map(p => {
      const isInCompare = compareList.some(c => c.id === p.product_id);

      // Allergen warning pill (show up to 2 allergens on the card)
      const allergenPill = p.allergens && p.allergens.length > 0
        ? `<div class="mb-2">
             ${p.allergens.slice(0, 2).map(a =>
               `<span class="badge bg-danger-subtle text-danger border border-danger-subtle me-1" title="Contains ${App.escapeHtml(a)}">
                  <i class="bi bi-exclamation-triangle-fill"></i> ${App.escapeHtml(a)}
                </span>`
             ).join("")}
             ${p.allergens.length > 2 ? `<span class="badge bg-secondary-subtle text-secondary border">+${p.allergens.length - 2} more</span>` : ""}
           </div>`
        : "";

      return `
      <div class="col-md-6 col-lg-4">
        <div class="product-card">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <span class="brand-badge">${App.escapeHtml(p.brand_name || "Brand")}</span>
              <div>
                ${App.renderDietaryBadge(p.dietary_types)}
                <span class="badge bg-light text-dark border">${App.escapeHtml(p.category_name || "Category")}</span>
              </div>
            </div>

            <h5 class="product-title mb-2">
              <a href="/product-detail?id=${p.product_id}" class="text-decoration-none text-dark">
                ${App.escapeHtml(p.item_name)}
              </a>
            </h5>

            <div class="mb-2 d-flex flex-wrap">
              ${p.tags.slice(0, 3).map(t => App.renderTagBadge(t)).join("")}
            </div>

            ${allergenPill}

            <div class="row g-2 mb-3">
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Calories</span>
                  <span>${p.calories !== null ? p.calories + " kcal" : "N/A"}</span>
                </div>
              </div>
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Sugar</span>
                  <span>${p.sugar !== null ? p.sugar + "g" : "N/A"}</span>
                </div>
              </div>
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Sodium</span>
                  <span>${p.sodium !== null ? p.sodium + "mg" : "N/A"}</span>
                </div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center pt-2 border-top">
              <div class="d-flex align-items-center gap-2">
                <span class="fw-bold text-success">${p.price_inr ? "₹" + p.price_inr : "Price N/A"}</span>
                <label class="compare-checkbox-label small text-muted" title="Add to compare (max 3)">
                  <input type="checkbox" class="compare-chk me-1" ${isInCompare ? "checked" : ""}
                    onchange="App.toggleCompare(${p.product_id}, '${App.escapeHtml(p.item_name).replace(/'/g, "\\'")}')">
                  Compare
                </label>
              </div>
              <a href="/product-detail?id=${p.product_id}" class="btn btn-outline-success btn-sm">
                Details <i class="bi bi-chevron-right"></i>
              </a>
            </div>
          </div>
        </div>
      </div>
    `;
    }).join("");
  },

  renderPagination(data) {
    const container = document.getElementById("pagination-controls");
    container.innerHTML = "";

    if (data.total_pages <= 1) return;

    // Previous Button
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${data.page <= 1 ? "disabled" : ""}`;
    prevLi.innerHTML = `<button class="page-link" aria-label="Previous">&laquo;</button>`;
    prevLi.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
    container.appendChild(prevLi);

    // Page window: show up to 5 surrounding pages
    const maxPagesToShow = 5;
    let startPage = Math.max(1, data.page - 2);
    let endPage = Math.min(data.total_pages, startPage + maxPagesToShow - 1);
    if (endPage - startPage < maxPagesToShow - 1) {
      startPage = Math.max(1, endPage - maxPagesToShow + 1);
    }

    if (startPage > 1) {
      const li = document.createElement("li");
      li.className = "page-item";
      li.innerHTML = `<button class="page-link">1</button>`;
      li.addEventListener("click", () => {
        this.currentPage = 1;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      container.appendChild(li);

      if (startPage > 2) {
        const dots = document.createElement("li");
        dots.className = "page-item disabled";
        dots.innerHTML = `<span class="page-link">...</span>`;
        container.appendChild(dots);
      }
    }

    for (let p = startPage; p <= endPage; p++) {
      const li = document.createElement("li");
      li.className = `page-item ${p === data.page ? "active" : ""}`;
      li.innerHTML = `<button class="page-link">${p}</button>`;
      const targetPage = p;
      li.addEventListener("click", () => {
        this.currentPage = targetPage;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      container.appendChild(li);
    }

    if (endPage < data.total_pages) {
      if (endPage < data.total_pages - 1) {
        const dots = document.createElement("li");
        dots.className = "page-item disabled";
        dots.innerHTML = `<span class="page-link">...</span>`;
        container.appendChild(dots);
      }
      const li = document.createElement("li");
      li.className = "page-item";
      li.innerHTML = `<button class="page-link">${data.total_pages}</button>`;
      li.addEventListener("click", () => {
        this.currentPage = data.total_pages;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: "smooth" });
      });
      container.appendChild(li);
    }

    // Next Button
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${data.page >= data.total_pages ? "disabled" : ""}`;
    nextLi.innerHTML = `<button class="page-link" aria-label="Next">&raquo;</button>`;
    nextLi.addEventListener("click", () => {
      if (this.currentPage < data.total_pages) {
        this.currentPage++;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
    container.appendChild(nextLi);
  }
};

document.addEventListener("DOMContentLoaded", () => Catalogue.init());
