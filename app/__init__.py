from flask import Flask, request, session, url_for
from flask_babel import gettext as _
from flask_login import current_user

from config import Config
from app.extensions import babel, csrf, db, login_manager


def create_app(config_object=Config):
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(config_object)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    def select_locale():
        lang = request.args.get("lang")
        if lang in {"en", "fr"}:
            session["lang"] = lang
            return lang
        if current_user.is_authenticated and current_user.language_preference in {"en", "fr"}:
            return current_user.language_preference
        if session.get("lang") in {"en", "fr"}:
            return session["lang"]
        return request.accept_languages.best_match(["en", "fr"]) or "en"

    babel.init_app(app, locale_selector=select_locale)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = "web.login"
    login_manager.login_message = _("Please log in to continue.")

    from app.api.routes import api_bp
    from app.web import web_bp

    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    csrf.exempt(api_bp)

    @app.context_processor
    def inject_helpers():
        def lang_url(lang):
            args = request.args.to_dict(flat=True)
            args["lang"] = lang
            return url_for(request.endpoint or "web.home", **(request.view_args or {}), **args)

        return {"lang_url": lang_url}

    from app.services.seed import seed_command

    app.cli.add_command(seed_command)

    with app.app_context():
        db.create_all()

    return app
