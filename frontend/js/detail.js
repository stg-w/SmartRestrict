// SmartRestrict Product Detail & Suitability Controller

const ProductDetailCtrl = {
  productId: null,
  productData: null,
  metadata: null,

  async init() {
    const params = new URLSearchParams(window.location.search);
    this.productId = params.get("id");

    if (!this.productId) {
      window.location.href = "/catalogue";
      return;
    }

    try {
      // Parallel fetch of product and metadata
      const [prod, meta] = await Promise.all([
        API.getProductDetail(this.productId),
        API.getMetadata()
      ]);

      this.productData = prod;
      this.metadata = meta;

      this.renderProductHeader();
      this.renderNutritionTable();
      this.renderIngredientsAndAllergens();
      this.setupEvaluationWidget();
      this.loadAlternatives();

      document.getElementById("product-loading").style.display = "none";
      document.getElementById("product-content").style.display = "block";
    } catch (e) {
      document.getElementById("product-loading").innerHTML = `
        <div class="empty-state">
          <i class="bi bi-exclamation-triangle text-danger fs-1"></i>
          <h4 class="mt-3">Unable to Load Product #${this.productId}</h4>
          <p class="text-muted small">${App.escapeHtml(e.message || "Product not found or database unavailable.")}</p>
          <a href="/catalogue" class="btn btn-outline-success mt-2">Back to Catalogue</a>
        </div>
      `;
    }
  },

  renderProductHeader() {
    const p = this.productData;
    document.title = `${p.item_name} | SmartRestrict`;
    document.getElementById("breadcrumb-product-name").textContent = p.item_name;

    document.getElementById("detail-brand").textContent = p.brand_name || "Unknown Brand";
    document.getElementById("detail-category").textContent = p.category_name || "Packaged Food";
    document.getElementById("detail-title").textContent = p.item_name;
    document.getElementById("detail-serving").textContent = p.serving_size_g ? `${p.serving_size_g}g` : "Not specified on label";
    document.getElementById("detail-price").textContent = p.price_inr ? `₹${p.price_inr}` : "N/A";
    
    const src = document.getElementById("detail-data-source");
    if (p.source_of_data) {
      src.textContent = `Source: ${p.source_of_data}`;
    } else {
      src.style.display = "none";
    }

    document.getElementById("detail-dietary-badge").innerHTML = App.renderDietaryBadge(p.dietary_types);

    const tagsContainer = document.getElementById("detail-tags-container");
    tagsContainer.innerHTML = p.tags.map(t => App.renderTagBadge(t)).join("");

    // Completeness card
    const completenessBox = document.getElementById("data-completeness-status");
    const totalNutrients = p.nutrition_facts.length;
    const presentNutrients = p.nutrition_facts.filter(n => n.amount !== null).length;
    const missingCount = p.missing_nutrients.length;

    completenessBox.innerHTML = `
      <div class="mb-2">
        <span class="text-muted">Nutritional parameters recorded:</span>
        <strong class="d-block">${presentNutrients} of ${totalNutrients} measured</strong>
      </div>
      <div>
        <span class="text-muted">Allergen tests/declarations:</span>
        <strong class="d-block">${p.allergens.length > 0 ? p.allergens.join(", ") : "No explicit allergens recorded"}</strong>
      </div>
    `;
  },

  renderNutritionTable() {
    const p = this.productData;
    const tbody = document.getElementById("nutrition-table-body");
    tbody.innerHTML = "";

    p.nutrition_facts.forEach(nf => {
      const tr = document.createElement("tr");

      // Check if this nutrient triggered any tag rule
      let indicatorHtml = `<span class="text-muted small">Standard parameter</span>`;
      if (nf.amount === null) {
        indicatorHtml = `<span class="badge bg-secondary-subtle text-secondary">Missing Value</span>`;
      } else {
        // Find matching tag rules
        const rules = this.metadata.tag_rules.filter(r => r.nutrient_id === nf.nutrient_id);
        const activeIndicators = [];
        rules.forEach(r => {
          let matched = false;
          if (r.operator === ">" && nf.amount > r.threshold) matched = true;
          else if (r.operator === "<=" && nf.amount <= r.threshold) matched = true;

          if (matched) {
            const badgeClass = r.tag_type === "CONCERN" ? "badge-concern" : "badge-positive";
            activeIndicators.push(`
              <span class="badge ${badgeClass} rounded-pill me-1" title="${r.description}">
                ${App.escapeHtml(r.tag_name)} (${r.operator} ${r.threshold}${r.unit})
              </span>
            `);
          }
        });
        if (activeIndicators.length > 0) {
          indicatorHtml = activeIndicators.join(" ");
        }
      }

      tr.innerHTML = `
        <td class="fw-semibold">${App.escapeHtml(nf.nutrient_name)}</td>
        <td class="text-end fw-bold">
          ${nf.amount !== null ? `${nf.amount} ${App.escapeHtml(nf.unit)}` : '<span class="text-muted fw-normal">N/A</span>'}
        </td>
        <td>${indicatorHtml}</td>
      `;
      tbody.appendChild(tr);
    });

    const alertContainer = document.getElementById("missing-nutrients-alert");
    if (p.missing_nutrients.length > 0) {
      alertContainer.innerHTML = `
        <div class="alert alert-warning py-2 small mb-0">
          <i class="bi bi-info-circle-fill me-1"></i>
          <strong>Missing Nutrients:</strong> ${App.escapeHtml(p.missing_nutrients.join(", "))}. 
          SmartRestrict never assumes missing nutrients are zero.
        </div>
      `;
    } else {
      alertContainer.innerHTML = "";
    }
  },

  renderIngredientsAndAllergens() {
    const p = this.productData;

    // Allergens
    const allBox = document.getElementById("product-allergens-list");
    if (p.allergens_list.length > 0) {
      allBox.innerHTML = p.allergens_list.map(a => `
        <span class="badge bg-danger-subtle text-danger border border-danger-subtle p-2 me-1 mb-1 fs-6">
          <i class="bi bi-exclamation-triangle-fill me-1"></i> Contains ${App.escapeHtml(a.allergen_name)}
        </span>
      `).join("");
    } else {
      allBox.innerHTML = `
        <div class="alert alert-light border small text-muted mb-0">
          No explicit allergens declared on this package record. 
          <em>Always verify physical packaging before consumption.</em>
        </div>
      `;
    }

    // Master Ingredients
    const ingBadges = document.getElementById("product-ingredients-badges");
    if (p.ingredients_list.length > 0) {
      ingBadges.innerHTML = p.ingredients_list.map(i => `
        <span class="badge bg-light text-dark border p-2 mb-1">${App.escapeHtml(i.ingredient_name)}</span>
      `).join("");
    } else {
      ingBadges.innerHTML = `<span class="text-muted small">No structured ingredient tags recorded.</span>`;
    }

    // Raw Ingredients Text
    document.getElementById("product-raw-ingredients").textContent = 
      p.ingredients_text || "No raw ingredient label text recorded for this item.";
  },

  setupEvaluationWidget() {
    const rGroup = document.getElementById("restrictions-checkbox-group");
    const aGroup = document.getElementById("allergens-checkbox-group");

    rGroup.innerHTML = this.metadata.restrictions.map(r => `
      <div class="form-check">
        <input class="form-check-input eval-r-check" type="checkbox" value="${r.restriction_id}" id="r-chk-${r.restriction_id}">
        <label class="form-check-label small fw-semibold" for="r-chk-${r.restriction_id}">
          ${App.escapeHtml(r.restriction_name)}
        </label>
      </div>
    `).join("");

    aGroup.innerHTML = this.metadata.allergens.map(a => `
      <div class="form-check">
        <input class="form-check-input eval-a-check" type="checkbox" value="${a.allergen_id}" id="a-chk-${a.allergen_id}">
        <label class="form-check-label small" for="a-chk-${a.allergen_id}">
          ${App.escapeHtml(a.allergen_name)}
        </label>
      </div>
    `).join("");

    // Check saved user restrictions if session exists
    if (App.activeUser && App.activeUser.restrictions) {
      const btnUseProfile = document.getElementById("btn-use-profile");
      btnUseProfile.style.display = "inline-block";
      btnUseProfile.addEventListener("click", () => {
        const savedIds = App.activeUser.restrictions.map(r => r.restriction_id);
        document.querySelectorAll(".eval-r-check").forEach(chk => {
          chk.checked = savedIds.includes(parseInt(chk.value, 10));
        });
        this.runEvaluation();
      });

      // Auto-apply on first load
      const savedIds = App.activeUser.restrictions.map(r => r.restriction_id);
      document.querySelectorAll(".eval-r-check").forEach(chk => {
        if (savedIds.includes(parseInt(chk.value, 10))) chk.checked = true;
      });
    }

    document.getElementById("btn-run-evaluation").addEventListener("click", () => {
      this.runEvaluation();
      this.loadAlternatives();
    });

    // Run initial evaluation
    this.runEvaluation();
  },

  async runEvaluation() {
    const selectedRestrictions = Array.from(document.querySelectorAll(".eval-r-check:checked"))
      .map(c => parseInt(c.value, 10));
    const selectedAllergens = Array.from(document.querySelectorAll(".eval-a-check:checked"))
      .map(c => parseInt(c.value, 10));

    const resultBox = document.getElementById("evaluation-result-container");
    resultBox.innerHTML = `
      <div class="text-center py-3 text-muted">
        <div class="spinner-border spinner-border-sm text-success" role="status"></div>
        <span class="ms-2 small">Analyzing suitability against selected parameters...</span>
      </div>
    `;

    try {
      const res = await API.evaluateProducts(this.productId, selectedRestrictions, selectedAllergens);
      if (!res || res.length === 0) return;
      const evalData = res[0];

      let verdictClass = "suitable";
      let icon = "bi-check-circle-fill text-success";
      if (evalData.status === "AVOID") {
        verdictClass = "avoid";
        icon = "bi-x-circle-fill text-danger";
      } else if (evalData.status === "CAUTION") {
        verdictClass = "caution";
        icon = "bi-exclamation-triangle-fill text-warning";
      }

      resultBox.innerHTML = `
        <div class="verdict-box ${verdictClass}">
          <div class="d-flex align-items-center gap-2 mb-2">
            <i class="bi ${icon} fs-4"></i>
            <h5 class="fw-bold mb-0">${App.escapeHtml(evalData.status)}: ${App.escapeHtml(evalData.verdict)}</h5>
          </div>

          ${evalData.allergen_warnings.length > 0 ? `
            <div class="mt-3">
              <strong class="text-danger small text-uppercase d-block mb-1">
                <i class="bi bi-shield-slash"></i> Allergen Alerts:
              </strong>
              <ul class="mb-2 ps-3 small text-danger">
                ${evalData.allergen_warnings.map(w => `<li><strong>${App.escapeHtml(w.title)}:</strong> ${App.escapeHtml(w.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${evalData.restriction_flags.length > 0 ? `
            <div class="mt-3">
              <strong class="text-dark small text-uppercase d-block mb-1">
                <i class="bi bi-exclamation-octagon"></i> Dietary Restriction Flags:
              </strong>
              <ul class="mb-2 ps-3 small">
                ${evalData.restriction_flags.map(f => `<li><strong>${App.escapeHtml(f.title)}:</strong> ${App.escapeHtml(f.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${evalData.positive_matches.length > 0 ? `
            <div class="mt-3">
              <strong class="text-success small text-uppercase d-block mb-1">
                <i class="bi bi-hand-thumbs-up"></i> Positive Beneficial Matches:
              </strong>
              <ul class="mb-2 ps-3 small text-success">
                ${evalData.positive_matches.map(m => `<li><strong>${App.escapeHtml(m.title)}:</strong> ${App.escapeHtml(m.details)}</li>`).join("")}
              </ul>
            </div>
          ` : ''}

          ${evalData.missing_data_warnings.length > 0 ? `
            <div class="mt-2 pt-2 border-top text-muted small" style="font-size: 0.8rem;">
              <i class="bi bi-info-circle"></i> ${App.escapeHtml(evalData.missing_data_warnings.join(" "))}
            </div>
          ` : ''}

          <div class="mt-2 text-muted small" style="font-size: 0.75rem;">
            <em>${App.escapeHtml(evalData.safety_disclaimer)}</em>
          </div>
        </div>
      `;
    } catch (e) {
      resultBox.innerHTML = `
        <div class="alert alert-warning py-2 small">
          Unable to complete live evaluation: ${App.escapeHtml(e.message)}
        </div>
      `;
    }
  },

  async loadAlternatives() {
    const selectedRestrictions = Array.from(document.querySelectorAll(".eval-r-check:checked"))
      .map(c => parseInt(c.value, 10));
    const selectedAllergens = Array.from(document.querySelectorAll(".eval-a-check:checked"))
      .map(c => parseInt(c.value, 10));

    const grid = document.getElementById("alternatives-grid");
    const loading = document.getElementById("alternatives-loading");
    loading.style.display = "block";
    grid.innerHTML = "";

    try {
      const alts = await API.getAlternatives(this.productId, selectedRestrictions, selectedAllergens, 4);
      loading.style.display = "none";

      if (!alts || alts.length === 0) {
        grid.innerHTML = `
          <div class="col-12 empty-state py-4">
            <i class="bi bi-search text-muted fs-3"></i>
            <p class="text-muted small mt-2">
              No healthier alternatives with complete nutrition improvement found in this category.
            </p>
          </div>
        `;
        return;
      }

      grid.innerHTML = alts.map(alt => `
        <div class="col-md-6">
          <div class="alternative-card h-100">
            <div class="d-flex justify-content-between align-items-start mb-2">
              <div>
                <span class="brand-badge">${App.escapeHtml(alt.brand_name || "Brand")}</span>
                <h5 class="fw-bold mb-1">
                  <a href="/product-detail?id=${alt.product_id}" class="text-decoration-none text-dark">
                    ${App.escapeHtml(alt.item_name)}
                  </a>
                </h5>
                <span class="badge bg-light text-dark border small">${App.escapeHtml(alt.category_name || "Category")}</span>
              </div>
              <div class="text-end">
                <span class="score-badge d-inline-block" title="Alternative Recommendation Score">
                  ${alt.alternative_score}%
                </span>
                <span class="d-block text-muted" style="font-size: 0.65rem;">BETTER MATCH</span>
              </div>
            </div>

            <div class="my-2">
              <strong class="text-success small d-block mb-1">
                <i class="bi bi-check-circle me-1"></i> Why it's a better choice:
              </strong>
              <ul class="mb-2 ps-3 small text-dark">
                ${alt.comparison_points.map(pt => `<li>${App.escapeHtml(pt)}</li>`).join("")}
              </ul>

              ${alt.trade_offs.length > 0 ? `
                <strong class="text-warning-emphasis small d-block mb-1">
                  <i class="bi bi-arrow-left-right me-1"></i> Nutritional Trade-offs:
                </strong>
                <ul class="mb-2 ps-3 small text-muted">
                  ${alt.trade_offs.map(to => `<li>${App.escapeHtml(to)}</li>`).join("")}
                </ul>
              ` : ''}
            </div>

            <div class="d-flex justify-content-between align-items-center pt-2 border-top mt-auto">
              <span class="fw-bold text-success">${alt.price_inr ? '₹' + alt.price_inr : 'Label Price'}</span>
              <a href="/product-detail?id=${alt.product_id}" class="btn btn-outline-success btn-sm">
                Inspect Alternative <i class="bi bi-chevron-right"></i>
              </a>
            </div>
          </div>
        </div>
      `).join("");
    } catch (e) {
      loading.style.display = "none";
      grid.innerHTML = `
        <div class="col-12 text-center text-muted py-3 small">
          Alternatives engine standby: ${App.escapeHtml(e.message)}
        </div>
      `;
    }
  }
};

document.addEventListener("DOMContentLoaded", () => ProductDetailCtrl.init());

