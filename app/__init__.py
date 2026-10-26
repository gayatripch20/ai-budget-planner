import os
from flask import Flask
from config import config_by_name
from app.extensions import db, migrate, login_manager, csrf


def create_app(config_name: str | None = None) -> Flask:
    """
    Application Factory: Instantiates and configures the Flask application.
    Enables clean environment switching (development, testing, production).
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    config_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader callback for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id: str):
        return db.session.get(User, int(user_id))

    # Global template context processor: makes currency and helper variables available in all Jinja templates
    @app.context_processor
    def inject_global_template_context():
        from flask_login import current_user
        from datetime import datetime
        from app.models.notification import Notification

        user_currency = app.config.get("DEFAULT_CURRENCY", "₹")
        unread_notifs_count = 0
        if current_user.is_authenticated:
            if getattr(current_user, "currency", None):
                user_currency = current_user.currency
            unread_notifs_count = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

        return {
            "currency": user_currency,
            "unread_notifications_count": unread_notifs_count,
            "current_year": datetime.now().year,
            "app_name": "AI Budget Planner",
        }

    # Register Blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.dashboard import dashboard_bp
    from app.routes.transactions import transactions_bp
    from app.routes.budgets import budgets_bp
    from app.routes.goals import goals_bp
    from app.routes.analytics import analytics_bp
    from app.routes.predictions import predictions_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(budgets_bp)
    app.register_blueprint(goals_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(predictions_bp)

    # Register CLI seed command for database initial categories
    register_cli_commands(app)

    return app


def register_cli_commands(app: Flask) -> None:
    """Register custom Flask CLI commands."""
    import click

    @app.cli.command("seed-db")
    def seed_db():
        """Seed initial default income and expense categories."""
        from app.models.category import Category

        default_categories = [
            # Income Categories
            {"name": "Salary", "type": "income", "icon": "bi-cash-stack", "color": "#1cc88a", "is_default": True},
            {"name": "Freelance", "type": "income", "icon": "bi-laptop", "color": "#36b9cc", "is_default": True},
            {"name": "Investments", "type": "income", "icon": "bi-graph-up-arrow", "color": "#4e73df", "is_default": True},
            {"name": "Gifts & Grants", "type": "income", "icon": "bi-gift", "color": "#f6c23e", "is_default": True},
            {"name": "Other Income", "type": "income", "icon": "bi-wallet2", "color": "#858796", "is_default": True},
            # Expense Categories
            {"name": "Food & Dining", "type": "expense", "icon": "bi-cup-hot", "color": "#e74a3b", "is_default": True},
            {"name": "Rent & Housing", "type": "expense", "icon": "bi-house", "color": "#fd7e14", "is_default": True},
            {"name": "Groceries", "type": "expense", "icon": "bi-cart3", "color": "#20c997", "is_default": True},
            {"name": "Utilities & Bills", "type": "expense", "icon": "bi-lightning-charge", "color": "#6f42c1", "is_default": True},
            {"name": "Travel & Transport", "type": "expense", "icon": "bi-car-front", "color": "#0dcaf0", "is_default": True},
            {"name": "Education & Courses", "type": "expense", "icon": "bi-book", "color": "#0d6efd", "is_default": True},
            {"name": "Shopping & Gadgets", "type": "expense", "icon": "bi-bag", "color": "#d63384", "is_default": True},
            {"name": "Entertainment", "type": "expense", "icon": "bi-film", "color": "#ffc107", "is_default": True},
            {"name": "Healthcare & Medical", "type": "expense", "icon": "bi-heart-pulse", "color": "#dc3545", "is_default": True},
            {"name": "Miscellaneous", "type": "expense", "icon": "bi-three-dots", "color": "#6c757d", "is_default": True},
        ]

        seeded_count = 0
        for cat_data in default_categories:
            existing = Category.query.filter_by(name=cat_data["name"], type=cat_data["type"], user_id=None).first()
            if not existing:
                cat = Category(**cat_data)
                db.session.add(cat)
                seeded_count += 1

        db.session.commit()
        click.echo(f"Successfully seeded {seeded_count} default categories into MySQL database!")
