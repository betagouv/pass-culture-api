from pcapi.core.offers.models import Mediation
from pcapi.core.users.models import User
from pcapi.models import Offer
from pcapi.models import Product
from pcapi.models import Stock
from pcapi.repository.user_queries import keep_only_webapp_users
from pcapi.sandboxes.scripts.utils.bookings import find_offer_compatible_with_bookings
from pcapi.sandboxes.scripts.utils.bookings import get_cancellable_bookings_for_user
from pcapi.sandboxes.scripts.utils.helpers import get_beneficiary_helper
from pcapi.sandboxes.scripts.utils.helpers import get_mediation_helper
from pcapi.sandboxes.scripts.utils.helpers import get_offer_helper


def get_existing_webapp_hnmm_user(return_as_dict=False):
    query = keep_only_webapp_users(User.query)
    query = query.filter(User.email.contains("93.has-no-more-money"))
    user = query.first()
    if return_as_dict == False:
        return user
    return {"user": get_beneficiary_helper(user)}


def get_existing_webapp_hbs_user():
    query = keep_only_webapp_users(User.query)
    query = query.filter(User.email.contains("has-booked-some"))
    user = query.first()
    return {"user": get_beneficiary_helper(user)}


def get_existing_event_offer_with_active_mediation_already_booked_but_cancellable_and_user_hnmm_93():
    offer_with_stock_id_tuples = (
        Offer.query.filter(Offer.mediations.any(Mediation.isActive))
        .join(Stock)
        .filter(Stock.beginningDatetime != None)
        .add_columns(Stock.id)
        .all()
    )
    user = get_existing_webapp_hnmm_user()
    bookings = get_cancellable_bookings_for_user(user)
    offer = find_offer_compatible_with_bookings(offer_with_stock_id_tuples, bookings)

    for mediation in offer.mediations:
        if mediation.isActive:
            return {
                "mediation": get_mediation_helper(mediation),
                "offer": get_offer_helper(offer),
                "user": get_beneficiary_helper(user),
            }
    return None


def get_existing_digital_offer_with_active_mediation_already_booked_and_user_hnmm_93():
    offer_with_stock_id_tuples = (
        Offer.query.outerjoin(Product)
        .filter(Offer.mediations.any(Mediation.isActive))
        .filter(Product.url != None)
        .join(Stock, (Offer.id == Stock.offerId))
        .add_columns(Stock.id)
        .all()
    )
    user = get_existing_webapp_hnmm_user()
    bookings = get_cancellable_bookings_for_user(user)
    offer = find_offer_compatible_with_bookings(offer_with_stock_id_tuples, bookings)

    for mediation in offer.mediations:
        if mediation.isActive:
            return {
                "mediation": get_mediation_helper(mediation),
                "offer": get_offer_helper(offer),
                "user": get_beneficiary_helper(user),
            }
    return None
