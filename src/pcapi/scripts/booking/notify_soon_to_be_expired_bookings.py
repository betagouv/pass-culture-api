import datetime
from itertools import groupby
import logging
from operator import attrgetter

from pcapi import settings
import pcapi.core.bookings.repository as bookings_repository
from pcapi.domain.user_emails import send_soon_to_be_expired_bookings_recap_email_to_beneficiary


logger = logging.getLogger(__name__)


def notify_soon_to_be_expired_bookings() -> None:
    logger.info("[notify_soon_to_be_expired_bookings] Start")
    if settings.IS_STAGING:
        logger.info("[handle_expired_bookings] ENV=STAGING: Skipping")
    else:
        notify_users_of_soon_to_be_expired_bookings()
    logger.info("[notify_soon_to_be_expired_bookings] End")


def notify_users_of_soon_to_be_expired_bookings(given_date: datetime.date = None) -> None:
    logger.info("[notify_users_of_soon_to_be_expired_bookings] Start")
    bookings_ordered_by_user = bookings_repository.find_soon_to_be_expiring_booking_ordered_by_user(given_date)

    expired_bookings_grouped_by_user = dict()
    for user, booking in groupby(bookings_ordered_by_user, attrgetter("user")):
        expired_bookings_grouped_by_user[user] = list(booking)

    notified_users = []

    for user, bookings in expired_bookings_grouped_by_user.items():
        send_soon_to_be_expired_bookings_recap_email_to_beneficiary(user, bookings)
        notified_users.append(user)

    logger.info(
        "[notify_users_of_soon_to_be_expired_bookings] %d Users have been notified: %s",
        len(notified_users),
        notified_users,
    )

    logger.info("[notify_users_of_soon_to_be_expired_bookings] End")
