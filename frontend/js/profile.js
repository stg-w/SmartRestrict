// SmartRestrict User Profile Controller

const ProfileCtrl = {
  metadata: null,

  async init() {
    try {
      this.metadata = await API.getMetadata();
      this.renderRestrictions();
      this.populateActiveUser();
      this.bindEvents();
    } catch (e) {
      console.warn("Could not load metadata for profile:", e);
    }
  },

  renderRestrictions() {
    const group = document.getElementById("profile-restrictions-group");
    group.innerHTML = this.metadata.restrictions.map(r => `
      <div class="col-md-6">
        <div class="p-2 border rounded bg-white h-100">
          <div class="form-check">
            <input class="form-check-input profile-r-chk" type="checkbox" value="${r.restriction_id}" id="pref-r-${r.restriction_id}">
            <label class="form-check-label fw-semibold small" for="pref-r-${r.restriction_id}">
              ${App.escapeHtml(r.restriction_name)}
            </label>
            <p class="text-muted mb-0" style="font-size: 0.75rem;">
              ${App.escapeHtml(r.description || '')}
            </p>
          </div>
        </div>
      </div>
    `).join("");
  },

  populateActiveUser() {
    if (!App.activeUser) return;
    document.getElementById("profile-name").value = App.activeUser.user_name || "";
    document.getElementById("profile-email").value = App.activeUser.email || "";

    if (App.activeUser.restrictions) {
      const savedIds = App.activeUser.restrictions.map(r => r.restriction_id);
      document.querySelectorAll(".profile-r-chk").forEach(chk => {
        if (savedIds.includes(parseInt(chk.value, 10))) {
          chk.checked = true;
        }
      });
    }
  },

  bindEvents() {
    const form = document.getElementById("profile-form");
    const msgBox = document.getElementById("profile-message");
    const btnLoad = document.getElementById("btn-load-by-email");
    const btnClear = document.getElementById("btn-clear-session");

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      msgBox.innerHTML = `
        <div class="alert alert-info py-2 small">
          <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
          <span class="ms-2">Saving profile to Oracle Database...</span>
        </div>
      `;

      const userName = document.getElementById("profile-name").value.trim();
      const email = document.getElementById("profile-email").value.trim();
      const selectedRIds = Array.from(document.querySelectorAll(".profile-r-chk:checked"))
        .map(c => parseInt(c.value, 10));

      try {
        const saved = await API.saveUserProfile(userName, email, selectedRIds);
        App.saveUserSession(saved);

        msgBox.innerHTML = `
          <div class="alert alert-success py-2 small">
            <i class="bi bi-check-circle-fill me-1"></i>
            Profile saved successfully to Oracle! User ID #${saved.user_id} with ${saved.restrictions.length} restrictions.
          </div>
        `;
      } catch (err) {
        msgBox.innerHTML = `
          <div class="alert alert-danger py-2 small">
            <i class="bi bi-exclamation-triangle-fill me-1"></i>
            Failed to save profile: ${App.escapeHtml(err.message)}
          </div>
        `;
      }
    });

    btnLoad.addEventListener("click", async () => {
      const email = document.getElementById("profile-email").value.trim();
      if (!email) {
        alert("Please enter an email address to look up.");
        return;
      }
      msgBox.innerHTML = '<div class="text-muted small">Searching Oracle USERS table...</div>';
      try {
        const profile = await API.getUserProfile(email);
        App.saveUserSession(profile);
        this.populateActiveUser();
        msgBox.innerHTML = `
          <div class="alert alert-success py-2 small">
            Loaded profile for ${App.escapeHtml(profile.user_name)} from Oracle!
          </div>
        `;
      } catch (err) {
        msgBox.innerHTML = `
          <div class="alert alert-warning py-2 small">
            No profile found in Oracle for ${App.escapeHtml(email)}. Fill out the form to register.
          </div>
        `;
      }
    });

    btnClear.addEventListener("click", () => {
      App.clearUserSession();
      document.getElementById("profile-name").value = "";
      document.getElementById("profile-email").value = "";
      document.querySelectorAll(".profile-r-chk").forEach(c => c.checked = false);
      msgBox.innerHTML = `<div class="alert alert-secondary py-2 small">Active session cleared.</div>`;
    });
  }
};

document.addEventListener("DOMContentLoaded", () => ProfileCtrl.init());

