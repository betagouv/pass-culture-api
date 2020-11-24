import pytest

from pcapi.core.users.factories import UserFactory
from pcapi.routes.serialization.beneficiaries import BeneficiaryAccountResponse


@pytest.mark.usefixtures("db_session")
class BeneficiaryAccountResponseTest:
    def should_humanize_the_user_id(self, app):
        # Given
        beneficiary = UserFactory(id=1)

        # When
        response = BeneficiaryAccountResponse.from_orm(beneficiary)

        # Then
        assert response.pk == 1
        assert response.id == "AE"
