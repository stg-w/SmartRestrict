from fastapi import APIRouter, HTTPException, status
from backend.database import get_db_connection, rows_to_dicts

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get("", summary="Live database statistics and analytics")
def get_stats():
    """Return live counts, top tags, and top categories from the Oracle database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Core counts
                cur.execute("SELECT COUNT(*) FROM PRODUCTS")
                total_products = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM BRANDS")
                total_brands = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM CATEGORIES WHERE PARENT_CATEGORY_ID IS NULL"
                )
                total_parent_categories = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM CATEGORIES")
                total_categories = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM ALLERGENS")
                total_allergens = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM RESTRICTIONS")
                total_restrictions = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM PRODUCT_NUTRITION")
                total_nutrition_records = cur.fetchone()[0]

                cur.execute("SELECT COUNT(*) FROM PRODUCT_ALLERGENS")
                total_allergen_records = cur.fetchone()[0]

                # Top 5 tags by frequency
                cur.execute("""
                    SELECT t.TAG_NAME, t.TAG_TYPE, COUNT(pt.PRODUCT_ID) AS cnt
                    FROM PRODUCT_TAGS pt
                    JOIN TAGS t ON pt.TAG_ID = t.TAG_ID
                    GROUP BY t.TAG_NAME, t.TAG_TYPE
                    ORDER BY cnt DESC
                    FETCH FIRST 5 ROWS ONLY
                """)
                top_tags = rows_to_dicts(cur)

                # Top 5 categories by product count
                cur.execute("""
                    SELECT c.CATEGORY_NAME, COUNT(p.PRODUCT_ID) AS cnt
                    FROM PRODUCTS p
                    JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                    GROUP BY c.CATEGORY_NAME
                    ORDER BY cnt DESC
                    FETCH FIRST 5 ROWS ONLY
                """)
                top_categories = rows_to_dicts(cur)

                # Top 5 brands by product count
                cur.execute("""
                    SELECT b.BRAND_NAME, COUNT(p.PRODUCT_ID) AS cnt
                    FROM PRODUCTS p
                    JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                    GROUP BY b.BRAND_NAME
                    ORDER BY cnt DESC
                    FETCH FIRST 5 ROWS ONLY
                """)
                top_brands = rows_to_dicts(cur)

                # Nutrition coverage (% products with each major nutrient)
                cur.execute("""
                    SELECT n.NUTRIENT_NAME,
                           COUNT(pn.PRODUCT_ID) AS recorded,
                           ROUND(COUNT(pn.PRODUCT_ID) * 100.0 / (SELECT COUNT(*) FROM PRODUCTS), 1) AS coverage_pct
                    FROM NUTRIENTS n
                    LEFT JOIN PRODUCT_NUTRITION pn ON n.NUTRIENT_ID = pn.NUTRIENT_ID
                    GROUP BY n.NUTRIENT_NAME, n.NUTRIENT_ID
                    ORDER BY n.NUTRIENT_ID
                """)
                nutrition_coverage = rows_to_dicts(cur)

                return {
                    "counts": {
                        "products": total_products,
                        "brands": total_brands,
                        "categories": total_categories,
                        "parent_categories": total_parent_categories,
                        "allergens": total_allergens,
                        "restrictions": total_restrictions,
                        "nutrition_records": total_nutrition_records,
                        "allergen_records": total_allergen_records,
                    },
                    "top_tags": top_tags,
                    "top_categories": top_categories,
                    "top_brands": top_brands,
                    "nutrition_coverage": nutrition_coverage,
                }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch statistics: {str(e)}",
        )

