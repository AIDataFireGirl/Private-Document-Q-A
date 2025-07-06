"""
Web Routes Module for Private Document Q&A System.
Handles web interface routes and templates.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
from pathlib import Path
from typing import Dict, Any

# Local imports
from config.settings import Config
from core.document_indexer import DocumentIndexer
from core.qa_engine import QAEngine


class WebRouter:
    """
    Web Router for handling web interface routes.
    
    This class provides functionality to:
    - Serve web pages
    - Handle form submissions
    - Provide chat interface
    - Manage document uploads via web
    """
    
    def __init__(self, app: Flask, config: Config):
        """
        Initialize the Web Router.
        
        Args:
            app: Flask application instance
            config: Application configuration
        """
        self.app = app
        self.config = config
        
        # Initialize core components
        self.document_indexer = DocumentIndexer(config)
        self.qa_engine = QAEngine(config, self.document_indexer)
        
        # Register routes
        self._register_routes()
    
    def _register_routes(self):
        """Register all web routes."""
        
        # Main pages
        @self.app.route('/')
        def index():
            """Main page with chat interface."""
            return render_template('index.html')
        
        @self.app.route('/upload')
        def upload_page():
            """Document upload page."""
            return render_template('upload.html')
        
        @self.app.route('/documents')
        def documents_page():
            """Documents management page."""
            return render_template('documents.html')
        
        @self.app.route('/stats')
        def stats_page():
            """System statistics page."""
            return render_template('stats.html')
        
        # API endpoints for web interface
        @self.app.route('/api/web/chat', methods=['POST'])
        def web_chat():
            """Handle chat messages from web interface."""
            return self._handle_web_chat()
        
        @self.app.route('/api/web/upload', methods=['POST'])
        def web_upload():
            """Handle file uploads from web interface."""
            return self._handle_web_upload()
        
        @self.app.route('/api/web/documents')
        def web_documents():
            """Get documents for web interface."""
            return self._handle_web_documents()
        
        @self.app.route('/api/web/stats')
        def web_stats():
            """Get stats for web interface."""
            return self._handle_web_stats()
    
    def _handle_web_chat(self) -> Dict[str, Any]:
        """Handle chat messages from web interface."""
        try:
            data = request.get_json()
            if not data or 'message' not in data:
                return jsonify({'error': 'Message is required'}), 400
            
            message = data['message']
            
            # Process the question
            response = self.qa_engine.process_question(message)
            
            return jsonify(response)
            
        except Exception as e:
            return jsonify({'error': f'Chat failed: {str(e)}'}), 500
    
    def _handle_web_upload(self) -> Dict[str, Any]:
        """Handle file uploads from web interface."""
        try:
            if 'file' not in request.files:
                return jsonify({'error': 'No file provided'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'error': 'No file selected'}), 400
            
            # Save and index the file
            documents_dir = self.config.DOCUMENTS_DIR
            documents_dir.mkdir(exist_ok=True)
            
            file_path = documents_dir / file.filename
            file.save(str(file_path))
            
            # Index the document
            result = self.document_indexer.index_document(file_path)
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': 'Document uploaded and indexed successfully',
                    'file_name': file.filename
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to index document')
                }), 500
                
        except Exception as e:
            return jsonify({'error': f'Upload failed: {str(e)}'}), 500
    
    def _handle_web_documents(self) -> Dict[str, Any]:
        """Get documents for web interface."""
        try:
            documents_dir = self.config.DOCUMENTS_DIR
            if not documents_dir.exists():
                return jsonify({'documents': []})
            
            documents = []
            for file_path in documents_dir.iterdir():
                if file_path.is_file():
                    documents.append({
                        'name': file_path.name,
                        'size': file_path.stat().st_size,
                        'modified': file_path.stat().st_mtime
                    })
            
            return jsonify({'documents': documents})
            
        except Exception as e:
            return jsonify({'error': f'Failed to get documents: {str(e)}'}), 500
    
    def _handle_web_stats(self) -> Dict[str, Any]:
        """Get stats for web interface."""
        try:
            index_stats = self.document_indexer.get_index_stats()
            qa_stats = self.qa_engine.get_engine_stats()
            
            return jsonify({
                'index_stats': index_stats,
                'qa_stats': qa_stats
            })
            
        except Exception as e:
            return jsonify({'error': f'Failed to get stats: {str(e)}'}), 500 