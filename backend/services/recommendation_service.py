import logging
from typing import Optional, Any
from backend.database import get_db_connection, rows_to_dicts
from backend.models import AlternativeItem
from backend.services.rule_engine import rule_engine

logger = logging.getLogger("smartrestrict.recommendation_service")

class RecommendationService:
    """Calculates explainable healthier alternatives based on live database records."""

    def get_alternatives(
        self,
        product_id: int,
        user_restriction_ids: Optional[list[int]] = None,
        user_allergen_ids: Optional[list[int]] = None,
        limit: int = 5
    ) -> list[AlternativeItem]:
        user_restriction_ids = user_restriction_ids or []
        user_allergen_ids = user_allergen_ids or []

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Fetch target product details
                cur.execute("""
                    SELECT p.PRODUCT_ID, p.ITEM_NAME, p.BRAND_ID, b.BRAND_NAME,
                           p.CATEGORY_ID, c.CATEGORY_NAME, c.PARENT_CATEGORY_ID,
                           p.SERVING_SIZE_G, p.PRICE_INR, p.INGREDIENTS_TEXT
                    FROM PRODUCTS p
                    JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                    JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                    WHERE p.PRODUCT_ID = :pid
                """, {"pid": product_id})
                target = rows_to_dicts(cur)
                if not target:
                    return []
                target_prod = target[0]

                # Fetch target nutrition
                cur.execute("""
                    SELECT NUTRIENT_ID, AMOUNT FROM PRODUCT_NUTRITION WHERE PRODUCT_ID = :pid
                """, {"pid": product_id})
                target_nut = {r["nutrient_id"]: float(r["amount"]) for r in rows_to_dicts(cur) if r["amount"] is not None}

                cat_id = target_prod["category_id"]
                parent_cat_id = target_prod.get("parent_category_id")

                # 2. Fetch candidate alternatives in same category or parent category
                cur.execute("""
                    SELECT p.PRODUCT_ID, p.ITEM_NAME, p.BRAND_ID, b.BRAND_NAME,
                           p.CATEGORY_ID, c.CATEGORY_NAME, c.PARENT_CATEGORY_ID,
                           p.SERVING_SIZE_G, p.PRICE_INR, p.INGREDIENTS_TEXT,
                           cal.AMOUNT AS calories,
                           sug.AMOUNT AS sugar,
                           sod.AMOUNT AS sodium,
                           sf.AMOUNT AS saturated_fat,
                           pro.AMOUNT AS protein,
                           fib.AMOUNT AS dietary_fibre,
                           tf.AMOUNT AS trans_fat
                    FROM PRODUCTS p
                    JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                    JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                    LEFT JOIN PRODUCT_NUTRITION cal ON p.PRODUCT_ID = cal.PRODUCT_ID AND cal.NUTRIENT_ID = 1
                    LEFT JOIN PRODUCT_NUTRITION sug ON p.PRODUCT_ID = sug.PRODUCT_ID AND sug.NUTRIENT_ID = 7
                    LEFT JOIN PRODUCT_NUTRITION sod ON p.PRODUCT_ID = sod.PRODUCT_ID AND sod.NUTRIENT_ID = 8
                    LEFT JOIN PRODUCT_NUTRITION sf  ON p.PRODUCT_ID = sf.PRODUCT_ID AND sf.NUTRIENT_ID = 5
                    LEFT JOIN PRODUCT_NUTRITION pro ON p.PRODUCT_ID = pro.PRODUCT_ID AND pro.NUTRIENT_ID = 3
                    LEFT JOIN PRODUCT_NUTRITION fib ON p.PRODUCT_ID = fib.PRODUCT_ID AND fib.NUTRIENT_ID = 9
                    LEFT JOIN PRODUCT_NUTRITION tf  ON p.PRODUCT_ID = tf.PRODUCT_ID AND tf.NUTRIENT_ID = 6
                    WHERE p.PRODUCT_ID != :target_id
                      AND (p.CATEGORY_ID = :cat_id OR (:parent_id IS NOT NULL AND (c.CATEGORY_ID = :parent_id OR c.PARENT_CATEGORY_ID = :parent_id)))
                """, {
                    "target_id": product_id,
                    "cat_id": cat_id,
                    "parent_id": parent_cat_id
                })
                candidates = rows_to_dicts(cur)

                if not candidates:
                    # Fallback to broader category search if direct subcategory is small
                    cur.execute("""
                        SELECT p.PRODUCT_ID, p.ITEM_NAME, p.BRAND_ID, b.BRAND_NAME,
                               p.CATEGORY_ID, c.CATEGORY_NAME, c.PARENT_CATEGORY_ID,
                               p.SERVING_SIZE_G, p.PRICE_INR, p.INGREDIENTS_TEXT,
                               cal.AMOUNT AS calories,
                               sug.AMOUNT AS sugar,
                               sod.AMOUNT AS sodium,
                               sf.AMOUNT AS saturated_fat,
                               pro.AMOUNT AS protein,
                               fib.AMOUNT AS dietary_fibre,
                               tf.AMOUNT AS trans_fat
                        FROM PRODUCTS p
                        JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                        JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                        LEFT JOIN PRODUCT_NUTRITION cal ON p.PRODUCT_ID = cal.PRODUCT_ID AND cal.NUTRIENT_ID = 1
                        LEFT JOIN PRODUCT_NUTRITION sug ON p.PRODUCT_ID = sug.PRODUCT_ID AND sug.NUTRIENT_ID = 7
                        LEFT JOIN PRODUCT_NUTRITION sod ON p.PRODUCT_ID = sod.PRODUCT_ID AND sod.NUTRIENT_ID = 8
                        LEFT JOIN PRODUCT_NUTRITION sf  ON p.PRODUCT_ID = sf.PRODUCT_ID AND sf.NUTRIENT_ID = 5
                        LEFT JOIN PRODUCT_NUTRITION pro ON p.PRODUCT_ID = pro.PRODUCT_ID AND pro.NUTRIENT_ID = 3
                        LEFT JOIN PRODUCT_NUTRITION fib ON p.PRODUCT_ID = fib.PRODUCT_ID AND fib.NUTRIENT_ID = 9
                        LEFT JOIN PRODUCT_NUTRITION tf  ON p.PRODUCT_ID = tf.PRODUCT_ID AND tf.NUTRIENT_ID = 6
                        WHERE p.PRODUCT_ID != :target_id
                        FETCH FIRST 50 ROWS ONLY
                    """, {"target_id": product_id})
                    candidates = rows_to_dicts(cur)

                if not candidates:
                    return []

                cand_ids = [c["product_id"] for c in candidates]

                # Fetch candidate allergens
                cur.execute(f"""
                    SELECT pa.PRODUCT_ID, pa.ALLERGEN_ID
                    FROM PRODUCT_ALLERGENS pa
                    WHERE pa.PRODUCT_ID IN ({','.join([':p' + str(i) for i in range(len(cand_ids))])})
                """, {f"p{i}": cid for i, cid in enumerate(cand_ids)})
                cand_allergens: dict[int, set[int]] = {}
                for pid, aid in cur.fetchall():
                    cand_allergens.setdefault(pid, set()).add(aid)

                # Fetch candidate tags
                cur.execute(f"""
                    SELECT pt.PRODUCT_ID, t.TAG_ID, t.TAG_NAME, t.TAG_TYPE
                    FROM PRODUCT_TAGS pt
                    JOIN TAGS t ON pt.TAG_ID = t.TAG_ID
                    WHERE pt.PRODUCT_ID IN ({','.join([':p' + str(i) for i in range(len(cand_ids))])})
                """, {f"p{i}": cid for i, cid in enumerate(cand_ids)})
                cand_tags: dict[int, list[dict[str, Any]]] = {}
                for pid, tid, tname, ttype in cur.fetchall():
                    cand_tags.setdefault(pid, []).append({"tag_id": tid, "tag_name": tname, "tag_type": ttype})

        # 3. Score and evaluate each candidate
        scored_alternatives: list[AlternativeItem] = []

        t_sug = target_nut.get(7)
        t_sf = target_nut.get(5)
        t_sod = target_nut.get(8)
        t_cal = target_nut.get(1)
        t_pro = target_nut.get(3)
        t_fib = target_nut.get(9)

        for c in candidates:
            cid = c["product_id"]
            c_all = cand_allergens.get(cid, set())
            c_tags = cand_tags.get(cid, [])
            c_tag_names = [t["tag_name"] for t in c_tags]
            c_tag_ids = {t["tag_id"] for t in c_tags}

            # Filter out any candidate with user-declared allergens
            if any(u_a in c_all for u_a in user_allergen_ids):
                continue

            # Filter out candidate if it violates active restrictions
            # (e.g. Diabetes user -> discard candidate with High Sugar)
            if 1 in user_restriction_ids and 1 in c_tag_ids:  # High Sugar
                continue
            if 2 in user_restriction_ids and (5 in c_tag_ids or 11 in c_tag_ids):  # High Sat Fat / Trans Fat
                continue
            if 3 in user_restriction_ids and 3 in c_tag_ids:  # High Sodium
                continue
            if 5 in user_restriction_ids and 3 in c_all:  # Wheat/Gluten
                continue

            # Candidate nutrition
            c_sug = float(c["sugar"]) if c["sugar"] is not None else None
            c_sf = float(c["saturated_fat"]) if c["saturated_fat"] is not None else None
            c_sod = float(c["sodium"]) if c["sodium"] is not None else None
            c_cal = float(c["calories"]) if c["calories"] is not None else None
            c_pro = float(c["protein"]) if c["protein"] is not None else None
            c_fib = float(c["dietary_fibre"]) if c["dietary_fibre"] is not None else None

            score = 50.0
            comparisons: list[str] = []
            trade_offs: list[str] = []

            # Sugar evaluation
            if t_sug is not None and c_sug is not None:
                diff = t_sug - c_sug
                if diff > 0.5:
                    pct = int(round((diff / (t_sug if t_sug > 0 else 1.0)) * 100))
                    score += min(25.0, (diff / (t_sug + 1.0)) * 25.0)
                    comparisons.append(f"{pct}% less sugar ({c_sug}g vs {t_sug}g per 100g)")
                elif diff < -2.0:
                    score -= 10.0
                    trade_offs.append(f"Higher sugar content (+{abs(round(diff, 1))}g)")

            # Saturated fat evaluation
            if t_sf is not None and c_sf is not None:
                diff = t_sf - c_sf
                if diff > 0.5:
                    score += min(15.0, (diff / (t_sf + 1.0)) * 15.0)
                    comparisons.append(f"Lower saturated fat ({c_sf}g vs {t_sf}g)")
                elif diff < -1.0:
                    score -= 8.0
                    trade_offs.append(f"Higher saturated fat (+{abs(round(diff, 1))}g)")

            # Sodium evaluation
            if t_sod is not None and c_sod is not None:
                diff = t_sod - c_sod
                if diff > 20.0:
                    score += min(15.0, (diff / (t_sod + 1.0)) * 15.0)
                    comparisons.append(f"Lower sodium ({c_sod}mg vs {t_sod}mg)")
                elif diff < -50.0:
                    score -= 8.0
                    trade_offs.append(f"Higher sodium (+{abs(round(diff, 1))}mg)")

            # Fibre & Protein boosts
            if c_fib is not None and t_fib is not None and (c_fib - t_fib) > 0.8:
                score += 8.0
                comparisons.append(f"Higher dietary fibre ({c_fib}g vs {t_fib}g)")

            if c_pro is not None and t_pro is not None and (c_pro - t_pro) > 1.5:
                score += 8.0
                comparisons.append(f"Higher protein ({c_pro}g vs {t_pro}g)")

            # Calories comparison
            if t_cal is not None and c_cal is not None:
                diff = t_cal - c_cal
                if diff > 30.0:
                    score += min(10.0, (diff / (t_cal + 1.0)) * 10.0)
                    comparisons.append(f"Lower calories ({int(c_cal)} vs {int(t_cal)} kcal)")
                elif diff < -50.0:
                    trade_offs.append(f"Higher calories (+{abs(int(diff))} kcal)")

            # Tag bonuses and penalties
            pos_tags = [t["tag_name"] for t in c_tags if t["tag_type"] == "POSITIVE"]
            concern_tags = [t["tag_name"] for t in c_tags if t["tag_type"] == "CONCERN"]

            score += len(pos_tags) * 3.0
            score -= len(concern_tags) * 4.0

            if "Clean Ingredients" in pos_tags:
                comparisons.append("Tagged with Clean Ingredients")

            # Same sub-category bonus
            if c["category_id"] == target_prod["category_id"]:
                score += 8.0

            # Only recommend products that show genuine improvement (comparisons > 0)
            if not comparisons:
                continue

            final_score = max(10.0, min(99.0, round(score, 1)))

            suitability = "SUITABLE"
            if concern_tags:
                suitability = "CAUTION"

            scored_alternatives.append(AlternativeItem(
                product_id=cid,
                item_name=c["item_name"],
                brand_name=c["brand_name"],
                category_name=c["category_name"],
                price_inr=float(c["price_inr"]) if c["price_inr"] is not None else None,
                serving_size_g=float(c["serving_size_g"]) if c["serving_size_g"] is not None else None,
                suitability_status=suitability,
                alternative_score=final_score,
                comparison_points=comparisons,
                trade_offs=trade_offs,
                nutrition_comparison={
                    "calories": c_cal,
                    "sugar": c_sug,
                    "sodium": c_sod,
                    "saturated_fat": c_sf,
                    "protein": c_pro,
                    "dietary_fibre": c_fib
                },
                tags=c_tag_names
            ))

        # Sort by alternative score descending
        scored_alternatives.sort(key=lambda x: x.alternative_score, reverse=True)
        return scored_alternatives[:limit]

recommendation_service = RecommendationService()
