"""Pydantic models for vendor profiles and config."""

from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class VendorProfile(BaseModel):
    """A vendor profile defining how to connect to an API provider."""

    base_url: str | None = Field(default=None, description="Base URL for the provider")
    auth_env: Literal["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"] = Field(
        default="ANTHROPIC_API_KEY",
        description="Environment variable name for the API key",
    )
    model: str = Field(description="Model name to use with this vendor")
    official: bool = Field(default=False, description="Whether this is the official Anthropic API")
    extra_env: dict[str, str] = Field(
        default_factory=dict,
        description="Extra environment variables to set",
    )

    @model_validator(mode="after")
    def validate_base_url(self) -> Self:
        if not self.official and not self.base_url:
            raise ValueError("Non-official vendors must have a base_url")
        return self


class Config(BaseModel):
    """Top-level configuration for claudeapikey."""

    active_vendor: str | None = Field(
        default=None,
        description="Currently active vendor name",
    )
    vendors: dict[str, VendorProfile] = Field(
        default_factory=dict,
        description="Map of vendor name to profile",
    )
