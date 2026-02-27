"""
Health check endpoint.
"""
from flask import Blueprint, jsonify
from datetime import datetime

health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        'status': 'healthy',
        'service': 'prism-backend',
        'timestamp': datetime.utcnow().isoformat()
    })


@health_bp.route('/')
def root():
    """Root endpoint."""
    return jsonify({
        'message': 'PRISM Parking API',
        'version': '1.0.0',
        'docs': '/api/v1'
    })
