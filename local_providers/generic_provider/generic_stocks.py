from datetime import datetime
from typing import List, Callable

from sqlalchemy import Sequence

from local_providers.local_provider import LocalProvider
from local_providers.providable_info import ProvidableInfo
from models import VenueProvider, OfferSQLEntity, StockSQLEntity
from models.db import Model, db
from repository import product_queries
from repository.booking_queries import count_not_cancelled_bookings_quantity_by_stock_id


class GenericStocks(LocalProvider):
    name = 'Generic Stock Provider Interface'
    can_create = True

    def __init__(self,
                 venue_provider: VenueProvider,
                 get_provider_stock_information: Callable,
                 read_last_sync_date: Callable,
                 **options):
        super().__init__(venue_provider, **options)
        self.get_provider_stock_information = get_provider_stock_information
        self.venue = venue_provider.venue
        self.siret = self.venue.siret
        self.last_processed_isbn = ''
        self.stock_data = iter([])
        self.modified_since = read_last_sync_date(venue_provider.lastSyncDate)
        self.product = None
        self.offer_id = None

    def __next__(self) -> List[ProvidableInfo]:
        try:
            self.provider_stocks = next(self.stock_data)
        except StopIteration:
            self.stock_data = self.get_provider_stock_information(self.siret,
                                                                  self.last_processed_isbn,
                                                                  self.modified_since)
            self.provider_stocks = next(self.stock_data)

        self.last_processed_isbn = str(self.provider_stocks['ref'])
        self.product = product_queries.find_active_book_product_by_isbn(self.provider_stocks['ref'])
        if not self.product:
            return []

        providable_info_offer = self.create_providable_info(OfferSQLEntity,
                                                            f"{self.provider_stocks['ref']}@{self.siret}",
                                                            datetime.utcnow())
        providable_info_stock = self.create_providable_info(StockSQLEntity,
                                                            f"{self.provider_stocks['ref']}@{self.siret}",
                                                            datetime.utcnow())

        return [providable_info_offer, providable_info_stock]

    def fill_object_attributes(self, pc_object: Model):
        if isinstance(pc_object, OfferSQLEntity):
            self.fill_offer_attributes(pc_object)
        if isinstance(pc_object, StockSQLEntity):
            self.fill_stock_attributes(pc_object)

    def fill_offer_attributes(self, offer: OfferSQLEntity):
        offer.bookingEmail = self.venue.bookingEmail
        offer.description = self.product.description
        offer.extraData = self.product.extraData
        offer.name = self.product.name
        offer.productId = self.product.id
        offer.venueId = self.venue.id
        offer.type = self.product.type

        is_new_offer_to_create = not offer.id
        if is_new_offer_to_create:
            next_id = self.get_next_offer_id_from_sequence()
            offer.id = next_id

        self.offer_id = offer.id

    def fill_stock_attributes(self, stock: StockSQLEntity):
        bookings_quantity = count_not_cancelled_bookings_quantity_by_stock_id(stock.id)
        stock.quantity = self.provider_stocks['available'] + bookings_quantity
        stock.bookingLimitDatetime = None
        stock.offerId = self.offer_id
        stock.price = self.provider_stocks['price']

    def get_next_offer_id_from_sequence(self):
        sequence = Sequence('offer_id_seq')
        return db.session.execute(sequence)