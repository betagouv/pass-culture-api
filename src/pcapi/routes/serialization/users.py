from typing import Optional
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from pcapi.serialization.utils import to_camel, humanize_field
from pcapi.utils.date import format_into_utc_date


class PatchUserBodyModel(BaseModel):  # pylint: disable=too-few-public-methods
    cultural_survey_id: Optional[str]
    cultural_survey_filled_date: Optional[str]
    department_code: Optional[str] = Field(None, alias="departementCode")
    email: Optional[EmailStr]
    needs_to_fill_cultural_survey: Optional[bool]
    phone_number: Optional[str]
    postal_code: Optional[str]
    public_name: Optional[str]
    has_seen_tutorials: Optional[bool]

    class Config:  # pylint: disable=too-few-public-methods
        alias_generator = to_camel
        extra = "forbid"


class PatchUserResponseModel(BaseModel):  # pylint: disable=too-few-public-methods
    id: str
    email: EmailStr
    publicName: str
    postalCode: str
    phoneNumber: Optional[str]
    departementCode: str
    activity: Optional[str]
    address: Optional[str]
    canBookFreeOffers: bool
    city: Optional[str]
    civility: Optional[str]
    dateCreated: datetime
    dateOfBirth: Optional[str]
    firstName: Optional[str]
    hasOffers: bool
    hasPhysicalVenues: bool
    isAdmin: bool
    lastConnectionDate: Optional[str]
    lastName: Optional[str]
    needsToFillCulturalSurvey: bool

    _normalize_id = humanize_field("id")

    class Config:  # pylint: disable=too-few-public-methods
        json_encoders = {datetime: format_into_utc_date}
        orm_mode = True
        alias_generator = to_camel
        allow_population_by_field_name = True
        arbitrary_types_allowed = True