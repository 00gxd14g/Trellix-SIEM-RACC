"""
File handling utilities for secure tenant-isolated file operations.

This module provides utilities for generating secure filenames and managing
file storage with tenant isolation to prevent cross-tenant access.
"""

import os
import uuid
import hashlib
from werkzeug.utils import secure_filename
from flask import current_app


def generate_secure_filename(customer_id, original_filename, file_type):
    """
    Generate a secure, randomized filename for tenant-isolated storage.
    
    Args:
        customer_id (int): The tenant/customer ID
        original_filename (str): The original uploaded filename
        file_type (str): Type of file ('rule' or 'alarm')
    
    Returns:
        str: A secure, randomized filename that prevents directory traversal
        and cross-tenant access
    """
    # Extract the file extension
    _, ext = os.path.splitext(original_filename)
    if not ext:
        ext = '.xml'  # Default extension for our XML files
    
    # Generate a random UUID-based filename
    random_uuid = str(uuid.uuid4())
    
    # Create a hash of customer_id + file_type for additional security
    hash_input = f"{customer_id}_{file_type}_{random_uuid}"
    file_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:12]
    
    # Combine to create secure filename
    secure_name = f"{file_type}_{file_hash}_{random_uuid[:8]}{ext}"
    
    return secure_name


def get_customer_upload_path(customer_id):
    """
    Get the secure upload path for a specific customer.
    
    Args:
        customer_id (int): The tenant/customer ID
    
    Returns:
        str: Absolute path to the customer's upload directory
    """
    upload_root = current_app.config['UPLOAD_ROOT']
    customer_path = os.path.join(upload_root, str(customer_id))
    
    # Ensure the directory exists
    os.makedirs(customer_path, exist_ok=True)
    
    return customer_path


def get_secure_file_path(customer_id, filename):
    """
    Get the full secure file path for a customer file.
    
    Args:
        customer_id (int): The tenant/customer ID
        filename (str): The secure filename
    
    Returns:
        str: Full absolute path to the file
    """
    customer_path = get_customer_upload_path(customer_id)
    return os.path.join(customer_path, filename)


def validate_file_access(customer_id, file_path):
    """
    Validate that a file path belongs to the specified customer and is secure.
    
    Args:
        customer_id (int): The tenant/customer ID
        file_path (str): The file path to validate
    
    Returns:
        bool: True if the file access is valid, False otherwise
    
    Raises:
        ValueError: If the file path is invalid or unsafe
    """
    # Get the expected customer path
    expected_customer_path = get_customer_upload_path(customer_id)
    
    # Resolve the absolute path to prevent directory traversal
    try:
        resolved_path = os.path.abspath(file_path)
        expected_path = os.path.abspath(expected_customer_path)
    except Exception:
        raise ValueError("Invalid file path")
    
    # Check if the file is within the customer's directory
    if not resolved_path.startswith(expected_path):
        raise ValueError("File access outside customer directory not allowed")
    
    return True


def cleanup_old_files(customer_id, file_type, keep_latest=True):
    """
    Clean up old files for a customer, optionally keeping the latest one.
    
    Args:
        customer_id (int): The tenant/customer ID
        file_type (str): Type of files to clean up ('rule' or 'alarm')
        keep_latest (bool): Whether to keep the most recent file
    
    Returns:
        int: Number of files cleaned up
    """
    customer_path = get_customer_upload_path(customer_id)
    
    if not os.path.exists(customer_path):
        return 0
    
    # Find all files of the specified type
    files = []
    for filename in os.listdir(customer_path):
        if filename.startswith(f"{file_type}_") and filename.endswith('.xml'):
            file_path = os.path.join(customer_path, filename)
            if os.path.isfile(file_path):
                files.append((file_path, os.path.getmtime(file_path)))
    
    if not files:
        return 0
    
    # Sort by modification time (newest first)
    files.sort(key=lambda x: x[1], reverse=True)
    
    # Determine which files to delete
    files_to_delete = files[1:] if keep_latest else files
    
    # Delete the files
    deleted_count = 0
    for file_path, _ in files_to_delete:
        try:
            os.remove(file_path)
            deleted_count += 1
        except OSError:
            # Log the error but continue with other files
            current_app.logger.warning(f"Failed to delete file: {file_path}")
    
    return deleted_count