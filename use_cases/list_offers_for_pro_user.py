from typing import Optional

from domain.pro_offers.paginated_offers import PaginatedOffers
from domain.pro_offers.paginated_offers_repository import PaginatedOffersRepository


class OffersRequestParameters(object):
    def __init__(self,
                 user_id: int,
                 user_is_admin: bool,
                 offerer_id: Optional[int],
                 venue_id: Optional[int],
                 pagination_limit: str = '10',
                 keywords: Optional[str] = None,
                 page: str = '0'):
        self.user_id = user_id
        self.user_is_admin = user_is_admin
        self.offerer_id = offerer_id
        self.venue_id = venue_id
        self.pagination_limit = int(pagination_limit)
        self.keywords = keywords
        self.page = int(page)


class ListOffersForProUser:
    def __init__(self, paginated_offer_repository: PaginatedOffersRepository):
        self.paginated_offer_repository = paginated_offer_repository

    def execute(self, offers_request_parameters: OffersRequestParameters) -> PaginatedOffers:
        return self.paginated_offer_repository.get_paginated_offers_for_offerer_venue_and_keywords(
            user_id=offers_request_parameters.user_id,
            user_is_admin=offers_request_parameters.user_is_admin,
            offerer_id=offers_request_parameters.offerer_id,
            pagination_limit=offers_request_parameters.pagination_limit,
            venue_id=offers_request_parameters.venue_id,
            keywords=offers_request_parameters.keywords,
            page=offers_request_parameters.page,
        )