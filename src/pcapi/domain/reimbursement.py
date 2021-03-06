from abc import ABC
from abc import abstractmethod
import datetime
from decimal import Decimal
from enum import Enum

from pcapi.models import Booking
from pcapi.models import ThingType


MIN_DATETIME = datetime.datetime(datetime.MINYEAR, 1, 1)
MAX_DATETIME = datetime.datetime(datetime.MAXYEAR, 1, 1)


class ReimbursementRule(ABC):
    def is_active(self, booking: Booking) -> bool:
        valid_from = self.valid_from if self.valid_from else MIN_DATETIME
        valid_until = self.valid_until if self.valid_until else MAX_DATETIME
        return valid_from < booking.dateCreated < valid_until

    @abstractmethod
    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        pass

    @property
    @abstractmethod
    def rate(self) -> Decimal:
        pass

    @property
    @abstractmethod
    def valid_from(self) -> None:
        pass

    @property
    @abstractmethod
    def valid_until(self) -> None:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    def apply(self, booking: Booking) -> Decimal:
        return Decimal(booking.total_amount * self.rate)


class DigitalThingsReimbursement(ReimbursementRule):
    rate = Decimal(0)
    description = "Pas de remboursement pour les offres digitales"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        offer = booking.stock.offer
        book_offer = offer.type == str(ThingType.LIVRE_EDITION)
        cinema_card_offer = offer.type == str(ThingType.CINEMA_CARD)
        offer_is_an_exception = book_offer or cinema_card_offer
        return offer.isDigital and not offer_is_an_exception


class PhysicalOffersReimbursement(ReimbursementRule):
    rate = Decimal(1)
    description = "Remboursement total pour les offres physiques"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        offer = booking.stock.offer
        book_offer = offer.type == str(ThingType.LIVRE_EDITION)
        cinema_card_offer = offer.type == str(ThingType.CINEMA_CARD)
        offer_is_an_exception = book_offer or cinema_card_offer
        return offer_is_an_exception or not offer.isDigital


class MaxReimbursementByOfferer(ReimbursementRule):
    rate = Decimal(0)
    description = "Pas de remboursement au dessus du plafond de 20 000 € par acteur culturel"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        if booking.stock.offer.product.isDigital:
            return False
        return kwargs["cumulative_value"] > 20000


class ReimbursementRateByVenueBetween20000And40000(ReimbursementRule):
    rate = Decimal(0.95)
    description = "Remboursement à 95% entre 20 000 € et 40 000 € par lieu"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        if booking.stock.offer.product.isDigital:
            return False
        return 20000 < kwargs["cumulative_value"] <= 40000


class ReimbursementRateByVenueBetween40000And150000(ReimbursementRule):
    rate = Decimal(0.85)
    description = "Remboursement à 85% entre 40 000 € et 150 000 € par lieu"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        if booking.stock.offer.product.isDigital:
            return False
        return 40000 < kwargs["cumulative_value"] <= 150000


class ReimbursementRateByVenueAbove150000(ReimbursementRule):
    rate = Decimal(0.7)
    description = "Remboursement à 70% au dessus de 150 000 € par lieu"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        if booking.stock.offer.product.isDigital:
            return False
        return kwargs["cumulative_value"] > 150000


class ReimbursementRateForBookAbove20000(ReimbursementRule):
    rate = Decimal(0.95)
    description = "Remboursement à 95% au dessus de 20 000 € pour les livres"
    valid_from = None
    valid_until = None

    def is_relevant(self, booking: Booking, **kwargs: Decimal) -> bool:
        if not booking.stock.offer.type == str(ThingType.LIVRE_EDITION):
            return False
        return kwargs["cumulative_value"] > 20000


class ReimbursementRules(Enum):
    DIGITAL_THINGS = DigitalThingsReimbursement()
    PHYSICAL_OFFERS = PhysicalOffersReimbursement()
    BETWEEN_20000_AND_40000_EUROS = ReimbursementRateByVenueBetween20000And40000()
    BETWEEN_40000_AND_150000_EUROS = ReimbursementRateByVenueBetween40000And150000()
    ABOVE_150000_EUROS = ReimbursementRateByVenueAbove150000()
    BOOK_REIMBURSEMENT = ReimbursementRateForBookAbove20000()


RULES = [
    ReimbursementRules.DIGITAL_THINGS,
    ReimbursementRules.PHYSICAL_OFFERS,
    ReimbursementRules.BETWEEN_20000_AND_40000_EUROS,
    ReimbursementRules.BETWEEN_40000_AND_150000_EUROS,
    ReimbursementRules.ABOVE_150000_EUROS,
    ReimbursementRules.BOOK_REIMBURSEMENT,
]


class AppliedReimbursement:
    def __init__(self, reimbursement_rule: ReimbursementRules, reimbursed_amount: Decimal):
        self.rule = reimbursement_rule
        self.amount = reimbursed_amount


class BookingReimbursement:
    def __init__(self, booking: Booking, reimbursement: ReimbursementRules, reimbursed_amount: Decimal):
        self.booking = booking
        self.reimbursement = reimbursement
        self.reimbursed_amount = reimbursed_amount


def find_all_booking_reimbursements(
    bookings: list[Booking], active_rules: list[ReimbursementRules]
) -> list[BookingReimbursement]:
    reimbursements = []
    cumulative_bookings_value_by_year = {}

    for booking in bookings:
        booking_civil_year = booking.dateCreated.year
        if booking_civil_year not in cumulative_bookings_value_by_year:
            cumulative_bookings_value_by_year[booking_civil_year] = Decimal(0)

        if ReimbursementRules.PHYSICAL_OFFERS.value.is_relevant(booking):
            cumulative_bookings_value_by_year[booking_civil_year] = (
                cumulative_bookings_value_by_year[booking_civil_year] + booking.total_amount
            )

        potential_rules = _find_potential_rules(
            booking, active_rules, cumulative_bookings_value_by_year[booking_civil_year]
        )
        elected_rule = determine_elected_rule(booking, potential_rules)
        reimbursements.append(BookingReimbursement(booking, elected_rule.rule, elected_rule.amount))

    return reimbursements


def determine_elected_rule(booking: Booking, potential_rules: list[AppliedReimbursement]) -> AppliedReimbursement:
    if any(map(lambda r: r.rule == ReimbursementRules.BOOK_REIMBURSEMENT, potential_rules)):
        elected_rule = AppliedReimbursement(
            ReimbursementRules.BOOK_REIMBURSEMENT, ReimbursementRules.BOOK_REIMBURSEMENT.value.apply(booking)
        )
    else:
        elected_rule = min(potential_rules, key=lambda x: x.amount)
    return elected_rule


def _find_potential_rules(
    booking: Booking, rules: list[ReimbursementRules], cumulative_bookings_value: Decimal
) -> list:
    relevant_rules = []
    for rule in rules:
        if rule.value.is_active and rule.value.is_relevant(booking, cumulative_value=cumulative_bookings_value):
            reimbursed_amount = rule.value.apply(booking)
            relevant_rules.append(AppliedReimbursement(rule, reimbursed_amount))
    return relevant_rules
