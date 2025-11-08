from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from query import run_query

app = FastAPI(title="Persona Analysis API")
app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:5173", "http://localhost:5174"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
)

class ProductRequest(BaseModel):
    product_description: str

@app.post("/analyze_product")
async def analyze_product(request: ProductRequest):
    try:
        product_description = request.product_description
        if not product_description:
            raise HTTPException(status_code=400, detail="Missing 'product_description' in request body")
        result = run_query(product_description)
        return result
    except Exception as e:
        print(f"❌ Handler error: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/")
async def root():
    return {"status": "ok", "message": "Persona Analysis API is running"}
