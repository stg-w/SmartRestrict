from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.models import PaginatedProductsResponse, ProductDetail
from backend.services.product_service import product_service
from backend.database import get_db_connection, rows_to_dicts

router = APIRouter(prefix="/api/products", tags=["Products"])


@router.get("/search", summary="Fast autocomplete search — returns id, name, brand (max 10 results)")
def search_products(
    q: str = Query(..., min_length=1, description="Search term"),
    limit: int = Query(10, ge=1, le=20, description="Maximum results to return")
):
    """Lightweight search endpoint for autocomplete dropdowns."""
    if not q.strip():
        return []
    try:
        clean_q = f"%{q.strip().lower()}%"
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT p.PRODUCT_ID, p.ITEM_NAME, b.BRAND_NAME, c.CATEGORY_NAME
                    FROM PRODUCTS p
                    JOIN BRANDS b ON p.BRAND_ID = b.BRAND_ID
                    JOIN CATEGORIES c ON p.CATEGORY_ID = c.CATEGORY_ID
                    WHERE LOWER(p.ITEM_NAME) LIKE :q OR LOWER(b.BRAND_NAME) LIKE :q
                    ORDER BY p.ITEM_NAME
                    FETCH FIRST :lim ROWS ONLY
                """, {"q": clean_q, "lim": limit})
                return rows_to_dicts(cur)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("", response_model=PaginatedProductsResponse, summary="Browse & search packaged food products")
def list_products(
    q: Optional[str] = Query(None, description="Search term for product name or brand"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    brand_id: Optional[int] = Query(None, description="Filter by brand ID"),
    dietary_type_id: Optional[int] = Query(None, description="Filter by dietary type (Vegetarian, Vegan, etc.)"),
    tag_id: Optional[int] = Query(None, description="Filter by tag ID (High Fibre, Low Sugar, etc.)"),
    sort_by: str = Query("name_asc", description="Sort option: name_asc, name_desc, price_asc, price_desc, calories_asc, sugar_asc, sodium_asc, protein_desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page")
):
    try:
        return product_service.get_products(
            q=q,
            category_id=category_id,
            brand_id=brand_id,
            dietary_type_id=dietary_type_id,
            tag_id=tag_id,
            sort_by=sort_by,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")


@router.get("/{product_id}", response_model=ProductDetail, summary="Get full product nutrition, ingredients, and tags")
def get_product(product_id: int):
    try:
        detail = product_service.get_product_detail(product_id)
        if not detail:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Product with ID {product_id} not found")
        return detail
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error: {str(e)}")
