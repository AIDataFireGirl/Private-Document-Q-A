"""
Basic tests for the Private Document Q&A System.
"""

import pytest
from pathlib import Path
import tempfile
import shutil

# Local imports
from config.settings import get_config, TestingConfig
from utils.validators import QuestionValidator, FileValidator, InputSanitizer


class TestQuestionValidator:
    """Test the QuestionValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.validator = QuestionValidator()
    
    def test_valid_question(self):
        """Test that valid questions pass validation."""
        question = "What is the main topic of the document?"
        result = self.validator.validate(question)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
        assert 'sanitized_question' in result
    
    def test_empty_question(self):
        """Test that empty questions fail validation."""
        question = ""
        result = self.validator.validate(question)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "empty" in result['errors'][0].lower()
    
    def test_short_question(self):
        """Test that very short questions fail validation."""
        question = "Hi"
        result = self.validator.validate(question)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_long_question(self):
        """Test that very long questions fail validation."""
        question = "A" * 600  # Exceeds max length
        result = self.validator.validate(question)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    def test_inappropriate_content(self):
        """Test that inappropriate content is detected."""
        question = "How can I hack the system?"
        result = self.validator.validate(question)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "inappropriate" in result['errors'][0].lower()


class TestFileValidator:
    """Test the FileValidator class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.config = TestingConfig()
        self.validator = FileValidator(self.config)
    
    def test_valid_file_upload(self):
        """Test that valid file uploads pass validation."""
        filename = "test.pdf"
        file_size = 1024  # 1KB
        
        result = self.validator.validate_file_upload(filename, file_size)
        
        assert result['valid'] is True
        assert len(result['errors']) == 0
    
    def test_large_file(self):
        """Test that large files fail validation."""
        filename = "large.pdf"
        file_size = self.config.MAX_FILE_SIZE + 1024  # Exceeds limit
        
        result = self.validator.validate_file_upload(filename, file_size)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "size" in result['errors'][0].lower()
    
    def test_invalid_extension(self):
        """Test that invalid file extensions fail validation."""
        filename = "test.exe"
        file_size = 1024
        
        result = self.validator.validate_file_upload(filename, file_size)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "type" in result['errors'][0].lower()
    
    def test_dangerous_filename(self):
        """Test that dangerous filenames fail validation."""
        filename = "../../../etc/passwd"
        file_size = 1024
        
        result = self.validator.validate_file_upload(filename, file_size)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        assert "dangerous" in result['errors'][0].lower()


class TestInputSanitizer:
    """Test the InputSanitizer class."""
    
    def test_sanitize_text(self):
        """Test text sanitization."""
        text = "<script>alert('xss')</script>Hello World"
        sanitized = InputSanitizer.sanitize_text(text)
        
        assert "<script>" not in sanitized
        assert "Hello World" in sanitized
    
    def test_sanitize_filename(self):
        """Test filename sanitization."""
        filename = "file/with\\dangerous:chars*.txt"
        sanitized = InputSanitizer.sanitize_filename(filename)
        
        assert "/" not in sanitized
        assert "\\" not in sanitized
        assert ":" not in sanitized
        assert "*" not in sanitized
    
    def test_validate_email(self):
        """Test email validation."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "user+tag@example.org"
        ]
        
        invalid_emails = [
            "invalid-email",
            "@example.com",
            "user@",
            "user@.com"
        ]
        
        for email in valid_emails:
            assert InputSanitizer.validate_email(email) is True
        
        for email in invalid_emails:
            assert InputSanitizer.validate_email(email) is False
    
    def test_validate_url(self):
        """Test URL validation."""
        valid_urls = [
            "https://example.com",
            "http://www.example.org/path",
            "https://api.example.com/v1/endpoint"
        ]
        
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "example.com",
            "http://"
        ]
        
        for url in valid_urls:
            assert InputSanitizer.validate_url(url) is True
        
        for url in invalid_urls:
            assert InputSanitizer.validate_url(url) is False


class TestConfiguration:
    """Test configuration functionality."""
    
    def test_get_config(self):
        """Test that configuration can be loaded."""
        config = get_config()
        assert config is not None
        assert hasattr(config, 'OPENAI_MODEL')
        assert hasattr(config, 'MAX_FILE_SIZE')
    
    def test_testing_config(self):
        """Test that testing configuration works."""
        config = TestingConfig()
        assert config.TESTING is True
        assert config.DEBUG is True
        assert "memory" in config.DATABASE_URL


if __name__ == "__main__":
    pytest.main([__file__]) 