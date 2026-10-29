from fastapi import APIRouter, HTTPException, Query, status
from backend.models import UserProfileCreate, UserProfileResponse
from backend.services.user_service import user_service

router = APIRouter(prefix="/api/users", tags=["User Profiles"])

@router.post("/profile", response_model=UserProfileResponse, summary="Create or update user profile and saved restrictions in Oracle")
def save_profile(req: UserProfileCreate):
    try:
        return user_service.save_profile_and_restrictions(
            user_name=req.user_name,
            email=req.email,
            restriction_ids=req.restriction_ids
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save user profile: {str(e)}"
        )

@router.get("/profile", response_model=UserProfileResponse, summary="Retrieve user profile and saved restrictions by email")
def get_profile(email: str = Query(..., description="User email address")):
    try:
        profile = user_service.get_profile_by_email(email)
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No profile found for email {email}"
            )
        return profile
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving user profile: {str(e)}"
        )
