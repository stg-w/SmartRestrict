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
        ? `Showing ${start}-${end} of ${data.total} products`
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

    grid.innerHTML = data.items.map(p => `
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

            <div class="mb-3 d-flex flex-wrap">
              ${p.tags.slice(0, 3).map(t => App.renderTagBadge(t)).join("")}
            </div>

            <div class="row g-2 mb-3 mt-auto">
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Calories</span>
                  <span>${p.calories !== null ? p.calories + ' kcal' : 'N/A'}</span>
                </div>
              </div>
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Sugar</span>
                  <span>${p.sugar !== null ? p.sugar + 'g' : 'N/A'}</span>
                </div>
              </div>
              <div class="col-4">
                <div class="nutrient-chip">
                  <span class="label">Sodium</span>
                  <span>${p.sodium !== null ? p.sodium + 'mg' : 'N/A'}</span>
                </div>
              </div>
            </div>

            <div class="d-flex justify-content-between align-items-center pt-2 border-top">
              <span class="fw-bold text-success">${p.price_inr ? '₹' + p.price_inr : 'Price N/A'}</span>
              <a href="/product-detail?id=${p.product_id}" class="btn btn-outline-success btn-sm">
                Details <i class="bi bi-chevron-right"></i>
              </a>
            </div>
          </div>
        </div>
      </div>
    `).join("");
  },

  renderPagination(data) {
    const container = document.getElementById("pagination-controls");
    container.innerHTML = "";

    if (data.total_pages <= 1) return;

    // Previous Button
    const prevLi = document.createElement("li");
    prevLi.className = `page-item ${data.page <= 1 ? 'disabled' : ''}`;
    prevLi.innerHTML = `<button class="page-link" aria-label="Previous">&laquo;</button>`;
    prevLi.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
      li.className = `page-item ${p === data.page ? 'active' : ''}`;
      li.innerHTML = `<button class="page-link">${p}</button>`;
      const targetPage = p;
      li.addEventListener("click", () => {
        this.currentPage = targetPage;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
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
        window.scrollTo({ top: 0, behavior: 'smooth' });
      });
      container.appendChild(li);
    }

    // Next Button
    const nextLi = document.createElement("li");
    nextLi.className = `page-item ${data.page >= data.total_pages ? 'disabled' : ''}`;
    nextLi.innerHTML = `<button class="page-link" aria-label="Next">&raquo;</button>`;
    nextLi.addEventListener("click", () => {
      if (this.currentPage < data.total_pages) {
        this.currentPage++;
        this.fetchProducts();
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    });
    container.appendChild(nextLi);
  }
};

document.addEventListener("DOMContentLoaded", () => Catalogue.init());

