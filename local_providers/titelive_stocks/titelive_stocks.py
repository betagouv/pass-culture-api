from datetime import datetime
from typing import List, Union

from sqlalchemy import Sequence

from infrastructure.container import api_titelive_stocks
from local_providers.local_provider import LocalProvider
from local_providers.providable_info import ProvidableInfo
from models import OfferSQLEntity, VenueProvider
from models.db import db
from models.stock_sql_entity import StockSQLEntity
from repository import product_queries
from repository.booking_queries import count_not_cancelled_bookings_quantity_by_stock_id

PRICE_DIVIDER_TO_EURO = 100


class TiteLiveStocks(LocalProvider):
    name = "TiteLive Stocks (Epagine / Place des libraires.com)"
    can_create = True

    def __init__(self, venue_provider: VenueProvider, **options):
        super().__init__(venue_provider, **options)
        self.venue = self.venue_provider.venue

        self.last_seen_isbn = ''
        self.data = iter([])
        self.last_sync_date = venue_provider.lastSyncDate
        self.product = None
        self.offer_id = None

    def __next__(self) -> List[ProvidableInfo]:
        try:
            self.titelive_stock = next(self.data)
        except StopIteration:
            self.data = api_titelive_stocks.stocks_information(self.venue_provider.venueIdAtOfferProvider,
                                                               self.last_seen_isbn,
                                                               self.last_sync_date)
            self.titelive_stock = next(self.data)

        self.last_seen_isbn = str(self.titelive_stock['ref'])
        self.product = product_queries.find_active_book_product_by_isbn(self.titelive_stock['ref'])

        if not self.product:
            return []

        providable_info_stock = self.create_providable_info(StockSQLEntity, f"{self.titelive_stock['ref']}@{self.venue.siret}",
                                                            datetime.utcnow())
        providable_info_offer = self.create_providable_info(OfferSQLEntity, f"{self.titelive_stock['ref']}@{self.venue.siret}",
                                                            datetime.utcnow())
        return [providable_info_offer, providable_info_stock]

    def fill_object_attributes(self, stock_or_offer: Union[StockSQLEntity, OfferSQLEntity]) -> None:
        if isinstance(stock_or_offer, StockSQLEntity):
            self.fill_stock_attributes(stock_or_offer, self.titelive_stock)
        elif isinstance(stock_or_offer, OfferSQLEntity):
            self.fill_offer_attributes(stock_or_offer)

    def fill_stock_attributes(self, stock: StockSQLEntity, stock_information: dict) -> None:
        bookings_quantity = count_not_cancelled_bookings_quantity_by_stock_id(stock.id)
        stock.price = int(stock_information['price']) / PRICE_DIVIDER_TO_EURO
        stock.quantity = int(stock_information['available']) + bookings_quantity
        stock.bookingLimitDatetime = None
        stock.offerId = self.offer_id
        stock.dateModified = datetime.now()

    def fill_offer_attributes(self, offer: OfferSQLEntity) -> None:
        offer.name = self.product.name
        offer.description = self.product.description
        offer.type = self.product.type
        offer.extraData = self.product.extraData
        offer.bookingEmail = self.venue.bookingEmail
        offer.venueId = self.venue.id
        offer.productId = self.product.id

        is_new_offer_to_create = not offer.id
        if is_new_offer_to_create:
            next_id = self.get_next_offer_id_from_sequence()
            offer.id = next_id

        self.offer_id = offer.id

    def get_next_offer_id_from_sequence(self) -> int:
        sequence = Sequence('offer_id_seq')
        return db.session.execute(sequence)