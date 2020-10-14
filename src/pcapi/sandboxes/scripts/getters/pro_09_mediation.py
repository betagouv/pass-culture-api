from pcapi.models.mediation_sql_entity import MediationSQLEntity
from pcapi.models.offer_sql_entity import OfferSQLEntity
from pcapi.models.user_sql_entity import UserSQLEntity
from pcapi.models import VenueSQLEntity
from pcapi.repository.user_queries import filter_users_with_at_least_one_validated_offerer_validated_user_offerer
from pcapi.sandboxes.scripts.utils.helpers import get_offer_helper, get_pro_helper

def get_existing_pro_validated_user_with_at_least_one_visible_offer_with_no_mediation():
    query = UserSQLEntity.query.filter(UserSQLEntity.validationToken == None)
    query = filter_users_with_at_least_one_validated_offerer_validated_user_offerer(query)
    query = query.join(VenueSQLEntity) \
                 .join(OfferSQLEntity) \
                 .join(MediationSQLEntity)
    user = query.first()

    for uo in user.UserOfferers:
        if uo.offerer.validationToken == None and uo.validationToken == None:
            for venue in uo.offerer.managedVenues:
                for offer in venue.offers:
                    if len(offer.mediations) == 0:
                        return {
                            "offer": get_offer_helper(offer),
                            "user": get_pro_helper(user)
                        }