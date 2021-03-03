from datetime import datetime
from decimal import Decimal
from typing import List
from typing import Optional

from pydantic.class_validators import validator

from pcapi.models.offer_type import CategoryNameEnum
from pcapi.models.offer_type import CategoryType
from pcapi.routes.native.utils import convert_to_cent

from . import BaseModel


# TODO(xordoquy): move common models with offers API
class Coordinates(BaseModel):
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]


class FavoriteCategoryResponse(BaseModel):
    categoryType: CategoryType
    label: str
    name: Optional[CategoryNameEnum]


class FavoriteMediationResponse(BaseModel):
    credit: Optional[str]
    url: str

    class Config:
        orm_mode = True


class FavoriteOfferResponse(BaseModel):
    id: int
    name: str
    category: FavoriteCategoryResponse
    externalTicketOfficeUrl: Optional[str]
    image: Optional[FavoriteMediationResponse]
    coordinates: Coordinates
    price: Optional[int] = None
    startPrice: Optional[int] = None
    date: Optional[datetime] = None
    startDate: Optional[datetime] = None

    _convert_price = validator("price", pre=True, allow_reuse=True)(convert_to_cent)
    _convert_start_price = validator("startPrice", pre=True, allow_reuse=True)(convert_to_cent)

    class Config:
        orm_mode = True

    @classmethod
    def from_orm(cls, offer):  # type: ignore
        offer.category = {
            "name": offer.offer_category,
            "label": offer.offerType["appLabel"],
            "categoryType": offer.category_type,
        }
        offer.coordinates = {"latitude": offer.venue.latitude, "longitude": offer.venue.longitude}
        return super().from_orm(offer)


class FavoriteResponse(BaseModel):
    id: int
    offer: FavoriteOfferResponse

    class Config:
        orm_mode = True


class PaginatedFavoritesResponse(BaseModel):
    page: int
    nbFavorites: int
    favorites: List[FavoriteResponse]