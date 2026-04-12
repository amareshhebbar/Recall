import asyncio
import json
import hashlib
import logging
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class ExtractedEntity(BaseModel):
    unique_identifier: str = Field(description="A unique name, title, or ID for the product or repository.")
    description: str = Field(description="Detailed description of the entity.")
    relevance_score: int = Field(description="Score from 1-10 on how well this matches the user's criteria.")
    sentiment_analysis: str = Field(description="Summary of user reviews, specifically highlighting hatred, dislike, or health problem-solving capabilities as requested.")
    source_url: Optional[str] = Field(description="The exact URL where this data was found.")
    metrics: Dict[str, Any] = Field(description="Any numerical metrics like upvotes, stars, or review counts.")

class AgenticDirectives(BaseModel):
    next_urls_to_try: List[str] = Field(description="Highly relevant URLs found on this page that should be crawled next.")
    actionable_selector: Optional[str] = Field(description="The CSS selector for a button to click (e.g., 'Load More', 'Next Page', or expanding a review).")
    is_saturated: bool = Field(description="Set to true if the page contains no relevant information and the crawler should abort this specific path.")

class AgenticExtraction(BaseModel):
    page_status: str = Field(
        description="Classify the current page state. MUST be one of: 'SUCCESS' (normal page), 'BLOCKED_CLOUDFLARE' (Just a moment/Security check), 'CAPTCHA' (Requires human input), or 'NOT_FOUND'."
    )
    extracted_data: List[ExtractedEntity]
    directives: AgenticDirectives