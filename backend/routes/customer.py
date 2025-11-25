import os
import json
from flask import Blueprint, request, jsonify, send_file, current_app
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge, NotFound
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from models.customer import db, Customer, CustomerFile, Rule, Alarm, ValidationLog
from utils.xml_utils import XMLValidator, RuleParser, AlarmParser
from utils.tenant_auth import require_customer_token, log_tenant_access
from utils.audit_logger import AuditLogger, AuditAction, audit_log
from utils.file_utils import generate_secure_filename, get_customer_upload_path, get_secure_file_path, validate_file_access, cleanup_old_files
import tempfile
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

customer_bp = Blueprint('customer', __name__)

ALLOWED_EXTENSIONS = {'xml'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@customer_bp.route('/customers', methods=['GET'])
def get_customers():
    """Get all customers (optionally paginated)"""
    try:
        page = request.args.get('page', type=int)
        per_page = request.args.get('per_page', type=int)

        query = Customer.query.order_by(Customer.name.asc())

        if page is not None or per_page is not None:
            page = page or 1
            per_page = per_page or 50
            total = query.count()
            customers = query.offset((page - 1) * per_page).limit(per_page).all()
        else:
            customers = query.all()
            total = len(customers)

        return jsonify({
            'success': True,
            'customers': [customer.to_dict() for customer in customers],
            'total': total,
            'page': page or 1,
            'per_page': per_page or total
        })
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching customers: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve customers due to a database error.'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching customers: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['GET'])
@require_customer_token
def get_customer(customer_id):
    """Get specific customer details"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        files = CustomerFile.query.filter_by(customer_id=customer_id).all()
        validation_logs = ValidationLog.query.filter_by(
            customer_id=customer_id
        ).order_by(ValidationLog.created_at.desc()).limit(10).all()
        
        customer_data = customer.to_dict()
        customer_data['files'] = [file.to_dict() for file in files]
        customer_data['recent_validations'] = [log.to_dict() for log in validation_logs]
        
        return jsonify({
            'success': True,
            'customer': customer_data
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve customer details due to a database error.'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers', methods=['POST'])
def create_customer():
    """Create a new customer"""
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({'success': False, 'error': 'Customer name is required'}), 400

    try:
        existing_customer = Customer.query.filter(Customer.name.ilike(data['name'])).first()
        if existing_customer:
            return jsonify({
                'success': False,
                'error': 'Customer with this name already exists'
            }), 400

        customer = Customer(
            name=data['name'],
            description=data.get('description'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone')
        )
        
        db.session.add(customer)
        db.session.commit()
        
        upload_root = current_app.config.get('UPLOAD_DIR') or current_app.config.get('UPLOAD_ROOT')
        customer_dir = os.path.join(upload_root, str(customer.id))
        os.makedirs(customer_dir, exist_ok=True)
        
        AuditLogger.log_success(
            action=AuditAction.CUSTOMER_CREATE,
            resource_type='customer',
            resource_id=customer.id,
            customer_id=customer.id,
            changes={'name': {'before': None, 'after': customer.name}}
        )

        return jsonify({
            'success': True,
            'customer': customer.to_dict()
        }), 201
        
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Customer with this name already exists'
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error creating customer: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to create customer due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error creating customer: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['PUT'])
@require_customer_token
def update_customer(customer_id):
    """Update customer information"""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Request data is required'}), 400

    try:
        customer = Customer.query.get_or_404(customer_id)
        old_data = customer.to_dict()

        if 'name' in data:
            existing = Customer.query.filter(
                Customer.name.ilike(data['name']),
                Customer.id != customer_id
            ).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': 'Customer with this name already exists'
                }), 400
            customer.name = data['name']
        
        # Update other fields
        for field in ['description', 'contact_email', 'contact_phone']:
            if field in data:
                setattr(customer, field, data[field])
        
        db.session.commit()
        
        AuditLogger.log_success(
            action=AuditAction.CUSTOMER_UPDATE,
            resource_type='customer',
            resource_id=customer.id,
            customer_id=customer.id,
            changes={'before': old_data, 'after': customer.to_dict()}
        )

        return jsonify({
            'success': True,
            'customer': customer.to_dict()
        })
        
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except IntegrityError:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Customer with this name already exists'
        }), 400
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error updating customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to update customer due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error updating customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
@require_customer_token
def delete_customer(customer_id):
    """Delete a customer and all associated data"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        customer_name = customer.name
        
        customer_dir = get_customer_upload_path(customer_id)
        if os.path.exists(customer_dir):
            import shutil
            shutil.rmtree(customer_dir)
        
        db.session.delete(customer)
        db.session.commit()
        
        AuditLogger.log_success(
            action=AuditAction.CUSTOMER_DELETE,
            resource_type='customer',
            resource_id=customer_id,
            customer_id=customer_id,
            metadata={'customer_name': customer_name}
        )

        return jsonify({
            'success': True,
            'message': 'Customer deleted successfully'
        })
        
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting customer {customer_id}: {e}")
        # Log failure to AuditLog
        try:
            AuditLogger.log_failure(
                action=AuditAction.CUSTOMER_DELETE,
                resource_type='customer',
                resource_id=customer_id,
                customer_id=customer_id,
                error_message=str(e),
                status_code=500
            )
        except:
            pass
            
        return jsonify({
            'success': False,
            'error': 'Failed to delete customer due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error deleting customer {customer_id}: {e}")
        # Log failure to AuditLog
        try:
            AuditLogger.log_failure(
                action=AuditAction.CUSTOMER_DELETE,
                resource_type='customer',
                resource_id=customer_id,
                customer_id=customer_id,
                error_message=str(e),
                status_code=500
            )
        except:
            pass

        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>/files', methods=['GET'])
@require_customer_token
def get_customer_files(customer_id):
    """Get all files for a customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        files = CustomerFile.query.filter_by(customer_id=customer_id).all()
        return jsonify({
            'success': True,
            'files': [file.to_dict() for file in files]
        })
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except SQLAlchemyError as e:
        logger.error(f"Database error fetching files for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve files due to a database error.'
        }), 500
    except Exception as e:
        logger.error(f"Unexpected error fetching files for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>/files/upload', methods=['POST'])
@require_customer_token
def upload_file(customer_id):
    """Upload and process XML files for a customer"""
    try:
        customer = Customer.query.get_or_404(customer_id)
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400
        
        file = request.files['file']
        file_type = request.form.get('file_type')
        
        if not file or file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
        
        if not file_type or file_type not in ['rule', 'alarm']:
            return jsonify({'success': False, 'error': 'file_type must be either "rule" or "alarm"'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Only XML files are allowed'}), 400
        
        # Generate secure filename and get customer upload path
        secure_filename_generated = generate_secure_filename(customer_id, file.filename, file_type)
        file_path = get_secure_file_path(customer_id, secure_filename_generated)
        
        # Clean up old files of the same type before saving new one
        cleanup_old_files(customer_id, file_type, keep_latest=False)
        
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        # Use a transaction for database operations
        with db.session.begin_nested():
            existing_file = CustomerFile.query.filter_by(
                customer_id=customer_id,
                file_type=file_type
            ).first()
            
            if existing_file:
                existing_file.filename = file.filename  # Keep original filename for display
                existing_file.file_path = file_path     # Store secure file path
                existing_file.file_size = file_size
                existing_file.validation_status = 'pending'
                existing_file.validation_errors = None
                customer_file = existing_file
            else:
                customer_file = CustomerFile(
                    customer_id=customer_id,
                    file_type=file_type,
                    filename=file.filename,  # Keep original filename for display
                    file_path=file_path,     # Store secure file path
                    file_size=file_size
                )
                db.session.add(customer_file)
            
            db.session.flush() # Ensure customer_file has an ID

        # Asynchronous processing would be ideal here, but for now, we process synchronously
        # In a production environment, this should be offloaded to a background worker (e.g., Celery)
        validation_result = _process_uploaded_file(customer_id, file_path, file_type)
        
        with db.session.begin_nested():
            customer_file.validation_status = 'valid' if validation_result['success'] else 'invalid'
            customer_file.validation_errors = json.dumps(validation_result.get('errors', []))

        db.session.commit()
        
        items_added_key = 'rules_added' if file_type == 'rule' else 'alarms_added'

        response = jsonify({
            'success': True,
            'file': customer_file.to_dict(),
            'validation': validation_result,
            items_added_key: validation_result.get('items_processed', 0)
        })

        # Log successful upload
        AuditLogger.log_success(
            action=AuditAction.FILE_UPLOAD,
            resource_type='file',
            resource_id=customer_file.id,
            customer_id=customer_id,
            metadata={
                'filename': file.filename,
                'file_type': file_type,
                'file_size': file_size,
                'validation_status': customer_file.validation_status
            }
        )

        return response, 201
        
    except NotFound:
        return jsonify({'success': False, 'error': 'Customer not found'}), 404
    except RequestEntityTooLarge:
        return jsonify({'success': False, 'error': 'File too large'}), 413
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error uploading file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to upload file due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error uploading file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred during file upload.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>/files/<file_type>', methods=['GET'])
@require_customer_token
def download_file(customer_id, file_type):
    """Download a customer file"""
    try:
        customer_file = CustomerFile.query.filter_by(
            customer_id=customer_id,
            file_type=file_type
        ).first_or_404()
        
        # Validate file access security
        try:
            validate_file_access(customer_id, customer_file.file_path)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 403
        
        if not os.path.exists(customer_file.file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        return send_file(
            customer_file.file_path,
            as_attachment=True,
            download_name=customer_file.filename
        )
        
    except NotFound:
        return jsonify({'success': False, 'error': 'File record not found'}), 404
    except Exception as e:
        logger.error(f"Error downloading file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred during file download.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>/files/<file_type>', methods=['DELETE'])
@require_customer_token
def delete_file(customer_id, file_type):
    """Delete a customer file"""
    try:
        customer_file = CustomerFile.query.filter_by(
            customer_id=customer_id,
            file_type=file_type
        ).first_or_404()
        
        with db.session.begin_nested():
            # Validate file access before deletion
            try:
                validate_file_access(customer_id, customer_file.file_path)
                if os.path.exists(customer_file.file_path):
                    os.remove(customer_file.file_path)
            except ValueError as e:
                return jsonify({'success': False, 'error': f'Security error: {str(e)}'}), 403
            
            if file_type == 'rule':
                Rule.query.filter_by(customer_id=customer_id).delete()
            elif file_type == 'alarm':
                Alarm.query.filter_by(customer_id=customer_id).delete()
            
            db.session.delete(customer_file)
        
        db.session.commit()
        
        AuditLogger.log_success(
            action=AuditAction.FILE_DELETE,
            resource_type='file',
            resource_id=customer_file.id,
            customer_id=customer_id,
            metadata={'file_type': file_type, 'filename': customer_file.filename}
        )

        return jsonify({
            'success': True,
            'message': f'{file_type.title()} file deleted successfully'
        })
        
    except NotFound:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error deleting file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to delete file due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error deleting file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred during file deletion.'
        }), 500

@customer_bp.route('/customers/<int:customer_id>/files/<file_type>/validate', methods=['POST'])
@require_customer_token
def validate_file(customer_id, file_type):
    """Validate a customer file"""
    try:
        customer_file = CustomerFile.query.filter_by(
            customer_id=customer_id,
            file_type=file_type
        ).first_or_404()
        
        # Validate file access security
        try:
            validate_file_access(customer_id, customer_file.file_path)
        except ValueError as e:
            return jsonify({'success': False, 'error': str(e)}), 403
        
        if not os.path.exists(customer_file.file_path):
            return jsonify({'success': False, 'error': 'File not found on disk'}), 404
        
        validation_result = _process_uploaded_file(customer_id, customer_file.file_path, file_type)
        
        with db.session.begin_nested():
            customer_file.validation_status = 'valid' if validation_result['success'] else 'invalid'
            customer_file.validation_errors = json.dumps(validation_result.get('errors', []))
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'validation': validation_result,
            'file': customer_file.to_dict()
        })
        
    except NotFound:
        return jsonify({'success': False, 'error': 'File not found'}), 404
    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error validating file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to validate file due to a database error.'
        }), 500
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error validating file for customer {customer_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred during file validation.'
        }), 500

def _process_uploaded_file(customer_id, file_path, file_type):
    """Process and validate uploaded XML file"""
    validator = XMLValidator()
    errors = []
    warnings = []
    items_processed = 0
    
    try:
        # Clear previous data for this file type
        if file_type == 'rule':
            Rule.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)
        elif file_type == 'alarm':
            Alarm.query.filter_by(customer_id=customer_id).delete(synchronize_session=False)

        # Validate and parse
        parser = RuleParser() if file_type == 'rule' else AlarmParser()
        validator_func = validator.validate_rule_xml if file_type == 'rule' else validator.validate_alarm_xml
        
        validation_result = validator_func(file_path)
        
        # Log validation result
        AuditLogger.log_event(
            action=AuditAction.FILE_VALIDATE,
            resource_type='file',
            status='success' if validation_result['valid'] else 'failure',
            customer_id=customer_id,
            metadata={
                'file_type': file_type,
                'file_path': file_path,
                'error_count': len(validation_result.get('errors', [])),
                'warning_count': len(validation_result.get('warnings', []))
            },
            error_message=json.dumps(validation_result.get('errors', [])) if not validation_result['valid'] else None
        )

        if validation_result['valid']:
            data_list = parser.parse_rule_file(file_path) if file_type == 'rule' else parser.parse_alarm_file(file_path)
            items_processed = len(data_list)
            model = Rule if file_type == 'rule' else Alarm
            
            for data_item in data_list:
                instance = model(customer_id=customer_id, **data_item)
                db.session.add(instance)
            
            # Log parsing result
            AuditLogger.log_success(
                action=AuditAction.FILE_PARSE,
                resource_type='file',
                customer_id=customer_id,
                metadata={
                    'file_type': file_type,
                    'items_processed': items_processed
                }
            )
        else:
            errors.extend(validation_result.get('errors', []))

        log = ValidationLog(
            customer_id=customer_id,
            file_type=file_type,
            validation_type='upload_processing',
            status='success' if not errors else 'error',
            message=f"Processed {file_type} file with {len(errors)} errors and {items_processed} items.",
            details=json.dumps({'errors': errors, 'warnings': warnings})
        )
        db.session.add(log)
        
        db.session.commit()
        
        return {
            'success': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'items_processed': items_processed
        }

    except SQLAlchemyError as e:
        db.session.rollback()
        logger.error(f"Database error processing file for customer {customer_id}: {e}")
        return {'success': False, 'errors': ['A database error occurred during file processing.'], 'warnings': [], 'items_processed': 0}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Unexpected error processing file for customer {customer_id}: {e}", exc_info=True)
        return {'success': False, 'errors': [f'An unexpected error occurred: {str(e)}'], 'warnings': [], 'items_processed': 0}
