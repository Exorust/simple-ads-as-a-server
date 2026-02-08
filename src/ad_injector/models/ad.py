"""Ad schema models using Pydantic."""

from pydantic import BaseModel, Field


class AdTargeting(BaseModel):
    """Targeting configuration for an ad."""

    topics: list[str] = Field(default_factory=list, description="Topics to target")
    locale: list[str] = Field(default_factory=list, description="Locale codes to target (e.g., 'en-US')")
    verticals: list[str] = Field(default_factory=list, description="Industry verticals to target")
    blocked_keywords: list[str] = Field(default_factory=list, description="Keywords to exclude from targeting")


class AdPolicy(BaseModel):
    """Policy flags for an ad."""

    sensitive: bool = Field(default=False, description="Whether the ad contains sensitive content")
    age_restricted: bool = Field(default=False, description="Whether the ad is age-restricted")


class Ad(BaseModel):
    """Complete ad schema for Pinecone storage."""

    ad_id: str = Field(..., description="Unique identifier for the ad")
    advertiser_id: str = Field(..., description="Identifier for the advertiser")
    title: str = Field(..., description="Ad title/headline")
    body: str = Field(..., description="Ad body text")
    cta_text: str = Field(..., description="Call-to-action text")
    landing_url: str = Field(..., description="URL to redirect users to")
    targeting: AdTargeting = Field(default_factory=AdTargeting, description="Targeting configuration")
    policy: AdPolicy = Field(default_factory=AdPolicy, description="Policy flags")

    @property
    def embedding_text(self) -> str:
        """Generate the text to be embedded (title + body + topics)."""
        topics_text = " ".join(self.targeting.topics)
        return f"{self.title} {self.body} {topics_text}".strip()

    def to_pinecone_metadata(self) -> dict:
        """Convert ad to Pinecone metadata format."""
        return {
            "ad_id": self.ad_id,
            "advertiser_id": self.advertiser_id,
            "title": self.title,
            "body": self.body,
            "cta_text": self.cta_text,
            "landing_url": self.landing_url,
            "topics": self.targeting.topics,
            "locale": self.targeting.locale,
            "verticals": self.targeting.verticals,
            "blocked_keywords": self.targeting.blocked_keywords,
            "sensitive": self.policy.sensitive,
            "age_restricted": self.policy.age_restricted,
        }
