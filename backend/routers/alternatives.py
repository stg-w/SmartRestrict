from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status
from backend.models import AlternativeItem
from backend.services.recommendation_service import recommendation_service

router = APIRouter(prefix="/api/products", tags=["Recommendations"])

@router.get("/{product_id}/alternatives", response_model=list[AlternativeItem], summary="Get explainable healthier alternatives for a product")
def get_product_alternatives(
    product_id: int,
    restriction_ids: Optional[str] = Query(None, description="Comma-separated restriction IDs (e.g. 1,2)"),
    allergen_ids: Optional[str] = Query(None, description="Comma-separated allergen IDs to avoid (e.g. 1,3)"),
    limit: int = Query(5, ge=1, le=20, description="Max number of alternatives to return")
):
    try:
        r_ids = []
        if restriction_ids:
            r_ids = [int(x.strip()) for x in restriction_ids.split(",") if x.strip().isdigit()]

        a_ids = []
        if allergen_ids:
            a_ids = [int(x.strip()) for x in allergen_ids.split(",") if x.strip().isdigit()]

        alternatives = recommendation_service.get_alternatives(
            product_id=product_id,
            user_restriction_ids=r_ids,
            user_allergen_ids=a_ids,
            limit=limit
        )
        return alternatives
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate alternatives: {str(e)}"
        )
