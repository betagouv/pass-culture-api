from functools import wraps
import logging

from flask import _request_ctx_stack
from flask_jwt_extended.utils import get_jwt_identity
from flask_jwt_extended.view_decorators import jwt_required

from pcapi.models.api_errors import ForbiddenError
from pcapi.repository.user_queries import find_user_by_email
from pcapi.routes.native.v1.blueprint import JWT_AUTH
from pcapi.serialization.spec_tree import add_security_scheme


logger = logging.getLogger(__name__)


def authenticated_user_required(route_function):  # type: ignore
    add_security_scheme(route_function, JWT_AUTH)

    @wraps(route_function)
    @jwt_required
    def retrieve_authenticated_user(*args, **kwargs):  # type: ignore
        email = get_jwt_identity()
        user = find_user_by_email(email)
        if user is None or not user.isActive:
            logger.error("Authenticated user with email %s not found or inactive", email)
            raise ForbiddenError({"email": ["Utilisateur introuvable"]})

        # push the user to the current context - similar to flask-login
        ctx = _request_ctx_stack.top
        ctx.user = user

        return route_function(user, *args, **kwargs)

    return retrieve_authenticated_user
