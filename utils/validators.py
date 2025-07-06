"""
Validators Module for Private Document Q&A System.
Handles input validation and sanitization.
"""

import re
from typing import Dict, Any, List
from datetime import datetime


class QuestionValidator:
    """
    Validates and sanitizes user questions.
    
    This class provides functionality to:
    - Validate question format and content
    - Sanitize user input
    - Check for inappropriate content
    - Ensure questions meet quality standards
    """
    
    def __init__(self):
        """Initialize the QuestionValidator."""
        # Define validation patterns
        self.min_length = 3
        self.max_length = 500
        self.inappropriate_patterns = [
            r'\b(hack|crack|exploit|bypass)\b',
            r'\b(password|credential|secret)\b',
            r'\b(admin|root|sudo)\b',
            r'\b(delete|remove|drop)\s+(database|table|index)\b',
            r'\b(script|javascript|eval)\b'
        ]
        
        # Compile patterns for efficiency
        self.inappropriate_regex = re.compile('|'.join(self.inappropriate_patterns), re.IGNORECASE)
    
    def validate(self, question: str) -> Dict[str, Any]:
        """
        Validate a user question.
        
        Args:
            question: The question to validate
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'sanitized_question': question.strip()
        }
        
        try:
            # Check if question is provided
            if not question or not question.strip():
                result['valid'] = False
                result['errors'].append("Question cannot be empty")
                return result
            
            # Check question length
            question_length = len(question.strip())
            if question_length < self.min_length:
                result['valid'] = False
                result['errors'].append(f"Question must be at least {self.min_length} characters long")
            
            if question_length > self.max_length:
                result['valid'] = False
                result['errors'].append(f"Question cannot exceed {self.max_length} characters")
            
            # Check for inappropriate content
            if self.inappropriate_regex.search(question):
                result['valid'] = False
                result['errors'].append("Question contains inappropriate content")
            
            # Check for basic question structure
            if not self._has_question_structure(question):
                result['warnings'].append("Question may not be clear enough for best results")
            
            # Sanitize the question
            result['sanitized_question'] = self._sanitize_question(question)
            
            return result
            
        except Exception as e:
            result['valid'] = False
            result['errors'].append(f"Validation error: {str(e)}")
            return result
    
    def _has_question_structure(self, question: str) -> bool:
        """
        Check if the question has proper structure.
        
        Args:
            question: The question to check
            
        Returns:
            True if question has proper structure, False otherwise
        """
        # Check for question words
        question_words = ['what', 'how', 'why', 'when', 'where', 'who', 'which', 'can', 'could', 'would', 'should']
        question_lower = question.lower()
        
        # Check if question starts with a question word
        starts_with_question_word = any(question_lower.startswith(word) for word in question_words)
        
        # Check if question ends with question mark
        ends_with_question_mark = question.strip().endswith('?')
        
        # Check if question has sufficient content
        has_content = len(question.strip().split()) >= 3
        
        return starts_with_question_word or ends_with_question_mark or has_content
    
    def _sanitize_question(self, question: str) -> str:
        """
        Sanitize the question text.
        
        Args:
            question: The question to sanitize
            
        Returns:
            Sanitized question
        """
        # Remove extra whitespace
        sanitized = ' '.join(question.split())
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';']
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '')
        
        # Limit length
        if len(sanitized) > self.max_length:
            sanitized = sanitized[:self.max_length]
        
        return sanitized.strip()
    
    def get_validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics and rules.
        
        Returns:
            Dictionary containing validation rules and statistics
        """
        return {
            'min_length': self.min_length,
            'max_length': self.max_length,
            'inappropriate_patterns_count': len(self.inappropriate_patterns),
            'timestamp': datetime.now().isoformat()
        }


class FileValidator:
    """
    Validates file uploads and file-related operations.
    """
    
    def __init__(self, config):
        """
        Initialize the FileValidator.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.max_file_size = config.MAX_FILE_SIZE
        self.allowed_extensions = config.ALLOWED_EXTENSIONS
    
    def validate_file_upload(self, filename: str, file_size: int) -> Dict[str, Any]:
        """
        Validate a file upload.
        
        Args:
            filename: Name of the uploaded file
            file_size: Size of the file in bytes
            
        Returns:
            Validation result dictionary
        """
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file size
        if file_size > self.max_file_size:
            result['valid'] = False
            result['errors'].append(f"File size ({file_size} bytes) exceeds maximum allowed size")
        
        # Check file extension
        file_ext = self._get_file_extension(filename)
        if file_ext not in self.allowed_extensions:
            result['valid'] = False
            result['errors'].append(f"File type '{file_ext}' is not allowed")
        
        # Check filename for dangerous patterns
        if self._has_dangerous_filename(filename):
            result['valid'] = False
            result['errors'].append("Filename contains potentially dangerous characters")
        
        # Check for empty files
        if file_size == 0:
            result['warnings'].append("File is empty")
        
        return result
    
    def _get_file_extension(self, filename: str) -> str:
        """
        Extract file extension from filename.
        
        Args:
            filename: Name of the file
            
        Returns:
            File extension (without dot)
        """
        return filename.split('.')[-1].lower() if '.' in filename else ''
    
    def _has_dangerous_filename(self, filename: str) -> bool:
        """
        Check if filename contains dangerous patterns.
        
        Args:
            filename: Name of the file
            
        Returns:
            True if filename is dangerous, False otherwise
        """
        dangerous_patterns = ['..', '/', '\\', ':', '*', '?', '"', '<', '>', '|']
        return any(pattern in filename for pattern in dangerous_patterns)


class InputSanitizer:
    """
    Sanitizes various types of user input.
    """
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """
        Sanitize text input.
        
        Args:
            text: Text to sanitize
            max_length: Maximum allowed length
            
        Returns:
            Sanitized text
        """
        if not text:
            return ""
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', ';', '\\']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Limit length
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize a filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename
        """
        # Remove dangerous characters
        dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
        sanitized = filename
        
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = sanitized.rsplit('.', 1) if '.' in sanitized else (sanitized, '')
            sanitized = name[:255-len(ext)-1] + ('.' + ext if ext else '')
        
        return sanitized or 'file'
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.
        
        Args:
            email: Email address to validate
            
        Returns:
            True if email is valid, False otherwise
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format.
        
        Args:
            url: URL to validate
            
        Returns:
            True if URL is valid, False otherwise
        """
        pattern = r'^https?://[^\s/$.?#].[^\s]*$'
        return bool(re.match(pattern, url)) 