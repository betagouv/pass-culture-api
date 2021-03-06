import logging
import re
import time
import typing

from flask import Blueprint
from flask import Flask
from flask import g
from flask import request
from flask.logging import default_handler
import flask.wrappers
from flask_admin import Admin
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_login import LoginManager
from flask_login import current_user
import redis
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.rq import RqIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from spectree import SpecTree
from sqlalchemy import orm
from werkzeug.middleware.profiler import ProfilerMiddleware

from pcapi import settings
from pcapi.core.logging import get_or_set_correlation_id
from pcapi.core.logging import install_logging
from pcapi.models.db import db
from pcapi.serialization.utils import before_handler
from pcapi.utils.health_checker import read_version_from_file
from pcapi.utils.json_encoder import EnumJSONEncoder
from pcapi.utils.rate_limiting import rate_limiter


logger = logging.getLogger(__name__)

install_logging()

if settings.IS_DEV is False:
    # pylint: disable=abstract-class-instantiated
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[FlaskIntegration(), RedisIntegration(), RqIntegration(), SqlalchemyIntegration()],
        release=read_version_from_file(),
        environment=settings.ENV,
        traces_sample_rate=settings.SENTRY_SAMPLE_RATE,
    )

app = Flask(__name__, static_url_path="/static")

if not settings.IS_DEV or settings.IS_RUNNING_TESTS:
    # Remove default logger/handler, since we use our own (see pcapi.core.logging)
    app.logger.removeHandler(default_handler)

api = SpecTree("flask", MODE="strict", before=before_handler)
api.register(app)

login_manager = LoginManager()
admin = Admin(name="Back Office du Pass Culture", url="/pc/back-office/", template_mode="bootstrap3")

if settings.PROFILE_REQUESTS:
    profiling_restrictions = [settings.PROFILE_REQUESTS_LINES_LIMIT]
    app.config["PROFILE"] = True
    app.wsgi_app = ProfilerMiddleware(  # type: ignore
        app.wsgi_app,
        restrictions=profiling_restrictions,
    )

if not settings.JWT_SECRET_KEY:
    raise Exception("JWT_SECRET_KEY not found in env")

app.secret_key = settings.FLASK_SECRET
app.json_encoder = EnumJSONEncoder
app.config["SQLALCHEMY_DATABASE_URI"] = settings.DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SECURE"] = not settings.IS_DEV
app.config["SESSION_COOKIE_SAMESITE"] = "Strict"
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = not settings.IS_DEV
app.config["REMEMBER_COOKIE_DURATION"] = 90 * 24 * 3600
app.config["PERMANENT_SESSION_LIFETIME"] = 90 * 24 * 3600
app.config["FLASK_ADMIN_SWATCH"] = "flatly"
app.config["FLASK_ADMIN_FLUID_LAYOUT"] = True
app.config["JWT_SECRET_KEY"] = settings.JWT_SECRET_KEY
app.config["RATELIMIT_STORAGE_URL"] = settings.REDIS_URL

jwt = JWTManager(app)

rate_limiter.init_app(app)


@app.before_request
def before_request() -> None:
    if current_user and current_user.is_authenticated:
        sentry_sdk.set_user(
            {
                "id": current_user.id,
            }
        )
    sentry_sdk.set_tag("correlation-id", get_or_set_correlation_id())
    g.request_start = time.perf_counter()


@app.after_request
def log_request_details(response: flask.wrappers.Response) -> flask.wrappers.Response:
    duration = round((time.perf_counter() - g.request_start) * 1000)  # milliseconds
    extra = {
        "statusCode": response.status_code,
        "method": request.method,
        "route": str(request.url_rule),  # e.g "/offers/<offer_id>"
        "path": request.path,
        "queryParams": request.query_string.decode("UTF-8"),
        "duration": duration,
        "size": response.headers.get("Content-Length", type=int),
    }

    logger.info("HTTP request at %s", request.path, extra=extra)

    return response


@app.after_request
def add_security_headers(response: flask.wrappers.Response) -> flask.wrappers.Response:
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

    return response


@app.teardown_request
def remove_db_session(
    exc: typing.Optional[Exception] = None,  # pylint: disable=unused-argument
) -> None:
    try:
        db.session.remove()
    except AttributeError:
        pass


admin.init_app(app)
db.init_app(app)
orm.configure_mappers()
login_manager.init_app(app)

public_api = Blueprint("Public API", __name__)
CORS(public_api, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

private_api = Blueprint("Private API", __name__)
CORS(
    private_api,
    resources={r"/*": {"origins": re.compile(settings.CORS_ALLOWED_ORIGIN)}},
    supports_credentials=True,
)

app.url_map.strict_slashes = False

with app.app_context():
    app.redis_client = redis.from_url(url=settings.REDIS_URL, decode_responses=True)
