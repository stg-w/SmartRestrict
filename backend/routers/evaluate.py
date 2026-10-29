from fastapi import APIRouter, HTTPException, status
from backend.models import EvaluateRequest, ProductEvaluationResult
from backend.services.product_service import product_service
from backend.services.rule_engine import rule_engine

router = APIRouter(prefix="/api/evaluate", tags=["Evaluation"])

@router.post("", response_model=list[ProductEvaluationResult], summary="Evaluate product suitability against restrictions and allergens")
def evaluate_products(req: EvaluateRequest):
    target_ids = []
    if req.product_id:
        target_ids.append(req.product_id)
    if req.product_ids:
        target_ids.extend([pid for pid in req.product_ids if pid not in target_ids])

    if not target_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide either 'product_id' or a non-empty list of 'product_ids' to evaluate."
        )

    results = []
    try:
        for pid in target_ids[:50]:  # limit batch evaluation to 50
            detail = product_service.get_product_detail(pid)
            if not detail:
                continue

            nutrition_dict_list = [
                {"nutrient_id": nf.nutrient_id, "amount": nf.amount}
                for nf in detail.nutrition_facts
            ]
            allergen_dict_list = [
                {"allergen_id": a.allergen_id, "allergen_name": a.allergen_name}
                for a in detail.allergens_list
            ]
            tag_dict_list = [
                {"tag_id": t.tag_id, "tag_name": t.tag_name, "tag_type": t.tag_type}
                for t in detail.tags_list
            ]
            ingredient_dict_list = [
                {"ingredient_id": i.ingredient_id, "ingredient_name": i.ingredient_name}
                for i in detail.ingredients_list
            ]

            eval_res = rule_engine.evaluate_product_suitability(
                product={
                    "product_id": detail.product_id,
                    "item_name": detail.item_name,
                    "brand_name": detail.brand_name,
                    "ingredients_text": detail.ingredients_text
                },
                nutrition_list=nutrition_dict_list,
                product_allergens=allergen_dict_list,
                product_tags=tag_dict_list,
                product_ingredients=ingredient_dict_list,
                user_restriction_ids=req.restriction_ids,
                user_allergen_ids=req.allergen_ids
            )
            results.append(eval_res)

        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Suitability evaluation failed: {str(e)}"
        )
