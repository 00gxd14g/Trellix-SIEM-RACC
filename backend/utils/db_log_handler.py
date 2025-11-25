import logging
from flask import has_request_context
from utils.audit_logger import AuditLogger

class DBLogHandler(logging.Handler):
    """
    Custom logging handler that writes logs to the AuditLog database table.
    It filters out logs from the audit logger itself to prevent recursion.
    """
    def emit(self, record):
        # Avoid infinite recursion if AuditLogger logs something
        # Also skip sqlalchemy logs to avoid noise and recursion during DB ops
        if (record.name.startswith('utils.audit_logger') or 
            record.name.startswith('sqlalchemy') or 
            record.name.startswith('werkzeug')):
            return

        try:
            # We need to be inside an app context to use the DB session
            if not has_request_context():
                return

            msg = self.format(record)
            
            # Determine status based on log level
            status = 'failure' if record.levelno >= logging.ERROR else 'success'
            
            # Use a specific action for backend logs
            action = 'BACKEND_LOG'
            
            # Prepare metadata
            metadata = {
                'level': record.levelname,
                'logger': record.name,
                'file': record.filename,
                'line': record.lineno,
                'func': record.funcName
            }

            # Log to AuditLogger
            # Use 'debug' resource_type for debug logs, 'system' for others
            resource_type = 'debug' if record.levelno == logging.DEBUG else 'system'
            
            AuditLogger.log_event(
                action=action,
                resource_type=resource_type,
                status=status,
                metadata=metadata,
                error_message=msg if status == 'failure' else msg  # Store message in error_message or we need a place for it
            )
            # AuditLogger.log_event uses error_message for the main message if it's an error.
            # But for INFO/DEBUG, it doesn't have a 'message' field in the model other than metadata.
            # Let's put the message in metadata as well.
            metadata['message'] = msg
            
            # If it's not an error, we still want to save it. 
            # AuditLogger saves 'error_message' column. 
            # Ideally we should have a 'message' column, but we can reuse error_message or metadata.
            # Let's stick to metadata for the message content for non-errors.

        except Exception:
            self.handleError(record)
