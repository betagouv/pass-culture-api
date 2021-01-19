from typing import Dict

from pcapi import settings
from pcapi.core.users.models import User
from pcapi.models.offerer import Offerer
from pcapi.repository.feature_queries import feature_send_mail_to_users_enabled


def retrieve_data_for_pro_user_waiting_offerer_validation_email(user: User, offerer: Offerer) -> Dict:
    return {
        "FromEmail": settings.SUPPORT_EMAIL_ADDRESS,
        "MJ-TemplateID": 778329,
        "MJ-TemplateLanguage": True,
        "To": user.email if feature_send_mail_to_users_enabled() else settings.DEV_EMAIL_ADDRESS,
        "Vars": {"nom_structure": offerer.name},
    }
