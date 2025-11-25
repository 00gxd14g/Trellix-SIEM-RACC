from datetime import datetime, timezone
from .customer import db


def _utcnow():
    return datetime.now(timezone.utc)


class SystemSetting(db.Model):
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(64), unique=True, nullable=False)
    data = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'category': self.category,
            'data': self.data,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class CustomerSetting(db.Model):
    __tablename__ = 'customer_settings'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, unique=True)
    data = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)

    customer = db.relationship('Customer', backref=db.backref('settings', uselist=False, lazy=True, cascade='all, delete-orphan'))

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'data': self.data,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }
