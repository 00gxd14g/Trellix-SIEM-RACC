from datetime import datetime, timezone

from .customer import db


def _utcnow():
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    """
    Immutable audit log entries for compliance and security monitoring.

    Each entry captures who did what, when, and from where.
    """

    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True, default=_utcnow)

    # Who performed the action
    user_id = db.Column(db.String(100), nullable=True, index=True)
    customer_id = db.Column(db.Integer, nullable=True, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)  # IPv4 or IPv6
    user_agent = db.Column(db.String(500), nullable=True)

    # What action was performed
    action = db.Column(db.String(100), nullable=False, index=True)
    resource_type = db.Column(db.String(100), nullable=False, index=True)
    resource_id = db.Column(db.String(100), nullable=True, index=True)
    endpoint = db.Column(db.String(200), nullable=True, index=True)
    method = db.Column(db.String(10), nullable=False)  # HTTP method

    # Result and details
    status = db.Column(db.String(20), nullable=False, index=True)  # success, failure, error
    status_code = db.Column(db.Integer, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    # Additional context
    changes = db.Column(db.JSON, nullable=True)  # Before/after values for modifications
    # Keep underlying DB column name "metadata" for backwards compatibility
    audit_metadata = db.Column("metadata", db.JSON, nullable=True)

    def to_dict(self):
        """Convert audit log entry to dictionary."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": self.user_id,
            "customer_id": self.customer_id,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "endpoint": self.endpoint,
            "method": self.method,
            "status": self.status,
            "status_code": self.status_code,
            "error_message": self.error_message,
            "changes": self.changes,
            # Expose as "metadata" in API payloads for continuity
            "metadata": self.audit_metadata,
        }

