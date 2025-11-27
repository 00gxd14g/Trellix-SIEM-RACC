from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy
from utils.signature_mapping import (
    get_alarm_event_ids,
    get_event_details,
    get_rule_event_ids,
)

db = SQLAlchemy()


def _utcnow():
    return datetime.now(timezone.utc)

class Customer(db.Model):
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    contact_email = db.Column(db.String(255))
    contact_phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    files = db.relationship('CustomerFile', backref='customer', lazy=True, cascade='all, delete-orphan')
    rules = db.relationship('Rule', backref='customer', lazy=True, cascade='all, delete-orphan')
    alarms = db.relationship('Alarm', backref='customer', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Customer {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'contact_email': self.contact_email,
            'contact_phone': self.contact_phone,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'file_count': len(self.files),
            'rule_count': len(self.rules),
            'alarm_count': len(self.alarms)
        }

class CustomerFile(db.Model):
    __tablename__ = 'customer_files'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)  # 'rule' or 'alarm'
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer)
    upload_date = db.Column(db.DateTime, default=_utcnow)
    validation_status = db.Column(db.String(20), default='pending')  # 'valid', 'invalid', 'pending'
    validation_errors = db.Column(db.Text)
    
    def __repr__(self):
        return f'<CustomerFile {self.filename}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'file_type': self.file_type,
            'filename': self.filename,
            'file_size': self.file_size,
            'upload_date': self.upload_date.isoformat() if self.upload_date else None,
            'validation_status': self.validation_status,
            'validation_errors': self.validation_errors
        }

class Rule(db.Model):
    __tablename__ = 'rules'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    rule_id = db.Column(db.String(100), nullable=False)  # e.g., "47-6000114"
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(db.Integer, nullable=False)
    sig_id = db.Column(db.String(50), nullable=True)  # Some rules may not have SigID
    rule_type = db.Column(db.Integer)
    revision = db.Column(db.Integer)
    origin = db.Column(db.Integer)
    action = db.Column(db.Integer)
    
    # New fields from schema
    normid = db.Column(db.String(50))
    sid = db.Column(db.Integer)
    rule_class = db.Column(db.Integer)  # Maps to <class>
    action_initial = db.Column(db.Integer)
    action_disallowed = db.Column(db.Integer)
    other_bits_default = db.Column(db.Integer)
    other_bits_disallowed = db.Column(db.Integer)
    
    xml_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    
    # Relationships
    alarms = db.relationship('Alarm', secondary='rule_alarm_relationships', back_populates='rules')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'rule_id', name='uq_customer_rule_id'),
        db.Index('idx_rules_customer_id', 'customer_id'),
    )
    
    def __repr__(self):
        return f'<Rule {self.rule_id}>'
    
    def to_dict(self):
        windows_event_ids = get_rule_event_ids(self)

        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'rule_id': self.rule_id,
            'name': self.name,
            'description': self.description,
            'severity': self.severity,
            'sig_id': self.sig_id,
            'rule_type': self.rule_type,
            'revision': self.revision,
            'origin': self.origin,
            'action': self.action,
            'normid': self.normid,
            'sid': self.sid,
            'class': self.rule_class,
            'action_initial': self.action_initial,
            'action_disallowed': self.action_disallowed,
            'other_bits_default': self.other_bits_default,
            'other_bits_disallowed': self.other_bits_disallowed,
            'xml_content': self.xml_content,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'windows_event_ids': windows_event_ids,
            'windows_events': get_event_details(windows_event_ids),
            'alarm_count': len(self.alarms),
            'matched_alarms': [{'id': a.id, 'name': a.name, 'match_value': a.match_value} for a in self.alarms]
        }

class Alarm(db.Model):
    __tablename__ = 'alarms'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False, index=True)
    name = db.Column(db.String(255), nullable=False)
    min_version = db.Column(db.String(20))
    severity = db.Column(db.Integer, nullable=False)
    match_field = db.Column(db.String(50), default='DSIDSigID')
    match_value = db.Column(db.String(100), nullable=False)  # e.g., "47|6000114"
    condition_type = db.Column(db.Integer)
    assignee_id = db.Column(db.Integer)
    esc_assignee_id = db.Column(db.Integer)
    note = db.Column(db.Text)
    device_ids = db.Column(db.Text)  # JSON string of device IDs/scopes
    xml_content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=_utcnow)
    updated_at = db.Column(db.DateTime, default=_utcnow, onupdate=_utcnow)
    
    # Relationships
    rules = db.relationship('Rule', secondary='rule_alarm_relationships', back_populates='alarms')
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'match_value', name='uq_customer_match_value'),
        db.Index('idx_alarms_customer_id', 'customer_id'),
    )
    
    def __repr__(self):
        return f'<Alarm {self.name}>'
    
    def to_dict(self):
        include_related = bool(getattr(self, 'rules', []) or [])
        windows_event_ids = get_alarm_event_ids(self, include_related_rules=include_related)

        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'name': self.name,
            'min_version': self.min_version,
            'severity': self.severity,
            'match_field': self.match_field,
            'match_value': self.match_value,
            'condition_type': self.condition_type,
            'assignee_id': self.assignee_id,
            'esc_assignee_id': self.esc_assignee_id,
            'note': self.note,
            'device_ids': self.device_ids,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'windows_event_ids': windows_event_ids,
            'windows_events': get_event_details(windows_event_ids),
            'matched_rules': [{'id': r.id, 'name': r.name, 'rule_id': r.rule_id} for r in self.rules]
        }

class RuleAlarmRelationship(db.Model):
    __tablename__ = 'rule_alarm_relationships'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    rule_id = db.Column(db.Integer, db.ForeignKey('rules.id'), nullable=False)
    alarm_id = db.Column(db.Integer, db.ForeignKey('alarms.id'), nullable=False)
    sig_id = db.Column(db.String(50), nullable=False)
    match_value = db.Column(db.String(100), nullable=False)
    relationship_type = db.Column(db.String(20), default='auto')  # 'auto', 'manual'
    created_at = db.Column(db.DateTime, default=_utcnow)
    
    # Unique constraint
    __table_args__ = (db.UniqueConstraint('rule_id', 'alarm_id', name='unique_rule_alarm'),)
    
    def __repr__(self):
        return f'<RuleAlarmRelationship {self.rule_id}-{self.alarm_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'rule_id': self.rule_id,
            'alarm_id': self.alarm_id,
            'sig_id': self.sig_id,
            'match_value': self.match_value,
            'relationship_type': self.relationship_type,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class ValidationLog(db.Model):
    __tablename__ = 'validation_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    file_type = db.Column(db.String(20), nullable=False)
    validation_type = db.Column(db.String(50), nullable=False)  # 'xml_structure', 'schema', 'relationship'
    status = db.Column(db.String(20), nullable=False)  # 'success', 'warning', 'error'
    message = db.Column(db.Text)
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=_utcnow)
    
    def __repr__(self):
        return f'<ValidationLog {self.validation_type}-{self.status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'file_type': self.file_type,
            'validation_type': self.validation_type,
            'status': self.status,
            'message': self.message,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
