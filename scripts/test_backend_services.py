import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database import check_db_health
from backend.services.product_service import product_service
from backend.services.rule_engine import rule_engine
from backend.services.recommendation_service import recommendation_service
from backend.services.user_service import user_service

print("Testing SmartRestrict Backend Services against Oracle Database...")

# 1. Health check
health = check_db_health()
print("\n[1] DB Health Check:", health)
assert health["status"] == "healthy", "Database health check failed"

# 2. Product catalogue & pagination
prods = product_service.get_products(page=1, page_size=5)
print(f"\n[2] Fetched {len(prods.items)} products out of {prods.total}:")
for p in prods.items:
    print(f"  #{p.product_id}: {p.item_name} ({p.brand_name}) - Sugar: {p.sugar}g, Sodium: {p.sodium}mg, Tags: {p.tags}")

# 3. Product detail
test_pid = prods.items[0].product_id
detail = product_service.get_product_detail(test_pid)
print(f"\n[3] Deep Product Detail for #{test_pid} ({detail.item_name}):")
print(f"  Category: {detail.category_name}, Price: ₹{detail.price_inr}")
print(f"  Nutrients count: {len(detail.nutrition_facts)}")
print(f"  Ingredients count: {len(detail.ingredients_list)}")
print(f"  Allergens: {detail.allergens}")
print(f"  Dietary Types: {detail.dietary_types}")
print(f"  Tags: {detail.tags}")

# 4. Suitability Evaluation
eval_res = rule_engine.evaluate_product_suitability(
    product={
        "product_id": detail.product_id,
        "item_name": detail.item_name,
        "brand_name": detail.brand_name,
        "ingredients_text": detail.ingredients_text
    },
    nutrition_list=[{"nutrient_id": nf.nutrient_id, "amount": nf.amount} for nf in detail.nutrition_facts],
    product_allergens=[{"allergen_id": a.allergen_id, "allergen_name": a.allergen_name} for a in detail.allergens_list],
    product_tags=[{"tag_id": t.tag_id, "tag_name": t.tag_name, "tag_type": t.tag_type} for t in detail.tags_list],
    product_ingredients=[{"ingredient_id": i.ingredient_id, "ingredient_name": i.ingredient_name} for i in detail.ingredients_list],
    user_restriction_ids=[1, 2],  # Diabetes, High Cholesterol
    user_allergen_ids=[1]  # Milk
)
print(f"\n[4] Suitability Evaluation Result for #{test_pid}:")
print(f"  Status: {eval_res.status} | Verdict: {eval_res.verdict}")
print(f"  Allergen warnings ({len(eval_res.allergen_warnings)}): {[w.title for w in eval_res.allergen_warnings]}")
print(f"  Restriction flags ({len(eval_res.restriction_flags)}): {[f.title for f in eval_res.restriction_flags]}")
print(f"  Positive matches ({len(eval_res.positive_matches)}): {[m.title for m in eval_res.positive_matches]}")

# 5. Recommendation Engine (Healthier Alternatives)
alts = recommendation_service.get_alternatives(test_pid, user_restriction_ids=[1], limit=3)
print(f"\n[5] Healthier Alternatives for #{test_pid}: found {len(alts)}:")
for a in alts:
    print(f"  -> #{a.product_id}: {a.item_name} (Score: {a.alternative_score})")
    print(f"     Why: {a.comparison_points}")
    print(f"     Trade-offs: {a.trade_offs}")

# 6. Metadata lookup
meta = product_service.get_metadata()
print(f"\n[6] Metadata Counts: Brands={len(meta['brands'])}, Categories={len(meta['categories'])}, Restrictions={len(meta['restrictions'])}, Allergens={len(meta['allergens'])}, Tags={len(meta['tags'])}")

print("\nALL BACKEND SERVICES TESTED AND FUNCTIONAL!")
