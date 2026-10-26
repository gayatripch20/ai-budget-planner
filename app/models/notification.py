from datetime import datetime, timezone
from app.extensions import db


class Notification(db.Model):
    """
    In-app alerts and notifications for budget warnings,
    savings recommendations, and goal achievements.
    """
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(20), default="info", nullable=False)  # info, warning, danger, success
    is_read = db.Column(db.Boolean, default=False, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def __repr__(self) -> str:
        return f"<Notification id={self.id} user={self.user_id} title='{self.title}'>"
