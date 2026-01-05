from pydantic import BaseModel, Field
from typing import Optional

class InputPayload(BaseModel):
    """Schema for incoming customer support request."""
    customer_name: str
    email: str
    query: str
    priority: Optional[str] = Field(default="Normal")
    ticket_id: Optional[str] = None
