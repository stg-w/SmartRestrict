import pytest
from backend.services.rule_engine import RuleEngine

@pytest.fixture
def test_engine():
    engine = RuleEngine()
    # Mock master rules so tests run deterministically and fast
    engine._tag_rules_cache = [
        {"tag_rule_id": 1, "tag_id": 1, "tag_name": "High Sugar", "tag_type": "CONCERN", "nutrient_id": 7, "nutrient_name": "Sugar", "unit": "g", "operator": ">", "threshold": 33.5, "priority": 1, "description": "Sugar above 75th percentile"},
        {"tag_rule_id": 2, "tag_id": 2, "tag_name": "Low Sugar", "tag_type": "POSITIVE", "nutrient_id": 7, "nutrient_name": "Sugar", "unit": "g", "operator": "<=", "threshold": 3.5, "priority": 1, "description": "Sugar at/below 25th percentile"},
        {"tag_rule_id": 3, "tag_id": 3, "tag_name": "High Sodium", "tag_type": "CONCERN", "nutrient_id": 8, "nutrient_name": "Sodium", "unit": "mg", "operator": ">", "threshold": 385.0, "priority": 1, "description": "Sodium above 75th percentile"},
        {"tag_rule_id": 4, "tag_id": 4, "tag_name": "Low Sodium", "tag_type": "POSITIVE", "nutrient_id": 8, "nutrient_name": "Sodium", "unit": "mg", "operator": "<=", "threshold": 11.6, "priority": 1, "description": "Sodium at/below 25th percentile"},
        {"tag_rule_id": 5, "tag_id": 5, "tag_name": "High Saturated Fat", "tag_type": "CONCERN", "nutrient_id": 5, "nutrient_name": "Saturated Fat", "unit": "g", "operator": ">", "threshold": 11.0, "priority": 1, "description": "Saturated fat above 75th percentile"},
        {"tag_rule_id": 7, "tag_id": 7, "tag_name": "High Fibre", "tag_type": "POSITIVE", "nutrient_id": 9, "nutrient_name": "Dietary Fibre", "unit": "g", "operator": ">", "threshold": 0.8, "priority": 1, "description": "Dietary fibre above 75th percentile"},
        {"tag_rule_id": 8, "tag_id": 8, "tag_name": "High Protein", "tag_type": "POSITIVE", "nutrient_id": 3, "nutrient_name": "Protein", "unit": "g", "operator": ">", "threshold": 7.8, "priority": 1, "description": "Protein above 75th percentile"},
        {"tag_rule_id": 11, "tag_id": 11, "tag_name": "Contains Trans Fat", "tag_type": "CONCERN", "nutrient_id": 6, "nutrient_name": "Trans Fat", "unit": "g", "operator": ">", "threshold": 0.0, "priority": 1, "description": "Any measurable trans fat content"}
    ]
    engine._restriction_rules_cache = [
        {"restriction_rule_id": 1, "restriction_id": 1, "restriction_name": "Diabetes", "tag_id": 1, "tag_name": "High Sugar", "tag_type": "CONCERN", "impact": "NEGATIVE"},
        {"restriction_rule_id": 2, "restriction_id": 1, "restriction_name": "Diabetes", "tag_id": 2, "tag_name": "Low Sugar", "tag_type": "POSITIVE", "impact": "POSITIVE"},
        {"restriction_rule_id": 4, "restriction_id": 2, "restriction_name": "High Cholesterol", "tag_id": 5, "tag_name": "High Saturated Fat", "tag_type": "CONCERN", "impact": "NEGATIVE"},
        {"restriction_rule_id": 5, "restriction_id": 2, "restriction_name": "High Cholesterol", "tag_id": 11, "tag_name": "Contains Trans Fat", "tag_type": "CONCERN", "impact": "NEGATIVE"},
        {"restriction_rule_id": 7, "restriction_id": 3, "restriction_name": "Low Sodium Diet", "tag_id": 3, "tag_name": "High Sodium", "tag_type": "CONCERN", "impact": "NEGATIVE"}
    ]
    engine._allergens_cache = {
        1: "Milk", 2: "Soy", 3: "Wheat/Gluten", 4: "Egg", 5: "Peanut"
    }
    return engine

def test_dynamic_tags_high_sugar(test_engine):
    nutrition = {7: 45.0}  # Sugar = 45g (> 33.5)
    tags = test_engine.evaluate_tags_for_nutrition(nutrition)
    tag_names = [t["tag_name"] for t in tags]
    assert "High Sugar" in tag_names
    assert "Low Sugar" not in tag_names

def test_dynamic_tags_low_sugar(test_engine):
    nutrition = {7: 2.0}  # Sugar = 2g (<= 3.5)
    tags = test_engine.evaluate_tags_for_nutrition(nutrition)
    tag_names = [t["tag_name"] for t in tags]
    assert "Low Sugar" in tag_names
    assert "High Sugar" not in tag_names

def test_allergen_avoid_flag(test_engine):
    product = {"product_id": 1, "item_name": "Milk Chocolate", "brand_name": "Amul", "ingredients_text": "Milk solids, cocoa"}
    allergens = [{"allergen_id": 1, "allergen_name": "Milk"}]
    res = test_engine.evaluate_product_suitability(
        product=product,
        nutrition_list=[],
        product_allergens=allergens,
        product_tags=[],
        product_ingredients=[],
        user_restriction_ids=[],
        user_allergen_ids=[1]  # User restricts Milk
    )
    assert res.status == "AVOID"
    assert len(res.allergen_warnings) > 0
    assert any("Milk" in w.title for w in res.allergen_warnings)

def test_restriction_evaluation_diabetes(test_engine):
    product = {"product_id": 2, "item_name": "Sugary Biscuit", "brand_name": "TestBrand", "ingredients_text": "Sugar, flour"}
    nutrition = [{"nutrient_id": 7, "amount": 40.0}]  # High Sugar
    res = test_engine.evaluate_product_suitability(
        product=product,
        nutrition_list=nutrition,
        product_allergens=[],
        product_tags=[],
        product_ingredients=[],
        user_restriction_ids=[1],  # Diabetes
        user_allergen_ids=[]
    )
    assert res.status == "AVOID"
    assert any("High Sugar" in f.title for f in res.restriction_flags)

def test_missing_data_warnings(test_engine):
    product = {"product_id": 3, "item_name": "Unknown Product", "brand_name": "TestBrand", "ingredients_text": ""}
    res = test_engine.evaluate_product_suitability(
        product=product,
        nutrition_list=[],  # Completely empty nutrition
        product_allergens=[],
        product_tags=[],
        product_ingredients=[],
        user_restriction_ids=[1],
        user_allergen_ids=[]
    )
    # Missing data should be explicitly flagged
    assert len(res.missing_data_warnings) > 0
    # Must contain safety disclaimer
    assert "SmartRestrict analyzes packaged food label information" in res.safety_disclaimer

