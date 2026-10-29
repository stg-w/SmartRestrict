from fastapi import APIRouter, HTTPException, status
from backend.services.product_service import product_service

router = APIRouter(prefix="/api/metadata", tags=["Metadata"])

@router.get("", summary="Get all master data (Brands, Categories, Allergens, Tags, Restrictions, Nutrients)")
def get_metadata():
    try:
        return product_service.get_metadata()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch metadata from database: {str(e)}"
        )
