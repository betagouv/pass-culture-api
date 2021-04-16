from flask_login import current_user

from pcapi.core.users import api as users_api
from pcapi.core.users.models import User
from pcapi.core.users.models import UserRole
from pcapi.flask_app import private_api
from pcapi.models import ApiErrors
from pcapi.routes.serialization.users import PatchProUserBodyModel
from pcapi.routes.serialization.users import PatchProUserResponseModel
from pcapi.serialization.decorator import spectree_serialize
from pcapi.utils.human_ids import dehumanize
from pcapi.utils.rest import authenticated_user
from pcapi.utils.rest import load_or_404
from pcapi.utils.rest import login_or_api_key_required


@private_api.route("/users/<user_id>/tuto-seen", methods=["PATCH"])
@login_or_api_key_required
@spectree_serialize(response_model=None, on_success_status=204)
def patch_user_tuto_seen(user_id: str) -> None:
    user = load_or_404(User, user_id)
    _ensure_current_user_has_rights(user_id)
    users_api.set_pro_tuto_as_seen(user)


@private_api.route("/users/current", methods=["PATCH"])
@authenticated_user(roles_whitelist=[UserRole.PRO, UserRole.ADMIN])
@spectree_serialize(response_model=PatchProUserResponseModel)  # type: ignore
def patch_profile(user, body: PatchProUserBodyModel) -> PatchProUserResponseModel:
    attributes = body.dict()
    # FIXME (dbaty, 2021-04-07): remove this hack once when we remove
    # PRO_HOMEPAGE (since the new profile update form does not allow
    # to update the public name). The new profile update form does
    # not send the publicName. pydantic hence stores a `None` value,
    # which is rejected by `validate_generic()` because the database
    # column is not nullable.
    if attributes["public_name"] is None:
        attributes["public_name"] = user.publicName
    users_api.update_user_info(user, **attributes)
    return PatchProUserResponseModel.from_orm(user)


def _ensure_current_user_has_rights(user_id):
    if current_user.id != dehumanize(user_id):
        errors = ApiErrors()
        errors.add_error("global", "Vous n'avez pas les droits d'accès suffisant pour effectuer cette modificaiton.")
        errors.status_code = 403
        raise errors
