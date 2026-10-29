from typing import Optional, Any
from pydantic import BaseModel, EmailStr, Field

class BrandItem(BaseModel):
    brand_id: int
    brand_name: str

class CategoryItem(BaseModel):
    category_id: int
    category_name: str
    parent_category_id: Optional[int] = None
    parent_name: Optional[str] = None

class NutrientItem(BaseModel):
    nutrient_id: int
    nutrient_name: str
    unit: str

class ProductNutritionFact(BaseModel):
    nutrient_id: int
    nutrient_name: str
    unit: str
    amount: Optional[float] = None

class IngredientItem(BaseModel):
    ingredient_id: int
    ingredient_name: str

class AllergenItem(BaseModel):
    allergen_id: int
    allergen_name: str

class DietaryTypeItem(BaseModel):
    dietary_type_id: int
    type_name: str

class TagItem(BaseModel):
    tag_id: int
    tag_name: str
    tag_type: str
    generated_date: Optional[str] = None
    source: Optional[str] = None

class TagRuleItem(BaseModel):
    tag_rule_id: int
    tag_id: int
    tag_name: Optional[str] = None
    tag_type: Optional[str] = None
    nutrient_id: int
    nutrient_name: Optional[str] = None
    unit: Optional[str] = None
    operator: str
    threshold: float
    priority: int
    description: Optional[str] = None

class RestrictionItem(BaseModel):
    restriction_id: int
    restriction_name: str
    description: Optional[str] = None

class RestrictionRuleItem(BaseModel):
    restriction_rule_id: int
    restriction_id: int
    restriction_name: Optional[str] = None
    tag_id: int
    tag_name: Optional[str] = None
    impact: str

class ProductSummary(BaseModel):
    product_id: int
    item_name: str
    brand_id: Optional[int] = None
    brand_name: Optional[str] = None
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    serving_size_g: Optional[float] = None
    price_inr: Optional[float] = None
    calories: Optional[float] = None
    sugar: Optional[float] = None
    sodium: Optional[float] = None
    saturated_fat: Optional[float] = None
    protein: Optional[float] = None
    dietary_fibre: Optional[float] = None
    tags: list[str] = []
    dietary_types: list[str] = []
    allergens: list[str] = []

class ProductDetail(ProductSummary):
    ingredients_text: Optional[str] = None
    vitamin_info: Optional[str] = None
    source_of_data: Optional[str] = None
    collection_date: Optional[str] = None
    collected_by: Optional[str] = None
    remarks: Optional[str] = None
    nutrition_facts: list[ProductNutritionFact] = []
    ingredients_list: list[IngredientItem] = []
    allergens_list: list[AllergenItem] = []
    dietary_types_list: list[DietaryTypeItem] = []
    tags_list: list[TagItem] = []
    missing_nutrients: list[str] = []

class PaginatedProductsResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int
    items: list[ProductSummary]

class EvaluateRequest(BaseModel):
    product_id: Optional[int] = None
    product_ids: Optional[list[int]] = None
    restriction_ids: list[int] = []
    allergen_ids: list[int] = []

class ReasonPoint(BaseModel):
    title: str
    details: str
    severity: str  # 'danger', 'warning', 'success', 'info'

class ProductEvaluationResult(BaseModel):
    product_id: int
    item_name: str
    brand_name: Optional[str] = None
    status: str  # 'SUITABLE', 'CAUTION', 'AVOID'
    verdict: str
    allergen_warnings: list[ReasonPoint] = []
    restriction_flags: list[ReasonPoint] = []
    positive_matches: list[ReasonPoint] = []
    missing_data_warnings: list[str] = []
    safety_disclaimer: str = (
        "SmartRestrict analyzes packaged food label information based on database records. "
        "It does not constitute medical advice and cannot guarantee zero cross-contamination. "
        "Always inspect physical packaging before consumption if you have severe allergies."
    )

class AlternativeItem(BaseModel):
    product_id: int
    item_name: str
    brand_name: Optional[str] = None
    category_name: Optional[str] = None
    price_inr: Optional[float] = None
    serving_size_g: Optional[float] = None
    suitability_status: str
    alternative_score: float
    comparison_points: list[str] = []
    trade_offs: list[str] = []
    nutrition_comparison: dict[str, Any] = {}
    tags: list[str] = []

class UserProfileCreate(BaseModel):
    user_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    restriction_ids: list[int] = []

class UserProfileResponse(BaseModel):
    user_id: int
    user_name: str
    email: str
    created_on: Optional[str] = None
    restrictions: list[RestrictionItem] = []
