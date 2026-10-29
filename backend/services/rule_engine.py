import logging
from typing import Optional, Any
from backend.database import get_db_connection, rows_to_dicts
from backend.models import ProductEvaluationResult, ReasonPoint

logger = logging.getLogger("smartrestrict.rule_engine")

class RuleEngine:
    """Evaluates nutrition thresholds, restriction rules, allergens, and dynamic tags."""
    
    def __init__(self):
        self._tag_rules_cache = None
        self._restriction_rules_cache = None
        self._allergens_cache = None
        self._nutrients_cache = None
        self._tags_cache = None

    def refresh_cache(self):
        """Preload master rules from Oracle."""
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    # Tag rules
                    cur.execute("""
                        SELECT tr.tag_rule_id, tr.tag_id, t.tag_name, t.tag_type,
                               tr.nutrient_id, n.nutrient_name, n.unit,
                               tr.operator, tr.threshold, tr.priority, tr.description
                        FROM TAG_RULES tr
                        JOIN TAGS t ON tr.tag_id = t.tag_id
                        JOIN NUTRIENTS n ON tr.nutrient_id = n.nutrient_id
                        ORDER BY tr.priority, tr.tag_rule_id
                    """)
                    self._tag_rules_cache = rows_to_dicts(cur)

                    # Restriction rules
                    cur.execute("""
                        SELECT rr.restriction_rule_id, rr.restriction_id, r.restriction_name,
                               rr.tag_id, t.tag_name, t.tag_type, rr.impact
                        FROM RESTRICTION_RULES rr
                        JOIN RESTRICTIONS r ON rr.restriction_id = r.restriction_id
                        JOIN TAGS t ON rr.tag_id = t.tag_id
                        ORDER BY rr.restriction_id, rr.restriction_rule_id
                    """)
                    self._restriction_rules_cache = rows_to_dicts(cur)

                    # Allergens
                    cur.execute("SELECT allergen_id, allergen_name FROM ALLERGENS ORDER BY allergen_id")
                    self._allergens_cache = {row['allergen_id']: row['allergen_name'] for row in rows_to_dicts(cur)}

                    # Nutrients
                    cur.execute("SELECT nutrient_id, nutrient_name, unit FROM NUTRIENTS ORDER BY nutrient_id")
                    self._nutrients_cache = {row['nutrient_id']: row for row in rows_to_dicts(cur)}

                    # Tags
                    cur.execute("SELECT tag_id, tag_name, tag_type FROM TAGS ORDER BY tag_id")
                    self._tags_cache = {row['tag_id']: row for row in rows_to_dicts(cur)}

            logger.info("RuleEngine cache loaded successfully from Oracle.")
        except Exception as e:
            logger.error(f"Error loading rule engine cache: {e}")

    def get_tag_rules(self) -> list[dict[str, Any]]:
        if self._tag_rules_cache is None:
            self.refresh_cache()
        return self._tag_rules_cache or []

    def get_restriction_rules(self) -> list[dict[str, Any]]:
        if self._restriction_rules_cache is None:
            self.refresh_cache()
        return self._restriction_rules_cache or []

    def evaluate_tags_for_nutrition(self, nutrition_map: dict[int, float]) -> list[dict[str, Any]]:
        """
        Dynamically evaluate which tags apply based on nutrient values and TAG_RULES.
        nutrition_map: {nutrient_id: amount}
        """
        rules = self.get_tag_rules()
        evaluated_tags = []
        for r in rules:
            n_id = r["nutrient_id"]
            if n_id not in nutrition_map or nutrition_map[n_id] is None:
                continue

            amount = float(nutrition_map[n_id])
            threshold = float(r["threshold"])
            op = r["operator"]

            matched = False
            if op == ">" and amount > threshold:
                matched = True
            elif op == ">=" and amount >= threshold:
                matched = True
            elif op == "<" and amount < threshold:
                matched = True
            elif op == "<=" and amount <= threshold:
                matched = True
            elif op == "=" and amount == threshold:
                matched = True

            if matched:
                evaluated_tags.append({
                    "tag_id": r["tag_id"],
                    "tag_name": r["tag_name"],
                    "tag_type": r["tag_type"],
                    "nutrient_id": n_id,
                    "nutrient_name": r["nutrient_name"],
                    "unit": r["unit"],
                    "amount": amount,
                    "operator": op,
                    "threshold": threshold,
                    "rule_description": r["description"]
                })
        return evaluated_tags

    def evaluate_product_suitability(
        self,
        product: dict[str, Any],
        nutrition_list: list[dict[str, Any]],
        product_allergens: list[dict[str, Any]],
        product_tags: list[dict[str, Any]],
        product_ingredients: list[dict[str, Any]],
        user_restriction_ids: list[int],
        user_allergen_ids: list[int]
    ) -> ProductEvaluationResult:
        """
        Comprehensive, explainable suitability evaluation against user restrictions and allergens.
        """
        allergen_warnings: list[ReasonPoint] = []
        restriction_flags: list[ReasonPoint] = []
        positive_matches: list[ReasonPoint] = []
        missing_data_warnings: list[str] = []

        # 1. Map existing product allergens and check against user selection
        prod_allergen_ids = {a.get("allergen_id") for a in product_allergens if a.get("allergen_id")}
        prod_allergen_names = {a.get("allergen_name") for a in product_allergens if a.get("allergen_name")}

        if not product_allergens:
            missing_data_warnings.append(
                "No specific allergen tests or label declarations recorded for this product. "
                "Absence of allergen data does not imply the product is allergen-free."
            )

        for u_all_id in user_allergen_ids:
            if u_all_id in prod_allergen_ids:
                all_name = self._allergens_cache.get(u_all_id, f"Allergen #{u_all_id}")
                allergen_warnings.append(ReasonPoint(
                    title=f"Contains {all_name}",
                    details=f"This product is recorded to contain {all_name}. Consumption should be avoided.",
                    severity="danger"
                ))

        # Check ingredients for gluten/wheat keywords if user restricted wheat/gluten
        if 3 in user_allergen_ids:  # Wheat/Gluten
            wheat_terms = ["wheat", "maida", "gluten", "atta", "semolina", "suji"]
            ing_text = (product.get("ingredients_text") or "").lower()
            for ing in product_ingredients:
                ing_text += " " + (ing.get("ingredient_name") or "").lower()
            
            if any(term in ing_text for term in wheat_terms) and not any(a.title == "Contains Wheat/Gluten" for a in allergen_warnings):
                allergen_warnings.append(ReasonPoint(
                    title="Contains Wheat / Gluten Ingredients",
                    details="Wheat/Maida derivatives identified in ingredient list. Strict caution recommended.",
                    severity="danger"
                ))

        # 2. Nutrition and Tag Evaluation
        nutrition_map = {n.get("nutrient_id"): n.get("amount") for n in nutrition_list if n.get("amount") is not None}
        missing_crucial_nutrients = []
        for n_id, name in [(7, "Sugar"), (8, "Sodium"), (5, "Saturated Fat"), (1, "Calories")]:
            if n_id not in nutrition_map:
                missing_crucial_nutrients.append(name)
        
        if missing_crucial_nutrients:
            missing_data_warnings.append(
                f"Missing nutritional data for: {', '.join(missing_crucial_nutrients)}. "
                "Missing values are not treated as zero."
            )

        # Dynamic tags evaluation
        dynamic_tags = self.evaluate_tags_for_nutrition(nutrition_map)
        dynamic_tag_ids = {t["tag_id"]: t for t in dynamic_tags}

        # Include stored tags
        stored_tag_ids = {t.get("tag_id") for t in product_tags if t.get("tag_id")}
        all_active_tag_ids = set(dynamic_tag_ids.keys()) | stored_tag_ids

        # 3. Restriction Evaluation via RESTRICTION_RULES
        r_rules = self.get_restriction_rules()
        for r_id in user_restriction_ids:
            # Special check for Gluten Intolerance restriction (r_id == 5)
            if r_id == 5:
                # Check if product contains wheat/gluten allergen or ingredients
                if 3 in prod_allergen_ids or any("wheat" in (product.get("ingredients_text") or "").lower() for _ in [1]):
                    restriction_flags.append(ReasonPoint(
                        title="Gluten Intolerance: Contains Wheat / Gluten",
                        details="Contains wheat or gluten derivatives which conflict with gluten intolerance restrictions.",
                        severity="danger"
                    ))

            rules_for_r = [r for r in r_rules if r["restriction_id"] == r_id]
            for rule in rules_for_r:
                tag_id = rule["tag_id"]
                tag_name = rule["tag_name"]
                impact = rule["impact"]
                r_name = rule["restriction_name"]

                if tag_id in all_active_tag_ids:
                    # Retrieve explanation details
                    dt = dynamic_tag_ids.get(tag_id)
                    details = ""
                    if dt:
                        details = (
                            f"Product contains {dt['amount']}{dt['unit']} of {dt['nutrient_name']}, "
                            f"which triggers '{tag_name}' ({dt['rule_description']})."
                        )
                    else:
                        details = f"Product has the '{tag_name}' tag recorded in database."

                    if impact == "NEGATIVE":
                        severity = "danger" if tag_id in (1, 3, 5, 11) else "warning"
                        restriction_flags.append(ReasonPoint(
                            title=f"{r_name} Alert: {tag_name}",
                            details=details,
                            severity=severity
                        ))
                    elif impact == "POSITIVE":
                        positive_matches.append(ReasonPoint(
                            title=f"{r_name} Positive: {tag_name}",
                            details=details,
                            severity="success"
                        ))

        # 4. Synthesize Final Verdict and Status
        if allergen_warnings:
            status = "AVOID"
            verdict = "Not Recommended: Contains ingredients matching your declared allergens."
        elif any(f.severity == "danger" for f in restriction_flags):
            status = "AVOID"
            verdict = "Not Recommended: Significantly conflicts with your active dietary restrictions."
        elif restriction_flags:
            status = "CAUTION"
            verdict = "Consume With Caution: Matches some restriction warnings."
        elif positive_matches and not restriction_flags:
            status = "SUITABLE"
            verdict = "Recommended: Aligns favorably with your active dietary profile."
        else:
            status = "SUITABLE"
            verdict = "Generally Suitable: No conflicting allergens or concern tags detected."

        return ProductEvaluationResult(
            product_id=product["product_id"],
            item_name=product["item_name"],
            brand_name=product.get("brand_name"),
            status=status,
            verdict=verdict,
            allergen_warnings=allergen_warnings,
            restriction_flags=restriction_flags,
            positive_matches=positive_matches,
            missing_data_warnings=missing_data_warnings
        )

rule_engine = RuleEngine()
