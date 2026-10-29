# SmartRestrict API Specification & Postman Collection Guide

This document contains request and response examples for testing the SmartRestrict API using Postman or cURL.

Base URL: `http://localhost:8000`

---

## 1. Health Check
Checks Oracle Database Free 26ai connectivity, connected host, and row counts.

- **Method**: `GET`
- **Endpoint**: `/api/health`
- **Headers**: None

### Example Response (200 OK)
```json
{
  "status": "healthy",
  "oracle_version": "23.26.2.0.0",
  "products_count": 852,
  "connected_host": "172.20.10.2",
  "connected_service": "FREEPDB1"
}
```

---

## 2. Master Metadata
Retrieves all 262 brands, 220 categories, 12 nutrients, 8 allergens, 4 dietary types, 12 tags, 5 restrictions, 11 tag rules, and 12 restriction rules.

- **Method**: `GET`
- **Endpoint**: `/api/metadata`

### Example Response (200 OK)
```json
{
  "brands": [
    { "brand_id": 1, "brand_name": "4700BC" },
    { "brand_id": 2, "brand_name": "ACT II" }
  ],
  "categories": [
    { "category_id": 1, "category_name": "BISCUIT", "parent_category_id": null, "parent_name": null }
  ],
  "allergens": [
    { "allergen_id": 1, "allergen_name": "Milk" },
    { "allergen_id": 2, "allergen_name": "Soy" },
    { "allergen_id": 3, "allergen_name": "Wheat/Gluten" }
  ],
  "tags": [
    { "tag_id": 1, "tag_name": "High Sugar", "tag_type": "CONCERN" },
    { "tag_id": 7, "tag_name": "High Fibre", "tag_type": "POSITIVE" }
  ],
  "restrictions": [
    { "restriction_id": 1, "restriction_name": "Diabetes", "description": "Blood-sugar-conscious profile; flags high-sugar products." },
    { "restriction_id": 2, "restriction_name": "High Cholesterol", "description": "Flags high saturated fat / trans fat products." }
  ]
}
```

---

## 3. Product Catalogue & Search
Searches by product name or brand with pagination and filtering.

- **Method**: `GET`
- **Endpoint**: `/api/products?q=biscuit&category_id=1&sort_by=sugar_asc&page=1&page_size=2`

### Example Response (200 OK)
```json
{
  "total": 310,
  "page": 1,
  "page_size": 2,
  "total_pages": 155,
  "items": [
    {
      "product_id": 2,
      "item_name": "Britannia Nutrichoice Digestive High-Fibre Biscuits",
      "brand_id": 45,
      "brand_name": "BRITANNIA",
      "category_id": 1,
      "category_name": "BISCUIT",
      "serving_size_g": 100.0,
      "price_inr": 20.0,
      "calories": 483.0,
      "sugar": 12.7,
      "sodium": 362.0,
      "saturated_fat": 10.3,
      "protein": 9.3,
      "dietary_fibre": 6.7,
      "tags": ["High Fibre", "High Protein"],
      "dietary_types": ["Vegetarian"],
      "allergens": ["Milk", "Wheat/Gluten"]
    }
  ]
}
```

---

## 4. Deep Product Details
Returns all nutrition facts with units, full raw ingredients text, structured master ingredients, allergens, and dynamic tags.

- **Method**: `GET`
- **Endpoint**: `/api/products/1`

### Example Response (200 OK)
```json
{
  "product_id": 1,
  "item_name": "HIDE & SEEK",
  "brand_id": 180,
  "brand_name": "PARLE",
  "category_id": 1,
  "category_name": "BISCUIT",
  "serving_size_g": 100.0,
  "price_inr": 30.0,
  "ingredients_text": "REFINED WHEAT FLOUR (MAIDA), CHOCOLATE (23%) SUGAR, COCOA SOLIDS...",
  "nutrition_facts": [
    { "nutrient_id": 1, "nutrient_name": "Calories", "unit": "kcal", "amount": 479.0 },
    { "nutrient_id": 7, "nutrient_name": "Sugar", "unit": "g", "amount": 32.5 },
    { "nutrient_id": 8, "nutrient_name": "Sodium", "unit": "mg", "amount": 114.0 }
  ],
  "ingredients_list": [
    { "ingredient_id": 1, "ingredient_name": "Sugar" },
    { "ingredient_id": 3, "ingredient_name": "Maida" }
  ],
  "allergens_list": [
    { "allergen_id": 2, "allergen_name": "Soy" },
    { "allergen_id": 3, "allergen_name": "Wheat/Gluten" }
  ],
  "tags_list": [
    { "tag_id": 1, "tag_name": "High Sugar", "tag_type": "CONCERN", "source": "RULE_ENGINE" }
  ],
  "missing_nutrients": []
}
```

