"""
Q&A Engine Module for Private Document Q&A System.
Handles question processing, answer generation, and response formatting.
"""

import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

# Local imports
from config.settings import Config
from core.document_indexer import DocumentIndexer
from utils.validators import QuestionValidator


class QAEngine:
    """
    Q&A Engine for processing questions and generating answers.
    
    This class provides functionality to:
    - Process and validate user questions
    - Generate context-aware answers
    - Format responses with metadata
    - Handle different types of queries
    """
    
    def __init__(self, config: Config, document_indexer: DocumentIndexer):
        """
        Initialize the QA Engine.
        
        Args:
            config: Application configuration
            document_indexer: Document indexer instance
        """
        self.config = config
        self.document_indexer = document_indexer
        self.question_validator = QuestionValidator()
        
        # Predefined question patterns for better processing
        self.question_patterns = {
            'summary': r'\b(summary|summarize|overview|brief)\b',
            'specific': r'\b(what|how|why|when|where|who)\b',
            'comparison': r'\b(compare|difference|similar|versus|vs)\b',
            'analysis': r'\b(analyze|analysis|examine|study)\b'
        }
    
    def process_question(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        Process a user question and generate an answer.
        
        Args:
            question: The user's question
            **kwargs: Additional parameters (document_id, user_id, etc.)
            
        Returns:
            Dictionary containing the answer and metadata
        """
        try:
            # Validate question
            validation_result = self.question_validator.validate(question)
            if not validation_result['valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'question': question
                }
            
            # Analyze question type
            question_type = self._analyze_question_type(question)
            
            # Generate answer using document indexer
            answer = self.document_indexer.query_index(
                question,
                similarity_top_k=kwargs.get('similarity_top_k', 3),
                response_mode=kwargs.get('response_mode', 'compact')
            )
            
            # Format response
            response = self._format_response(
                question=question,
                answer=answer,
                question_type=question_type,
                metadata=kwargs
            )
            
            logger.info(f"Successfully processed question: {question[:50]}...")
            return response
            
        except Exception as e:
            logger.error(f"Failed to process question '{question}': {e}")
            return {
                'success': False,
                'error': f"Failed to process question: {str(e)}",
                'question': question,
                'timestamp': datetime.now().isoformat()
            }
    
    def batch_process_questions(self, questions: List[str], **kwargs) -> List[Dict[str, Any]]:
        """
        Process multiple questions in batch.
        
        Args:
            questions: List of questions to process
            **kwargs: Additional parameters
            
        Returns:
            List of response dictionaries
        """
        results = []
        
        for question in questions:
            result = self.process_question(question, **kwargs)
            results.append(result)
            
            # Add batch metadata
            result['batch_index'] = len(results) - 1
            result['total_in_batch'] = len(questions)
        
        return results
    
    def get_suggested_questions(self, document_context: str = None) -> List[str]:
        """
        Generate suggested questions based on indexed documents.
        
        Args:
            document_context: Optional context to focus suggestions
            
        Returns:
            List of suggested questions
        """
        suggestions = [
            "What is the main topic of the documents?",
            "Can you summarize the key points?",
            "What are the most important findings?",
            "How does this relate to [specific topic]?",
            "What are the main conclusions?"
        ]
        
        if document_context:
            # Add context-specific suggestions
            suggestions.extend([
                f"What does the document say about {document_context}?",
                f"How is {document_context} addressed?",
                f"What are the implications for {document_context}?"
            ])
        
        return suggestions
    
    def get_answer_metadata(self, question: str, answer: str) -> Dict[str, Any]:
        """
        Extract metadata from a question-answer pair.
        
        Args:
            question: The original question
            answer: The generated answer
            
        Returns:
            Dictionary containing metadata
        """
        return {
            'question_length': len(question),
            'answer_length': len(answer),
            'question_type': self._analyze_question_type(question),
            'has_citations': self._has_citations(answer),
            'confidence_score': self._estimate_confidence(answer),
            'processing_time': datetime.now().isoformat()
        }
    
    def _analyze_question_type(self, question: str) -> str:
        """
        Analyze the type of question being asked.
        
        Args:
            question: The question to analyze
            
        Returns:
            Question type (summary, specific, comparison, analysis, general)
        """
        question_lower = question.lower()
        
        for question_type, pattern in self.question_patterns.items():
            if re.search(pattern, question_lower):
                return question_type
        
        return 'general'
    
    def _format_response(self, question: str, answer: str, 
                        question_type: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format the response with metadata and structure.
        
        Args:
            question: Original question
            answer: Generated answer
            question_type: Type of question
            metadata: Additional metadata
            
        Returns:
            Formatted response dictionary
        """
        # Extract answer metadata
        answer_metadata = self.get_answer_metadata(question, answer)
        
        # Build response
        response = {
            'success': True,
            'question': question,
            'answer': answer,
            'question_type': question_type,
            'metadata': {
                **answer_metadata,
                **metadata,
                'timestamp': datetime.now().isoformat(),
                'model_used': self.config.OPENAI_MODEL,
                'embedding_model': self.config.EMBEDDING_MODEL
            }
        }
        
        # Add confidence indicators
        if answer_metadata['confidence_score'] > 0.8:
            response['metadata']['high_confidence'] = True
        elif answer_metadata['confidence_score'] < 0.5:
            response['metadata']['low_confidence'] = True
            response['metadata']['suggestion'] = "Consider rephrasing your question for better results."
        
        return response
    
    def _has_citations(self, answer: str) -> bool:
        """
        Check if the answer contains citations or references.
        
        Args:
            answer: The answer text
            
        Returns:
            True if citations are present, False otherwise
        """
        citation_patterns = [
            r'\[.*?\]',  # [citation]
            r'\(.*?\d{4}.*?\)',  # (Author, 2024)
            r'according to',
            r'reference',
            r'source'
        ]
        
        answer_lower = answer.lower()
        return any(re.search(pattern, answer_lower) for pattern in citation_patterns)
    
    def _estimate_confidence(self, answer: str) -> float:
        """
        Estimate confidence score based on answer characteristics.
        
        Args:
            answer: The answer text
            
        Returns:
            Confidence score between 0 and 1
        """
        # Simple heuristics for confidence estimation
        confidence = 0.5  # Base confidence
        
        # Factors that increase confidence
        if len(answer) > 100:
            confidence += 0.2
        if self._has_citations(answer):
            confidence += 0.2
        if 'I don\'t know' not in answer.lower() and 'cannot' not in answer.lower():
            confidence += 0.1
        
        # Factors that decrease confidence
        if len(answer) < 50:
            confidence -= 0.2
        if 'unclear' in answer.lower() or 'ambiguous' in answer.lower():
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the QA engine.
        
        Returns:
            Dictionary containing engine statistics
        """
        index_stats = self.document_indexer.get_index_stats()
        
        return {
            'engine_type': 'LlamaIndex QA Engine',
            'config': {
                'model': self.config.OPENAI_MODEL,
                'embedding_model': self.config.EMBEDDING_MODEL,
                'max_file_size': self.config.MAX_FILE_SIZE,
                'allowed_extensions': self.config.ALLOWED_EXTENSIONS
            },
            'index_stats': index_stats,
            'question_patterns': list(self.question_patterns.keys()),
            'timestamp': datetime.now().isoformat()
        } 