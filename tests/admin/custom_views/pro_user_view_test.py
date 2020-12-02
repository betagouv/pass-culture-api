from datetime import datetime

from sqlalchemy import and_
from wtforms.form import Form

from pcapi.admin.custom_views.pro_user_view import ProUserView
import pcapi.core.offers.factories as offers_factories
import pcapi.core.users.factories as users_factories
from pcapi.models import UserOfferer
from pcapi.models.offerer import Offerer
from pcapi.models.user_sql_entity import UserSQLEntity

from tests.conftest import TestClient
from tests.conftest import clean_database


class ProUserViewTest:
    @clean_database
    def test_pro_user_creation(self, app):
        # Given
        users_factories.UserFactory(email="user@example.com", isAdmin=True, isBeneficiary=False)
        offers_factories.VirtualVenueTypeFactory()

        data = dict(
            email="toto@testemail.fr",
            firstName="Juste",
            lastName="Leblanc",
            phoneNumber="0601020304",
            dateOfBirth="2020-12-09 09:45:00",
            departementCode="93",
            postalCode="93000",
            offererSiren="123654987",
            offererName="Les films du plat pays",
            offererPostalCode="93000",
            offererCity="Nantes",
        )

        # When
        client = TestClient(app.test_client()).with_auth("user@example.com")

        # Then
        response = client.post("/pc/back-office/pro_users/new", form=data)

        assert response.status_code == 302

        users_filtered = UserSQLEntity.query.filter_by(email="toto@testemail.fr").all()
        assert len(users_filtered) == 1
        user_created = users_filtered[0]
        assert user_created.firstName == "Juste"
        assert user_created.lastName == "Leblanc"
        assert user_created.publicName == "Juste Leblanc"
        assert user_created.dateOfBirth == datetime(2020, 12, 9, 9, 45)
        assert user_created.departementCode == "93"
        assert user_created.postalCode == "93000"
        assert user_created.isBeneficiary is False
        assert len(user_created.deposits) == 0

        offerers_filtered = Offerer.query.filter_by(siren="123654987").all()
        assert len(offerers_filtered) == 1
        offerer_created = offerers_filtered[0]
        assert offerer_created.name == "Les films du plat pays"
        assert offerer_created.postalCode == "93000"
        assert offerer_created.city == "Nantes"

        user_offerers_filtered = UserOfferer.query.filter(
            and_(UserOfferer.userId == user_created.id, UserOfferer.offererId == offerer_created.id)
        ).all()
        assert len(user_offerers_filtered) == 1

    def test_it_gives_a_random_password_to_user(self, app, db_session):
        # Given
        offers_factories.VirtualVenueTypeFactory()
        pro_user_view = ProUserView(UserSQLEntity, db_session)
        pro_user_view_create_form = pro_user_view.get_create_form()
        data = dict(
            firstName="Juste",
            lastName="Leblanc",
            offererSiren="123654987",
            offererName="Les films du plat pays",
            offererPostalCode="93000",
            offererCity="Nantes",
        )
        form = pro_user_view_create_form(data=data)
        user = UserSQLEntity()

        # When
        pro_user_view.on_model_change(form, user, True)
        first_password = user.password

        pro_user_view.on_model_change(form, user, True)

        # Then
        assert user.password != first_password

    def test_should_create_the_public_name(self, app, db_session):
        # Given
        user = UserSQLEntity()
        user.firstName = "Ken"
        user.lastName = "Thompson"
        user.publicName = None
        view = ProUserView(model=UserSQLEntity, session=db_session)

        # When
        view.on_model_change(Form(), model=user, is_created=False)

        # Then
        assert user.publicName == "Ken Thompson"