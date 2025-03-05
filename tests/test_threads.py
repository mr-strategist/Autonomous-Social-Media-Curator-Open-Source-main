import unittest
from unittest.mock import patch, MagicMock
from social_media_bot.platforms.threads import Threads, ThreadsError, ThreadsAuthenticationError, ThreadsPostingError
from social_media_bot.config.platforms import Platform

class TestThreads(unittest.TestCase):
    def setUp(self):
        self.threads = Threads()
        
    @patch('selenium.webdriver.Chrome')
    def test_authentication(self, mock_chrome):
        # Test successful authentication
        mock_driver = MagicMock()
        mock_chrome.return_value = mock_driver
        
        # Mock successful login
        mock_driver.find_element.return_value = MagicMock()
        
        result = self.threads.authenticate()
        self.assertTrue(result)
        self.assertTrue(self.threads.is_authenticated)
    
    def test_authentication_failure(self):
        # Test authentication failure
        with patch('selenium.webdriver.Chrome') as mock_chrome:
            mock_driver = MagicMock()
            mock_chrome.return_value = mock_driver
            mock_driver.find_element.side_effect = Exception("Login failed")
            
            with self.assertRaises(ThreadsAuthenticationError):
                self.threads.authenticate()
                
    def test_missing_credentials(self):
        # Test missing credentials
        with patch.dict('os.environ', {'INSTAGRAM_USERNAME': '', 'INSTAGRAM_PASSWORD': ''}):
            threads = Threads()
            result = threads.authenticate()
            self.assertFalse(result)
        
    def test_content_formatting(self):
        # Test content formatting
        content = "Test content" * 100  # Long content
        formatted = self.threads._format_content(content)
        self.assertLessEqual(len(formatted), 500)
        
        # Test empty content
        formatted = self.threads._format_content("")
        self.assertEqual(formatted, "")
        
        # Test newline handling
        content = "Line 1\n\nLine 2\nLine 3"
        formatted = self.threads._format_content(content)
        self.assertEqual(formatted.count('\n\n'), 2)
        
    def test_post_content(self):
        # Test successful posting
        with patch.object(Threads, 'authenticate', return_value=True):
            with patch('selenium.webdriver.Chrome'):
                result = self.threads.post_content("Test post")
                self.assertTrue(result['success'])
                self.assertEqual(result['platform'], 'threads')
    
    def test_post_content_failure(self):
        # Test posting failure
        with patch.object(Threads, 'authenticate', return_value=True):
            with patch('selenium.webdriver.Chrome') as mock_chrome:
                mock_driver = MagicMock()
                mock_chrome.return_value = mock_driver
                mock_driver.find_element.side_effect = Exception("Posting failed")
                
                with self.assertRaises(ThreadsPostingError):
                    self.threads.post_content("Test post")
    
    def test_check_status(self):
        # Test status check
        with patch('requests.get') as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            self.assertTrue(self.threads.check_status())
            
            mock_get.return_value = MagicMock(status_code=500)
            self.assertFalse(self.threads.check_status())
            
            mock_get.side_effect = Exception("Connection error")
            self.assertFalse(self.threads.check_status())
            
    def tearDown(self):
        # Clean up after each test
        if self.threads.driver:
            self.threads.driver.quit() 