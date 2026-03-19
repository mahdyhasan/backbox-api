from fastapi import APIRouter
from typing import List
from datetime import datetime, timedelta

router = APIRouter()


@router.get("/usage")
async def get_usage(app_id: str = None, days: int = 30):
    # Demo data
    return {
        "total_queries": 125430,
        "total_tokens": 45000000,
        "total_cost_usd": 2847.50,
        "period_days": days,
        "by_day": [
            {
                "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
                "queries": 4000 + i * 100,
                "cost": 200 + i * 5
            }
            for i in range(min(days, 10))
        ]
    }