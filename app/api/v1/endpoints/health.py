from fastapi import APIRouter

# Reuse existing health router behavior
router = APIRouter(tags=["health"]) 

@router.get("/health")
async def health():
    return {"status": "up"}
