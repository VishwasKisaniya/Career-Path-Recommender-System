# request/response data shapes

from pydantic import BaseModel, Field
from typing import List, Optional


# What the user sends to the API
class SkillInput(BaseModel):
    skills: List[str] = Field(..., max_length=10)
    user_id: Optional[str] = None   # UUID from browser localStorage


# One recommended skill returned to the user
class Recommendation(BaseModel):
    skill: str
    track: str
    reason: str
    difficulty: Optional[int] = None


# The full response grouped by track
class RecommendationResponse(BaseModel):
    recommendations: dict   # track name → list of Recommendation
