from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.models import PaginatedProductsResponse, ProductDetail
from backend.services.product_service import product_service

router = APIRouter(prefix="/api/products", tags=["Products"])

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
