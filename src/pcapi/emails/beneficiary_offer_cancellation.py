from typing import Dict

from pcapi import settings
from pcapi.core.bookings.models import Booking
from pcapi.core.offers.models import Stock
from pcapi.repository.feature_queries import feature_send_mail_to_users_enabled
from pcapi.utils.mailing import build_pc_pro_offer_link
from pcapi.utils.mailing import extract_users_information_from_bookings
from pcapi.utils.mailing import format_booking_date_for_email
from pcapi.utils.mailing import format_booking_hours_for_email
from pcapi.utils.mailing import format_environment_for_email


def retrieve_offerer_booking_recap_email_data_after_user_cancellation(booking: Booking, recipients: str) -> Dict:
    user = booking.user
    stock = booking.stock
    bookings = list(filter(lambda ongoing_booking: not ongoing_booking.isCancelled, stock.bookings))
    offer = stock.offer
    venue = offer.venue
    departement_code = venue.departementCode or "numérique"
    price = str(stock.price) if stock.price > 0 else "Gratuit"
    offer_pc_pro_link = build_pc_pro_offer_link(offer)
    environment = format_environment_for_email()
    booked_date = format_booking_date_for_email(booking)
    booked_hour = format_booking_hours_for_email(booking)
    is_active = _is_offer_active_for_recap(stock)

    return {
        "FromEmail": settings.SUPPORT_EMAIL_ADDRESS,
        "MJ-TemplateID": 780015,
        "MJ-TemplateLanguage": True,
        "To": recipients if feature_send_mail_to_users_enabled() else settings.DEV_EMAIL_ADDRESS,
        "Vars": {
            "departement": departement_code,
            "nom_offre": offer.name,
            "lien_offre_pcpro": offer_pc_pro_link,
            "nom_lieu": venue.name,
            "prix": price,
            "is_event": int(offer.isEvent),
            "date": booked_date,
            "heure": booked_hour,
            "quantite": booking.quantity,
            "user_name": user.publicName,
            "user_email": user.email,
            "is_active": int(is_active),
            "nombre_resa": len(bookings),
            "env": environment,
            "users": extract_users_information_from_bookings(bookings),
        },
    }


def _is_offer_active_for_recap(stock: Stock) -> bool:
    return stock.isBookable and (stock.quantity is None or stock.remainingQuantity > 0)
