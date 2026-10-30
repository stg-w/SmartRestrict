// SmartRestrict API Client
const API = {
  baseUrl: window.location.origin.includes(":8000")
    ? ""
    : "http://localhost:8000",

  async getHealth() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    return await res.json();
  },

  async getStats() {
    const res = await fetch(`${this.baseUrl}/api/stats`);
    if (!res.ok) throw new Error("Failed to load statistics");
    return await res.json();
  },

  async getMetadata() {
    const res = await fetch(`${this.baseUrl}/api/metadata`);
    if (!res.ok) throw new Error("Failed to load metadata");
    return await res.json();
  },

  async getProducts(params = {}) {
    const query = new URLSearchParams();
    for (const [key, val] of Object.entries(params)) {
      if (val !== null && val !== undefined && val !== "") {
        query.append(key, val);
      }
    }
    const res = await fetch(`${this.baseUrl}/api/products?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch products");
    return await res.json();
  },

  async searchProducts(q, limit = 10) {
    const query = new URLSearchParams({ q, limit });
    const res = await fetch(`${this.baseUrl}/api/products/search?${query.toString()}`);
    if (!res.ok) throw new Error("Search failed");
    return await res.json();
  },

  async getProductDetail(productId) {
    const res = await fetch(`${this.baseUrl}/api/products/${productId}`);
    if (!res.ok) throw new Error("Product not found");
    return await res.json();
  },

  async evaluateProducts(productId, restrictionIds = [], allergenIds = []) {
    const res = await fetch(`${this.baseUrl}/api/evaluate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        product_id: productId,
        restriction_ids: restrictionIds,
        allergen_ids: allergenIds
      })
    });
    if (!res.ok) throw new Error("Evaluation failed");
    return await res.json();
  },

  async getAlternatives(productId, restrictionIds = [], allergenIds = [], limit = 5) {
    const query = new URLSearchParams();
    if (restrictionIds && restrictionIds.length > 0) {
      query.append("restriction_ids", restrictionIds.join(","));
    }
    if (allergenIds && allergenIds.length > 0) {
      query.append("allergen_ids", allergenIds.join(","));
    }
    query.append("limit", limit);

    const res = await fetch(`${this.baseUrl}/api/products/${productId}/alternatives?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to load alternatives");
    return await res.json();
  },

  async saveUserProfile(userName, email, restrictionIds) {
    const res = await fetch(`${this.baseUrl}/api/users/profile`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_name: userName,
        email: email,
        restriction_ids: restrictionIds
      })
    });
    if (!res.ok) throw new Error("Failed to save profile");
    return await res.json();
  },

  async getUserProfile(email) {
    const res = await fetch(`${this.baseUrl}/api/users/profile?email=${encodeURIComponent(email)}`);
    if (!res.ok) throw new Error("User not found");
    return await res.json();
  }
};
