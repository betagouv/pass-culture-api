from flask.helpers import flash
from flask_login import current_user
from sqlalchemy.orm import query
from sqlalchemy.sql.functions import func
from wtforms import Form
from wtforms import validators

from pcapi import settings
from pcapi.admin.base_configuration import BaseAdminView
from pcapi.domain.user_emails import send_activation_email
from pcapi.models import UserOfferer
from pcapi.models.user_sql_entity import UserSQLEntity
from pcapi.utils.mailing import parse_email_addresses
from pcapi.utils.mailing import send_raw_email


class BeneficiaryUserView(BaseAdminView):
    can_edit = True

    @property
    def can_create(self) -> bool:
        if settings.IS_PROD:
            return current_user.email in parse_email_addresses(settings.SUPER_ADMIN_EMAIL_ADDRESSES)

        return True

    column_list = [
        "id",
        "isBeneficiary",
        "email",
        "firstName",
        "lastName",
        "publicName",
        "dateOfBirth",
        "departementCode",
        "phoneNumber",
        "postalCode",
        "resetPasswordToken",
        "validationToken",
    ]
    column_labels = dict(
        email="Email",
        isBeneficiary="Est bénéficiaire",
        firstName="Prénom",
        lastName="Nom",
        publicName="Nom d'utilisateur",
        dateOfBirth="Date de naissance",
        departementCode="Département",
        phoneNumber="Numéro de téléphone",
        postalCode="Code postal",
        resetPasswordToken="Jeton d'activation et réinitialisation de mot de passe",
        validationToken="Jeton de validation d'adresse email",
    )
    column_searchable_list = ["id", "publicName", "email", "firstName", "lastName"]
    column_filters = ["postalCode", "isBeneficiary"]
    form_columns = [
        "email",
        "firstName",
        "lastName",
        "publicName",
        "dateOfBirth",
        "departementCode",
        "postalCode",
        "isBeneficiary",
    ]

    def on_model_change(self, form: Form, model: UserSQLEntity, is_created: bool) -> None:
        # If a user is an admin, he shouldn't be able to be beneficiary
        if form.isBeneficiary.data and model.isAdmin:
            raise validators.ValidationError("Un admin ne peut pas être bénéficiaire")

        if is_created:
            # This is to prevent a circulary import dependency
            from pcapi.core.users.api import fulfill_user_data

            fulfill_user_data(model, "pass-culture-admin")

        super().on_model_change(form, model, is_created)

    def after_model_change(self, form: Form, model: UserSQLEntity, is_created: bool) -> None:
        if not send_activation_email(model, send_raw_email):
            flash("L'envoi d'email a échoué", "error")
        super().after_model_change(form, model, is_created)

    def get_query(self) -> query:
        return UserSQLEntity.query.outerjoin(UserOfferer).filter(UserOfferer.userId.is_(None))

    def get_count_query(self) -> query:
        return (
            self.session.query(func.count("*"))
            .select_from(self.model)
            .outerjoin(UserOfferer)
            .filter(UserOfferer.userId.is_(None))
        )