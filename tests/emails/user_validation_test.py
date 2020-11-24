import pytest

from pcapi import settings
import pcapi.core.users.factories as users_factories
from pcapi.utils.mailing import make_admin_user_validation_email
from pcapi.utils.mailing import make_pro_user_validation_email


@pytest.mark.usefixtures("db_session")
class ProValidationEmailsTest:
    def test_make_pro_user_validation_email_includes_validation_url_with_token_and_user_email(self, app):
        # Given
        user = users_factories.UserFactory(email="test@example.com", validationToken="token123")

        # When
        email = make_pro_user_validation_email(user)
        expected = {
            "FromName": "pass Culture pro",
            "Subject": "[pass Culture pro] Validation de votre adresse email pour le pass Culture",
            "MJ-TemplateID": 1660341,
            "MJ-TemplateLanguage": True,
            "Vars": {
                "nom_structure": "Jeanne Doux",
                "lien_validation_mail": f"{settings.PRO_URL}/inscription/validation/token123",
            },
        }

        # Then
        assert email == expected


@pytest.mark.usefixtures("db_session")
class AdminValidationEmailsTest:
    def test_make_admin_user_validation_email_includes_validation_url_with_token_and_user_email(self, app):
        # Given
        user = users_factories.UserFactory(email="admin@example.com", isAdmin=True, resetPasswordToken="token123")

        # When
        email = make_admin_user_validation_email(user)
        expected = {
            "FromName": "pass Culture admin",
            "Subject": "[pass Culture admin] Validation de votre adresse email pour le pass Culture",
            "MJ-TemplateID": 1660341,
            "MJ-TemplateLanguage": True,
            "Vars": {
                "lien_validation_mail": f"{settings.PRO_URL}/creation-de-mot-de-passe/token123",
            },
        }

        # Then
        assert email == expected
