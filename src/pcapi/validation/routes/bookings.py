from datetime import datetime
from typing import Union

from pcapi.domain.bookings import BOOKING_CANCELLATION_DELAY
from pcapi.domain.user_activation import is_activation_booking
from pcapi.models import ApiErrors, BookingSQLEntity, RightsType
from pcapi.models.api_errors import ResourceGoneError, ForbiddenError
from pcapi.models.user_sql_entity import UserSQLEntity
from pcapi.repository import payment_queries, venue_queries
from pcapi.utils.rest import ensure_current_user_has_rights


def check_has_stock_id(stock_id: int) -> None:
    if stock_id is None:
        api_errors = ApiErrors()
        api_errors.add_error('stockId', "Vous devez préciser un identifiant d'offre")
        raise api_errors


def check_booking_token_is_usable(booking: BookingSQLEntity) -> None:
    resource_gone_error = ResourceGoneError()
    if booking.isUsed:
        resource_gone_error.add_error('booking', 'Cette réservation a déjà été validée')
        raise resource_gone_error
    if booking.isCancelled:
        resource_gone_error.add_error('booking', 'Cette réservation a été annulée')
        raise resource_gone_error
    event_starts_in_more_than_72_hours = booking.stock.beginningDatetime and (
            booking.stock.beginningDatetime > (datetime.utcnow() + BOOKING_CANCELLATION_DELAY))
    if event_starts_in_more_than_72_hours:
        errors = ForbiddenError()
        errors.add_error('beginningDatetime',
                         "Vous ne pouvez pas valider cette contremarque plus de 72h avant le début de l'évènement")
        raise errors


def check_booking_token_is_keepable(booking: BookingSQLEntity) -> None:
    resource_gone_error = ResourceGoneError()
    booking_payment = payment_queries.find_by_booking_id(booking.id)

    if booking_payment is not None:
        resource_gone_error.add_error('payment', "Le remboursement est en cours de traitement")
        raise resource_gone_error

    if not booking.isUsed:
        resource_gone_error.add_error('booking', "Cette réservation n'a pas encore été validée")
        raise resource_gone_error

    if booking.isCancelled:
        resource_gone_error.add_error('booking', 'Cette réservation a été annulée')
        raise resource_gone_error


def check_is_not_activation_booking(booking: BookingSQLEntity) -> None:
    if is_activation_booking(booking):
        error = ForbiddenError()
        error.add_error('booking', "Impossible d'annuler une offre d'activation")
        raise error


def check_email_and_offer_id_for_anonymous_user(email: str, offer_id: int) -> None:
    api_errors = ApiErrors()
    if not email:
        api_errors.add_error('email',
                             "L'adresse email qui a servie à la réservation est obligatoire dans l'URL [?email=<email>]")
    if not offer_id:
        api_errors.add_error('offer_id', "L'id de l'offre réservée est obligatoire dans l'URL [?offer_id=<id>]")
    if api_errors.errors:
        raise api_errors


def check_booking_is_not_already_cancelled(booking: BookingSQLEntity) -> None:
    if booking.isCancelled:
        api_errors = ResourceGoneError()
        api_errors.add_error(
            'global',
            "Cette contremarque a déjà été annulée"
        )
        raise api_errors


def check_booking_is_not_used(booking: BookingSQLEntity) -> None:
    if booking.isUsed:
        api_errors = ForbiddenError()
        api_errors.add_error(
            'global',
            "Impossible d'annuler une réservation consommée"
        )
        raise api_errors


def check_page_format_is_number(page: Union[int, str]):
    page_is_not_decimal = not isinstance(page, int) and not page.isdecimal()

    if page_is_not_decimal or int(page) < 1:
        api_errors = ApiErrors()
        api_errors.add_error(
            'global',
            f"L'argument 'page' {page} n'est pas valide"
        )
        raise api_errors