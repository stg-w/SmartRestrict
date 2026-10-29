import pytest
from backend.models import AlternativeItem

def test_alternative_item_model():
    alt = AlternativeItem(
        product_id=10,
        item_name="Whole Wheat Digestive Biscuit",
        brand_name="Britannia",
        category_name="BISCUIT",
        price_inr=30.0,
        serving_size_g=100.0,
        suitability_status="SUITABLE",
        alternative_score=85.5,
        comparison_points=[
            "45% less sugar (12.7g vs 32.5g per 100g)",
            "Higher dietary fibre (6.7g vs 0.0g)"
        ],
        trade_offs=[
            "Higher sodium (+248mg)"
        ],
        nutrition_comparison={"sugar": 12.7, "dietary_fibre": 6.7},
        tags=["High Fibre", "Low Sugar"]
    )

    assert alt.product_id == 10
    assert alt.alternative_score == 85.5
    assert len(alt.comparison_points) == 2
    assert len(alt.trade_offs) == 1
    assert "High Fibre" in alt.tags

