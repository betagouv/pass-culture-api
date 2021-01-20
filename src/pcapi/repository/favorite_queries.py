from typing import List

from sqlalchemy.orm.query import Query

from pcapi.models.favorite_sql_entity import FavoriteSQLEntity


def find_favorite_for_offer_and_user(offer_id: int, user_id: int) -> Query:
    return FavoriteSQLEntity.query.filter(FavoriteSQLEntity.offerId == offer_id).filter(
        FavoriteSQLEntity.userId == user_id
    )


def get_favorites_for_offers(offer_ids: List[int]) -> List[FavoriteSQLEntity]:
    return FavoriteSQLEntity.query.filter(FavoriteSQLEntity.offerId.in_(offer_ids)).all()