---

## 5. Live Restriction & Allergen Evaluation
Evaluates product suitability against user-selected health conditions and allergens.

- **Method**: `POST`
- **Endpoint**: `/api/evaluate`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "product_id": 1,
  "restriction_ids": [1, 2],
  "allergen_ids": [2]
}
```

### Example Response (200 OK)
```json
[
  {
    "product_id": 1,
    "item_name": "HIDE & SEEK",
    "brand_name": "PARLE",
    "status": "AVOID",
    "verdict": "Not Recommended: Contains ingredients matching your declared allergens.",
    "allergen_warnings": [
      {
        "title": "Contains Soy",
        "details": "This product is recorded to contain Soy. Consumption should be avoided.",
        "severity": "danger"
      }
    ],
    "restriction_flags": [
      {
        "title": "Diabetes Alert: High Sugar",
        "details": "Product contains 32.5g of Sugar, which triggers 'High Sugar' (Sugar above dataset 75th percentile).",
        "severity": "danger"
      }
    ],
    "positive_matches": [],
    "missing_data_warnings": [],
    "safety_disclaimer": "SmartRestrict analyzes packaged food label information based on database records. It does not constitute medical advice and cannot guarantee zero cross-contamination. Always inspect physical packaging before consumption if you have severe allergies."
  }
]
```

---

## 6. Healthier Alternative Recommendations
Calculates better options within the category, comparing nutritional improvements and trade-offs.

- **Method**: `GET`
- **Endpoint**: `/api/products/1/alternatives?restriction_ids=1&limit=3`

### Example Response (200 OK)
```json
[
  {
    "product_id": 2,
    "item_name": "Britannia Nutrichoice Digestive High-Fibre Biscuits",
    "brand_name": "BRITANNIA",
    "category_name": "BISCUIT",
    "price_inr": 20.0,
    "serving_size_g": 100.0,
    "suitability_status": "SUITABLE",
    "alternative_score": 87.2,
    "comparison_points": [
      "61% less sugar (12.7g vs 32.5g per 100g)",
      "Higher dietary fibre (6.7g vs 0.0g)",
      "Higher protein (9.3g vs 5.9g)"
    ],
    "trade_offs": [
      "Higher sodium content (+248mg)"
    ],
    "nutrition_comparison": {
      "calories": 483.0,
      "sugar": 12.7,
      "sodium": 362.0,
      "saturated_fat": 10.3,
      "protein": 9.3,
      "dietary_fibre": 6.7
    },
    "tags": ["High Fibre", "High Protein"]
  }
]
```

---

## 7. User Profile & Saved Restrictions
Creates or updates a profile in the Oracle `USERS` and `USER_RESTRICTIONS` tables.

- **Method**: `POST`
- **Endpoint**: `/api/users/profile`
- **Headers**: `Content-Type: application/json`
- **Body**:
```json
{
  "user_name": "Subi W",
  "email": "subi@example.com",
  "restriction_ids": [1, 5]
}
```

### Example Response (200 OK)
```json
{
  "user_id": 1,
  "user_name": "Subi W",
  "email": "subi@example.com",
  "created_on": "2026-10-17 16:30:00",
  "restrictions": [
    { "restriction_id": 1, "restriction_name": "Diabetes", "description": "Blood-sugar-conscious profile; flags high-sugar products." },
    { "restriction_id": 5, "restriction_name": "Gluten Intolerance", "description": "Flags products containing wheat/gluten ingredients." }
  ]
}
```

