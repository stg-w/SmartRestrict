// SmartRestrict Dietary & Allergen Evaluation Controller

const EvaluateCtrl = {
  metadata: null,
  selectedProductId: null,

  async init() {
    try {
      this.metadata = await API.getMetadata();
      this.renderControls();
      this.bindEvents();
      this.loadInitialProducts();
    } catch (e) {
      console.warn("Could not load evaluate metadata:", e);
    }
  },

  renderControls() {
    const rBox = document.getElementById("eval-restrictions-container");
    const aBox = document.getElementById("eval-allergens-container");

    rBox.innerHTML = this.metadata.restrictions.map(r => `
      <div class="form-check">
        <input class="form-check-input eval-r-chk" type="checkbox" value="${r.restriction_id}" id="chk-r-${r.restriction_id}">
        <label class="form-check-label small fw-semibold" for="chk-r-${r.restriction_id}">
          ${App.escapeHtml(r.restriction_name)}
        </label>
      </div>
    `).join("");

    aBox.innerHTML = this.metadata.allergens.map(a => `
      <div class="form-check">
        <input class="form-check-input eval-a-chk" type="checkbox" value="${a.allergen_id}" id="chk-a-${a.allergen_id}">
        <label class="form-check-label small" for="chk-a-${a.allergen_id}">
          ${App.escapeHtml(a.allergen_name)}
        </label>
      </div>
    `).join("");

    if (App.activeUser && App.activeUser.restrictions) {
      const btn = document.getElementById("btn-apply-user-profile");
      btn.style.display = "inline-block";
      btn.addEventListener("click", () => {
        const savedIds = App.activeUser.restrictions.map(r => r.restriction_id);
        document.querySelectorAll(".eval-r-chk").forEach(c => {
          c.checked = savedIds.includes(parseInt(c.value, 10));
        });
        this.runAnalysis();
      });
    }
  },

  bindEvents() {
    const searchInput = document.getElementById("eval-search-product");
    const searchBtn = document.getElementById("btn-search-product");
    const selectProduct = document.getElementById("eval-select-product");

    const doSearch = async () => {
      const q = searchInput.value.trim();
      if (!q) return;
      selectProduct.innerHTML = '<option value="">Searching...</option>';
      try {
        const res = await API.getProducts({ q, page: 1, page_size: 20 });
        if (res.items && res.items.length > 0) {
          selectProduct.innerHTML = '<option value="">-- Choose matching product --</option>' +
            res.items.map(p => `<option value="${p.product_id}">${App.escapeHtml(p.brand_name ? p.brand_name + ' - ' : '')}${App.escapeHtml(p.item_name)}</option>`).join("");
          selectProduct.selectedIndex = 1;
          this.selectedProductId = res.items[0].product_id;
          this.runAnalysis();
        } else {
          selectProduct.innerHTML = '<option value="">No products found</option>';
        }
      } catch (e) {
        selectProduct.innerHTML = '<option value="">Search error</option>';
      }
    };

    searchBtn.addEventListener("click", doSearch);
    searchInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") doSearch();
    });

    selectProduct.addEventListener("change", () => {
      const pid = selectProduct.value;
      if (pid) {
        this.selectedProductId = parseInt(pid, 10);
        this.runAnalysis();
      }
    });

    // Re-run on checkbox change
    document.addEventListener("change", (e) => {
      if (e.target.classList.contains("eval-r-chk") || e.target.classList.contains("eval-a-chk")) {
        if (this.selectedProductId) this.runAnalysis();
      }
    });
  },

  async loadInitialProducts() {
    const selectProduct = document.getElementById("eval-select-product");
    try {
      const res = await API.getProducts({ page: 1, page_size: 15 });
      if (res.items && res.items.length > 0) {
        selectProduct.innerHTML = '<option value="">-- Select a product to analyze --</option>' +
          res.items.map(p => `<option value="${p.product_id}">${App.escapeHtml(p.brand_name ? p.brand_name + ' - ' : '')}${App.escapeHtml(p.item_name)}</option>`).join("");
      }
    } catch (e) {
      console.warn("Could not prefill products:", e);
    }
  },

  async runAnalysis() {
    if (!this.selectedProductId) return;

    const selectedR = Array.from(document.querySelectorAll(".eval-r-chk:checked"))
      .map(c => parseInt(c.value, 10));
    const selectedA = Array.from(document.querySelectorAll(".eval-a-chk:checked"))
      .map(c => parseInt(c.value, 10));

    const container = document.getElementById("eval-results-container");
    container.innerHTML = `
      <div class="text-center py-4 text-muted">
        <div class="spinner-border text-success" role="status"></div>
        <p class="mt-2 small">Evaluating nutritional thresholds and restriction rules in Oracle...</p>
      </div>
    `;

    try {
      const [evalRes, detail, alts] = await Promise.all([
        API.evaluateProducts(this.selectedProductId, selectedR, selectedA),
        API.getProductDetail(this.selectedProductId),
        API.getAlternatives(this.selectedProductId, selectedR, selectedA, 2)
      ]);

      if (!evalRes || evalRes.length === 0) return;
      const res = evalRes[0];

      let verdictClass = "suitable";
      let icon = "bi-check-circle-fill text-success";
      if (res.status === "AVOID") {
        verdictClass = "avoid";
        icon = "bi-x-circle-fill text-danger";
      } else if (res.status === "CAUTION") {
        verdictClass = "caution";
        icon = "bi-exclamation-triangle-fill text-warning";
      }

      container.innerHTML = `
        <div class="verdict-box ${verdictClass} mb-4">
          <div class="d-flex justify-content-between align-items-start">
            <div class="d-flex align-items-center gap-3">
              <i class="bi ${icon} fs-2"></i>
              <div>
                <span class="badge bg-dark-subtle text-dark border small text-uppercase">${App.escapeHtml(detail.brand_name || 'Brand')}</span>
                <h4 class="fw-bold mb-1">${App.escapeHtml(detail.item_name)}</h4>
                <div class="fw-bold fs-6">${App.escapeHtml(res.status)}: ${App.escapeHtml(res.verdict)}</div>
              </div>
            </div>
            <a href="/product-detail?id=${detail.product_id}" class="btn btn-outline-dark btn-sm">
              Full Nutrition Facts <i class="bi bi-box-arrow-up-right"></i>
            </a>
          </div>

          ${res.allergen_warnings.length > 0 ? `
            <div class="mt-3 p-3 bg-white rounded border border-danger">
              <h6 class="text-danger fw-bold mb-2"><i class="bi bi-shield-slash"></i> Allergen Alerts</h6>
              <ul class="mb-0 ps-3 small text-danger">
                ${res.allergen_warnings.map(w => `<li><strong>${App.escapeHtml(w.title)}:</strong> ${App.escapeHtml(w.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${res.restriction_flags.length > 0 ? `
            <div class="mt-3 p-3 bg-white rounded border">
              <h6 class="text-dark fw-bold mb-2"><i class="bi bi-exclamation-octagon"></i> Dietary Restriction Flags</h6>
              <ul class="mb-0 ps-3 small">
                ${res.restriction_flags.map(f => `<li><strong>${App.escapeHtml(f.title)}:</strong> ${App.escapeHtml(f.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${res.positive_matches.length > 0 ? `
            <div class="mt-3 p-3 bg-white rounded border border-success">
              <h6 class="text-success fw-bold mb-2"><i class="bi bi-hand-thumbs-up"></i> Positive Nutritional Matches</h6>
              <ul class="mb-0 ps-3 small text-success">
                ${res.positive_matches.map(m => `<li><strong>${App.escapeHtml(m.title)}:</strong> ${App.escapeHtml(m.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${res.missing_data_warnings.length > 0 ? `
            <div class="mt-3 small text-muted">
              <i class="bi bi-info-circle"></i> ${App.escapeHtml(res.missing_data_warnings.join(" "))}
            </div>
          ` : ''}

          <div class="mt-2 text-muted small" style="font-size: 0.75rem;">
            <em>${App.escapeHtml(res.safety_disclaimer)}</em>
          </div>
        </div>

        ${alts && alts.length > 0 ? `
          <div class="mt-4 pt-3 border-top">
            <h6 class="fw-bold text-success mb-3"><i class="bi bi-arrow-up-right-circle"></i> Recommended Better Alternatives in This Category</h6>
            <div class="row g-3">
              ${alts.map(a => `
                <div class="col-md-6">
                  <div class="alternative-card">
                    <div class="d-flex justify-content-between align-items-start mb-2">
                      <div>
                        <span class="brand-badge">${App.escapeHtml(a.brand_name || 'Brand')}</span>
                        <h6 class="fw-bold mb-0">${App.escapeHtml(a.item_name)}</h6>
                      </div>
                      <span class="score-badge">${a.alternative_score}%</span>
                    </div>
                    <ul class="mb-2 ps-3 small text-success">
                      ${a.comparison_points.map(cp => `<li>${App.escapeHtml(cp)}</li>`).join("")}
                    </ul>
                    <a href="/product-detail?id=${a.product_id}" class="btn btn-outline-success btn-sm w-100">
                      View Alternative Details
                    </a>
                  </div>
                </div>
              `).join("")}
            </div>
          </div>
        ` : ''}
      `;
    } catch (e) {
      container.innerHTML = `
        <div class="alert alert-warning py-3">
          Analysis error: ${App.escapeHtml(e.message)}
        </div>
      `;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => EvaluateCtrl.init());

