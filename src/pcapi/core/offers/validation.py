from typing import Optional

from pcapi.models import UserOfferer
from pcapi.models.api_errors import ApiErrors

# FIXME (cgaunet, 2020-11-02): I moved this function from validation/routes/offers.py. It
# should not raise HTTP-related exceptions. It should rather raise
# generic exceptions such as `UserHasNotSufficientRights` and the calling
# route should have an exception handler that turns it into the
# desired HTTP-related exception (such as ForbiddenError)
# See also functions below.
def check_user_has_rights_on_offerer(user_offerer: Optional[UserOfferer]) -> None:
    errors = ApiErrors()
    errors.add_error(
        "global",
        "Vous n'avez pas les droits d'accès suffisant pour accéder à cette information.",
    )
    errors.status_code = 403

    if user_offerer is None:
        raise errors

    if not user_offerer.isValidated:
        raise errors