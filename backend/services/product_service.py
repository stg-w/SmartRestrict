import logging
from typing import Optional, Any
from backend.database import get_db_connection, rows_to_dicts, row_to_dict
from backend.models import (
    ProductSummary, ProductDetail, PaginatedProductsResponse,
    ProductNutritionFact, IngredientItem, AllergenItem, DietaryTypeItem, TagItem
)
from backend.services.rule_engine import rule_engine

logger = logging.getLogger("smartrestrict.product_service")

class ProductService:
    """Service layer for fetching product catalog, details, and metadata from Oracle."""

    def get_products(
        self,
        q: Optional[str] = None,
        category_id: Optional[int] = None,
        brand_id: Optional[int] = None,
        dietary_type_id: Optional[int] = None,
        tag_id: Optional[int] = None,
        sort_by: str = "name_asc",
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedProductsResponse:
        """Fetch filtered, searched, and paginated products."""
        offset = (page - 1) * page_size
        where_clauses = ["1=1"]
        params: dict[str, Any] = {}

        if q and q.strip():
            clean_q = f"%{q.strip().lower()}%"
            where_clauses.append("(LOWER(p.ITEM_NAME) LIKE :search_q OR LOWER(b.BRAND_NAME) LIKE :search_q)")
            params["search_q"] = clean_q

        if category_id:
            where_clauses.append("(p.CATEGORY_ID = :cat_id OR c.PARENT_CATEGORY_ID = :cat_id)")
            params["cat_id"] = category_id

        if brand_id:
            where_clauses.append("p.BRAND_ID = :brand_id")
            params["brand_id"] = brand_id

        if dietary_type_id:
            where_clauses.append("""
                EXISTS (
                    SELECT 1 FROM PRODUCT_DIETARY_TYPES pdt 
                    WHERE pdt.PRODUCT_ID = p.PRODUCT_ID AND pdt.DIETARY_TYPE_ID = :diet_id
                )
            """)
            params["diet_id"] = dietary_type_id

        if tag_id:
            where_clauses.append("""
                EXISTS (
                    SELECT 1 FROM PRODUCT_TAGS pt 
                    WHERE pt.PRODUCT_ID = p.PRODUCT_ID AND pt.TAG_ID = :tag_id
                )
            """)
            params["tag_id"] = tag_id

        where_sql = " AND ".join(where_clauses)

        # Determine sorting
        sort_order = "p.ITEM_NAME ASC"
        if sort_by == "name_desc":
            sort_order = "p.ITEM_NAME DESC"
        elif sort_by == "price_asc":
            sort_order = "p.PRICE_INR ASC NULLS LAST"
        elif sort_by == "price_desc":
            sort_order = "p.PRICE_INR DESC NULLS LAST"
        elif sort_by == "calories_asc":
            sort_order = "cal.AMOUNT ASC NULLS LAST"
        elif sort_by == "sugar_asc":
            sort_order = "sug.AMOUNT ASC NULLS LAST"
        elif sort_by == "sodium_asc":
            sort_order = "sod.AMOUNT ASC NULLS LAST"
        elif sort_by == "protein_desc":
            sort_order = "pro.AMOUNT DESC NULLS LAST"

        count_sql = f"""
            SELECT COUNT(*) 
            FROM PRODUCTS p
            JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
            JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
            WHERE {where_sql}
        """

        select_sql = f"""
            SELECT p.PRODUCT_ID, p.ITEM_NAME, p.BRAND_ID, b.BRAND_NAME,
                   p.CATEGORY_ID, c.CATEGORY_NAME, p.SERVING_SIZE_G, p.PRICE_INR,
                   cal.AMOUNT AS calories,
                   sug.AMOUNT AS sugar,
                   sod.AMOUNT AS sodium,
                   sf.AMOUNT AS saturated_fat,
                   pro.AMOUNT AS protein,
                   fib.AMOUNT AS dietary_fibre
            FROM PRODUCTS p
            JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
            JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
            LEFT JOIN PRODUCT_NUTRITION cal ON p.PRODUCT_ID = cal.PRODUCT_ID AND cal.NUTRIENT_ID = 1
            LEFT JOIN PRODUCT_NUTRITION sug ON p.PRODUCT_ID = sug.PRODUCT_ID AND sug.NUTRIENT_ID = 7
            LEFT JOIN PRODUCT_NUTRITION sod ON p.PRODUCT_ID = sod.PRODUCT_ID AND sod.NUTRIENT_ID = 8
            LEFT JOIN PRODUCT_NUTRITION sf  ON p.PRODUCT_ID = sf.PRODUCT_ID AND sf.NUTRIENT_ID = 5
            LEFT JOIN PRODUCT_NUTRITION pro ON p.PRODUCT_ID = pro.PRODUCT_ID AND pro.NUTRIENT_ID = 3
            LEFT JOIN PRODUCT_NUTRITION fib ON p.PRODUCT_ID = fib.PRODUCT_ID AND fib.NUTRIENT_ID = 9
            WHERE {where_sql}
            ORDER BY {sort_order}
            OFFSET :offset_val ROWS FETCH NEXT :limit_val ROWS ONLY
        """

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Count
                cur.execute(count_sql, params)
                total = cur.fetchone()[0]

                # Data
                data_params = dict(params)
                data_params["offset_val"] = offset
                data_params["limit_val"] = page_size
                cur.execute(select_sql, data_params)
                product_rows = rows_to_dicts(cur)

                if not product_rows:
                    return PaginatedProductsResponse(
                        total=total,
                        page=page,
                        page_size=page_size,
                        total_pages=(total + page_size - 1) // page_size if page_size > 0 else 0,
                        items=[]
                    )

                product_ids = [p["product_id"] for p in product_rows]

                # Batch fetch tags, dietary types, and allergens
                cur.execute(f"""
                    SELECT pt.PRODUCT_ID, t.TAG_NAME
                    FROM PRODUCT_TAGS pt
                    JOIN TAGS t ON pt.TAG_ID = t.TAG_ID
                    WHERE pt.PRODUCT_ID IN ({','.join([':p' + str(i) for i in range(len(product_ids))])})
                """, {f"p{i}": pid for i, pid in enumerate(product_ids)})
                tags_by_prod: dict[int, list[str]] = {}
                for pid, tname in cur.fetchall():
                    tags_by_prod.setdefault(pid, []).append(tname)

                cur.execute(f"""
                    SELECT pdt.PRODUCT_ID, dt.TYPE_NAME
                    FROM PRODUCT_DIETARY_TYPES pdt
                    JOIN DIETARY_TYPES dt ON pdt.DIETARY_TYPE_ID = dt.DIETARY_TYPE_ID
                    WHERE pdt.PRODUCT_ID IN ({','.join([':p' + str(i) for i in range(len(product_ids))])})
                """, {f"p{i}": pid for i, pid in enumerate(product_ids)})
                diet_by_prod: dict[int, list[str]] = {}
                for pid, dname in cur.fetchall():
                    diet_by_prod.setdefault(pid, []).append(dname)

                cur.execute(f"""
                    SELECT pa.PRODUCT_ID, a.ALLERGEN_NAME
                    FROM PRODUCT_ALLERGENS pa
                    JOIN ALLERGENS a ON pa.ALLERGEN_ID = a.ALLERGEN_ID
                    WHERE pa.PRODUCT_ID IN ({','.join([':p' + str(i) for i in range(len(product_ids))])})
                """, {f"p{i}": pid for i, pid in enumerate(product_ids)})
                all_by_prod: dict[int, list[str]] = {}
                for pid, aname in cur.fetchall():
                    all_by_prod.setdefault(pid, []).append(aname)

                items = []
                for p in product_rows:
                    pid = p["product_id"]
                    items.append(ProductSummary(
                        product_id=pid,
                        item_name=p["item_name"],
                        brand_id=p["brand_id"],
                        brand_name=p["brand_name"],
                        category_id=p["category_id"],
                        category_name=p["category_name"],
                        serving_size_g=float(p["serving_size_g"]) if p["serving_size_g"] is not None else None,
                        price_inr=float(p["price_inr"]) if p["price_inr"] is not None else None,
                        calories=float(p["calories"]) if p["calories"] is not None else None,
                        sugar=float(p["sugar"]) if p["sugar"] is not None else None,
                        sodium=float(p["sodium"]) if p["sodium"] is not None else None,
                        saturated_fat=float(p["saturated_fat"]) if p["saturated_fat"] is not None else None,
                        protein=float(p["protein"]) if p["protein"] is not None else None,
                        dietary_fibre=float(p["dietary_fibre"]) if p["dietary_fibre"] is not None else None,
                        tags=tags_by_prod.get(pid, []),
                        dietary_types=diet_by_prod.get(pid, []),
                        allergens=all_by_prod.get(pid, [])
                    ))

                total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
                return PaginatedProductsResponse(
                    total=total,
                    page=page,
                    page_size=page_size,
                    total_pages=total_pages,
                    items=items
                )

    def get_product_detail(self, product_id: int) -> Optional[ProductDetail]:
        """Fetch deep product data including nutrition facts, ingredients, allergens, and tags."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # 1. Base product info
                cur.execute("""
                    SELECT p.PRODUCT_ID, p.ITEM_NAME, p.BRAND_ID, b.BRAND_NAME,
                           p.CATEGORY_ID, c.CATEGORY_NAME, p.SERVING_SIZE_G, p.PRICE_INR,
                           p.INGREDIENTS_TEXT, p.VITAMIN_INFO, p.SOURCE_OF_DATA,
                           p.COLLECTION_DATE, p.COLLECTED_BY, p.REMARKS
                    FROM PRODUCTS p
                    LEFT JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                    LEFT JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                    WHERE p.PRODUCT_ID = :pid
                """, {"pid": product_id})
                base = row_to_dict(cur, cur.fetchone())
                if not base:
                    return None

                # 2. Nutrition facts
                cur.execute("""
                    SELECT n.NUTRIENT_ID, n.NUTRIENT_NAME, n.UNIT, pn.AMOUNT
                    FROM NUTRIENTS n
                    LEFT JOIN PRODUCT_NUTRITION pn ON n.NUTRIENT_ID = pn.NUTRIENT_ID AND pn.PRODUCT_ID = :pid
                    ORDER BY n.NUTRIENT_ID
                """, {"pid": product_id})
                nutrients_raw = rows_to_dicts(cur)
                nutrition_facts = []
                missing_nutrients = []
                nut_map = {}
                for n in nutrients_raw:
                    amt = float(n["amount"]) if n["amount"] is not None else None
                    if amt is None:
                        missing_nutrients.append(n["nutrient_name"])
                    else:
                        nut_map[n["nutrient_id"]] = amt
                    nutrition_facts.append(ProductNutritionFact(
                        nutrient_id=n["nutrient_id"],
                        nutrient_name=n["nutrient_name"],
                        unit=n["unit"],
                        amount=amt
                    ))

                # 3. Ingredients list
                cur.execute("""
                    SELECT i.INGREDIENT_ID, i.INGREDIENT_NAME
                    FROM PRODUCT_INGREDIENTS pi
                    JOIN INGREDIENTS i ON pi.INGREDIENT_ID = i.INGREDIENT_ID
                    WHERE pi.PRODUCT_ID = :pid
                    ORDER BY i.INGREDIENT_NAME
                """, {"pid": product_id})
                ingredients_list = [
                    IngredientItem(ingredient_id=r["ingredient_id"], ingredient_name=r["ingredient_name"])
                    for r in rows_to_dicts(cur)
                ]

                # 4. Allergens list
                cur.execute("""
                    SELECT a.ALLERGEN_ID, a.ALLERGEN_NAME
                    FROM PRODUCT_ALLERGENS pa
                    JOIN ALLERGENS a ON pa.ALLERGEN_ID = a.ALLERGEN_ID
                    WHERE pa.PRODUCT_ID = :pid
                    ORDER BY a.ALLERGEN_NAME
                """, {"pid": product_id})
                allergens_list = [
                    AllergenItem(allergen_id=r["allergen_id"], allergen_name=r["allergen_name"])
                    for r in rows_to_dicts(cur)
                ]

                # 5. Dietary types list
                cur.execute("""
                    SELECT dt.DIETARY_TYPE_ID, dt.TYPE_NAME
                    FROM PRODUCT_DIETARY_TYPES pdt
                    JOIN DIETARY_TYPES dt ON pdt.DIETARY_TYPE_ID = dt.DIETARY_TYPE_ID
                    WHERE pdt.PRODUCT_ID = :pid
                    ORDER BY dt.TYPE_NAME
                """, {"pid": product_id})
                dietary_types_list = [
                    DietaryTypeItem(dietary_type_id=r["dietary_type_id"], type_name=r["type_name"])
                    for r in rows_to_dicts(cur)
                ]

                # 6. Stored tags
                cur.execute("""
                    SELECT t.TAG_ID, t.TAG_NAME, t.TAG_TYPE, pt.GENERATED_DATE, pt.SOURCE
                    FROM PRODUCT_TAGS pt
                    JOIN TAGS t ON pt.TAG_ID = t.TAG_ID
                    WHERE pt.PRODUCT_ID = :pid
                    ORDER BY t.TAG_TYPE, t.TAG_NAME
                """, {"pid": product_id})
                tags_list = [
                    TagItem(
                        tag_id=r["tag_id"],
                        tag_name=r["tag_name"],
                        tag_type=r["tag_type"],
                        generated_date=str(r["generated_date"]) if r["generated_date"] else None,
                        source=r["source"]
                    )
                    for r in rows_to_dicts(cur)
                ]

                # Dynamic tags addition if missing from stored tags
                existing_tag_ids = {t.tag_id for t in tags_list}
                dyn_tags = rule_engine.evaluate_tags_for_nutrition(nut_map)
                for dt in dyn_tags:
                    if dt["tag_id"] not in existing_tag_ids:
                        tags_list.append(TagItem(
                            tag_id=dt["tag_id"],
                            tag_name=dt["tag_name"],
                            tag_type=dt["tag_type"],
                            generated_date=None,
                            source="RULE_ENGINE_DYNAMIC"
                        ))

                return ProductDetail(
                    product_id=base["product_id"],
                    item_name=base["item_name"],
                    brand_id=base["brand_id"],
                    brand_name=base["brand_name"],
                    category_id=base["category_id"],
                    category_name=base["category_name"],
                    serving_size_g=float(base["serving_size_g"]) if base["serving_size_g"] is not None else None,
                    price_inr=float(base["price_inr"]) if base["price_inr"] is not None else None,
                    ingredients_text=base["ingredients_text"],
                    vitamin_info=base["vitamin_info"],
                    source_of_data=base["source_of_data"],
                    collection_date=str(base["collection_date"]) if base["collection_date"] else None,
                    collected_by=base["collected_by"],
                    remarks=base["remarks"],
                    calories=nut_map.get(1),
                    sugar=nut_map.get(7),
                    sodium=nut_map.get(8),
                    saturated_fat=nut_map.get(5),
                    protein=nut_map.get(3),
                    dietary_fibre=nut_map.get(9),
                    tags=[t.tag_name for t in tags_list],
                    dietary_types=[dt.type_name for dt in dietary_types_list],
                    allergens=[a.allergen_name for a in allergens_list],
                    nutrition_facts=nutrition_facts,
                    ingredients_list=ingredients_list,
                    allergens_list=allergens_list,
                    dietary_types_list=dietary_types_list,
                    tags_list=tags_list,
                    missing_nutrients=missing_nutrients
                )

    def get_metadata(self) -> dict[str, Any]:
        """Fetch all metadata: brands, categories, nutrients, allergens, dietary types, tags, restrictions."""
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT BRAND_ID, BRAND_NAME FROM BRANDS ORDER BY BRAND_NAME")
                brands = rows_to_dicts(cur)

                cur.execute("""
                    SELECT c.CATEGORY_ID, c.CATEGORY_NAME, c.PARENT_CATEGORY_ID, p.CATEGORY_NAME AS PARENT_NAME
                    FROM CATEGORIES c
                    LEFT JOIN CATEGORIES p ON c.PARENT_CATEGORY_ID = p.CATEGORY_ID
                    ORDER BY c.CATEGORY_NAME
                """)
                categories = rows_to_dicts(cur)

                cur.execute("SELECT ALLERGEN_ID, ALLERGEN_NAME FROM ALLERGENS ORDER BY ALLERGEN_ID")
                allergens = rows_to_dicts(cur)

                cur.execute("SELECT DIETARY_TYPE_ID, TYPE_NAME FROM DIETARY_TYPES ORDER BY DIETARY_TYPE_ID")
                dietary_types = rows_to_dicts(cur)

                cur.execute("SELECT TAG_ID, TAG_NAME, TAG_TYPE FROM TAGS ORDER BY TAG_ID")
                tags = rows_to_dicts(cur)

                cur.execute("SELECT RESTRICTION_ID, RESTRICTION_NAME, DESCRIPTION FROM RESTRICTIONS ORDER BY RESTRICTION_ID")
                restrictions = rows_to_dicts(cur)

                cur.execute("SELECT NUTRIENT_ID, NUTRIENT_NAME, UNIT FROM NUTRIENTS ORDER BY NUTRIENT_ID")
                nutrients = rows_to_dicts(cur)

                cur.execute("""
                    SELECT tr.TAG_RULE_ID, tr.TAG_ID, t.TAG_NAME, t.TAG_TYPE,
                           tr.NUTRIENT_ID, n.NUTRIENT_NAME, n.UNIT,
                           tr.OPERATOR, tr.THRESHOLD, tr.PRIORITY, tr.DESCRIPTION
                    FROM TAG_RULES tr
                    JOIN TAGS t ON tr.TAG_ID = t.TAG_ID
                    JOIN NUTRIENTS n ON tr.NUTRIENT_ID = n.NUTRIENT_ID
                    ORDER BY tr.TAG_RULE_ID
                """)
                tag_rules = rows_to_dicts(cur)

                cur.execute("""
                    SELECT rr.RESTRICTION_RULE_ID, rr.RESTRICTION_ID, r.RESTRICTION_NAME,
                           rr.TAG_ID, t.TAG_NAME, rr.IMPACT
                    FROM RESTRICTION_RULES rr
                    JOIN RESTRICTIONS r ON rr.RESTRICTION_ID = r.RESTRICTION_ID
                    JOIN TAGS t ON rr.TAG_ID = t.TAG_ID
                    ORDER BY rr.RESTRICTION_RULE_ID
                """)
                restriction_rules = rows_to_dicts(cur)

                return {
                    "brands": brands,
                    "categories": categories,
                    "allergens": allergens,
                    "dietary_types": dietary_types,
                    "tags": tags,
                    "restrictions": restrictions,
                    "nutrients": nutrients,
                    "tag_rules": tag_rules,
                    "restriction_rules": restriction_rules
                }

product_service = ProductService()
