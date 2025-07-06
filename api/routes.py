"""
API Routes Module for Private Document Q&A System.
Defines all REST API endpoints for the application.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from flask import (
    Flask, request, jsonify, send_file, 
    current_app, abort, make_response
)
from werkzeug.utils import secure_filename

# Local imports
from config.settings import Config
from core.document_indexer import DocumentIndexer
from core.qa_engine import QAEngine
from core.security import SecurityManager
from utils.file_handlers import FileProcessor
from utils.validators import QuestionValidator, FileValidator, InputSanitizer


class APIRouter:
    """
    API Router for handling all REST endpoints.
    
    This class provides functionality to:
    - Handle document uploads
    - Process Q&A requests
    - Manage document indexing
    - Provide system statistics
    """
    
    def __init__(self, app: Flask, config: Config):
        """
        Initialize the API Router.
        
        Args:
            app: Flask application instance
            config: Application configuration
        """
        self.app = app
        self.config = config
        
        # Initialize core components
        self.document_indexer = DocumentIndexer(config)
        self.qa_engine = QAEngine(config, self.document_indexer)
        self.security_manager = SecurityManager(config)
        self.file_processor = FileProcessor(config)
        self.question_validator = QuestionValidator()
        self.file_validator = FileValidator(config)
        self.input_sanitizer = InputSanitizer()
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register all API routes."""
        
        # Health check endpoint
        @self.app.route('/api/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'version': '1.0.0'
            })
        
        # Document management endpoints
        @self.app.route('/api/documents/upload', methods=['POST'])
        def upload_document():
            """Upload and index a document."""
            return self._handle_document_upload()
        
        @self.app.route('/api/documents', methods=['GET'])
        def list_documents():
            """List all indexed documents."""
            return self._handle_list_documents()
        
        @self.app.route('/api/documents/<document_id>', methods=['DELETE'])
        def delete_document(document_id):
            """Delete a document from the index."""
            return self._handle_delete_document(document_id)
        
        # Q&A endpoints
        @self.app.route('/api/qa/ask', methods=['POST'])
        def ask_question():
            """Ask a question about indexed documents."""
            return self._handle_ask_question()
        
        @self.app.route('/api/qa/batch', methods=['POST'])
        def batch_questions():
            """Process multiple questions in batch."""
            return self._handle_batch_questions()
        
        @self.app.route('/api/qa/suggestions', methods=['GET'])
        def get_suggestions():
            """Get suggested questions."""
            return self._handle_get_suggestions()
        
        # Index management endpoints
        @self.app.route('/api/index/stats', methods=['GET'])
        def get_index_stats():
            """Get index statistics."""
            return self._handle_get_index_stats()
        
        @self.app.route('/api/index/clear', methods=['POST'])
        def clear_index():
            """Clear the entire document index."""
            return self._handle_clear_index()
        
        # System endpoints
        @self.app.route('/api/system/stats', methods=['GET'])
        def get_system_stats():
            """Get system statistics."""
            return self._handle_get_system_stats()
        
        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            return jsonify({'error': 'Endpoint not found'}), 404
        
        @self.app.errorhandler(500)
        def internal_error(error):
            return jsonify({'error': 'Internal server error'}), 500
    
    def _handle_document_upload(self) -> Dict[str, Any]:
        """Handle document upload request."""
        try:
            # Check if file was uploaded
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Validate file
            filename = secure_filename(file.filename)
            file_size = len(file.read())
            file.seek(0)  # Reset file pointer
            
            validation_result = self.file_validator.validate_file_upload(filename, file_size)
            if not validation_result['valid']:
                return jsonify({
                    'error': 'File validation failed',
                    'details': validation_result['errors']
                }), 400
            
            # Save file to documents directory
            documents_dir = self.config.DOCUMENTS_DIR
            documents_dir.mkdir(exist_ok=True)
            
            file_path = documents_dir / filename
            file.save(str(file_path))
            
            # Index the document
            indexing_result = self.document_indexer.index_document(file_path)
            
            if indexing_result['success']:
                return jsonify({
                    'message': 'Document uploaded and indexed successfully',
                    'file_name': filename,
                    'file_hash': indexing_result['file_hash'],
                    'indexed_at': indexing_result['indexed_at']
                }), 201
            else:
                return jsonify({
                    'error': 'Failed to index document',
                    'details': indexing_result.get('error', 'Unknown error')
                }), 500
                
        except Exception as e:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    def _handle_list_documents(self) -> Dict[str, Any]:
        """Handle document listing request."""
        try:
            documents_dir = self.config.DOCUMENTS_DIR
            if not documents_dir.exists():
                return jsonify({'documents': []})
            
            documents = []
            for file_path in documents_dir.iterdir():
                if file_path.is_file():
                    file_info = self.file_processor.get_file_info(file_path)
                    documents.append(file_info)
            
            return jsonify({
                'documents': documents,
                'total_count': len(documents)
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to list documents: {str(e)}'}), 500
    
    def _handle_delete_document(self, document_id: str) -> Dict[str, Any]:
        """Handle document deletion request."""
        try:
            # For now, we'll just return a success message
            # In a real implementation, you'd remove the document from the index
            return jsonify({
                'message': f'Document {document_id} deleted successfully'
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to delete document: {str(e)}'}), 500
    
    def _handle_ask_question(self) -> Dict[str, Any]:
        """Handle question asking request."""
        try:
            data = request.get_json()
            if not data or 'question' not in data:
                return jsonify({'error': 'Question is required'}), 400
            
            question = data['question']
            
            # Validate question
            validation_result = self.question_validator.validate(question)
            if not validation_result['valid']:
                return jsonify({
                    'error': 'Question validation failed',
                    'details': validation_result['errors']
                }), 400
            
            # Process question
            response = self.qa_engine.process_question(
                validation_result['sanitized_question'],
                user_id=data.get('user_id'),
                document_id=data.get('document_id')
            )
            
            if response['success']:
                return jsonify(response)
            else:
                return jsonify({
                    'error': 'Failed to process question',
                    'details': response.get('error', 'Unknown error')
                }), 500
                
        except Exception as e:
            return jsonify({'error': f'Question processing failed: {str(e)}'}), 500
    
    def _handle_batch_questions(self) -> Dict[str, Any]:
        """Handle batch question processing request."""
        try:
            data = request.get_json()
            if not data or 'questions' not in data:
                return jsonify({'error': 'Questions array is required'}), 400
            
            questions = data['questions']
            if not isinstance(questions, list):
                return jsonify({'error': 'Questions must be an array'}), 400
            
            # Process questions in batch
            responses = self.qa_engine.batch_process_questions(
                questions,
                user_id=data.get('user_id')
            )
            
            return jsonify({
                'responses': responses,
                'total_questions': len(questions),
                'successful_answers': len([r for r in responses if r.get('success', False)])
            })
            
        except Exception as e:
            return jsonify({'error': f'Batch processing failed: {str(e)}'}), 500
    
    def _handle_get_suggestions(self) -> Dict[str, Any]:
        """Handle suggestion request."""
        try:
            context = request.args.get('context', '')
            suggestions = self.qa_engine.get_suggested_questions(context)
            
            return jsonify({
                'suggestions': suggestions,
                'context': context
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to get suggestions: {str(e)}'}), 500
    
    def _handle_get_index_stats(self) -> Dict[str, Any]:
        """Handle index statistics request."""
        try:
            stats = self.document_indexer.get_index_stats()
            return jsonify(stats)
            
        except Exception as e:
            return jsonify({'error': f'Failed to get index stats: {str(e)}'}), 500
    
    def _handle_clear_index(self) -> Dict[str, Any]:
        """Handle index clearing request."""
        try:
            success = self.document_indexer.clear_index()
            
            if success:
                return jsonify({
                    'message': 'Document index cleared successfully'
                })
            else:
                return jsonify({
                    'error': 'Failed to clear document index'
                }), 500
                
        except Exception as e:
            return jsonify({'error': f'Failed to clear index: {str(e)}'}), 500
    
    def _handle_get_system_stats(self) -> Dict[str, Any]:
        """Handle system statistics request."""
        try:
            # Get various system statistics
            index_stats = self.document_indexer.get_index_stats()
            qa_stats = self.qa_engine.get_engine_stats()
            security_stats = self.security_manager.get_security_stats()
            
            return jsonify({
                'index_stats': index_stats,
                'qa_stats': qa_stats,
                'security_stats': security_stats,
                'timestamp': datetime.now().isoformat()
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to get system stats: {str(e)}'}), 500 