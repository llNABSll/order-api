from pydantic import BaseModel, Field
from typing import List, Optional

class OrderCreate(BaseModel):
    name: str  
    quantity: int = Field(gt=0, description="quantity must be positive")

class OrderOut(BaseModel):    
    name: str  
    price: float = Field(gt=0, description="price product must be positive")
    description: Optional[str] = None 
    is_available: bool = True
    tags: List[str] = []