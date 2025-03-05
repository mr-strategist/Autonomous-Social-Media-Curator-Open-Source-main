import unittest
from unittest.mock import patch, MagicMock
import os
import json
from social_media_bot.platforms.threads_api import ThreadsAPI, ThreadsAPIAuthError, ThreadsAPIPostError

class TestThreadsAPI(unittest.TestCase):
    def setUp(self):
        # Set up test environment variables
        os.environ['THREADS_CLIENT_ID'] = 'test_client_id'
        os.environ['THREADS_CLIENT_SECRET'] = 'test_client_secret'
        os.environ['THREADS_REDIRECT_URI'] = 'https://example.com/callback'
        os.environ['THREADS_ACCESS_TOKEN'] = 'test_access_token'
        os.environ['THREADS_REFRESH_TOKEN'] = 'test_refresh_token'
        os.environ['THREADS_TOKEN_EXPIRY'] = str(9999999999)  # Far future
        
        self.threads_api = ThreadsAPI()
    
    def test_initialization(self):
        """Test that the API client initializes correctly"""
        self.assertEqual(self.threads_api.client_id, 'test_client_id')
        self.assertEqual(self.threads_api.access_token, 'test_access_token')
        self.assertTrue(self.threads_api.is_authenticated)
    
    @patch('requests.post')
    def test_post_content(self, mock_post):
        """Test posting content to Threads"""
        # Mock the API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'id': '123456789'}
        mock_post.return_value = mock_response
        
        # Test posting text content
        result = self.threads_api.post_content("Test post content")
        
        # Verify the result
        self.assertTrue(result['success'])
        self.assertEqual(result['post_id'], '123456789')
        self.assertEqual(result['platform'], 'threads')
        
        # Verify the API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://graph.threads.net/v1/me/posts')
        self.assertEqual(kwargs['data']['message'], 'Test post content')
        self.assertEqual(kwargs['data']['access_token'], 'test_access_token')
    
    @patch('requests.post')
    def test_post_with_media(self, mock_post):
        """Test posting content with media"""
        # Create a temporary test image
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            temp_file.write(b'test image data')
            temp_path = temp_file.name
        
        try:
            # Mock the media upload response
            mock_media_response = MagicMock()
            mock_media_response.status_code = 200
            mock_media_response.json.return_value = {'id': 'media123'}
            
            # Mock the post response
            mock_post_response = MagicMock()
            mock_post_response.status_code = 200
            mock_post_response.json.return_value = {'id': 'post123'}
            
            # Configure the mock to return different responses
            mock_post.side_effect = [mock_media_response, mock_post_response]
            
            # Test posting with media
            result = self.threads_api.post_content("Test with media", [temp_path])
            
            # Verify the result
            self.assertTrue(result['success'])
            self.assertEqual(result['post_id'], 'post123')
            self.assertTrue(result['has_media'])
            
            # Verify the API calls
            self.assertEqual(mock_post.call_count, 2)
            
            # First call should be media upload
            media_args, media_kwargs = mock_post.call_args_list[0]
            self.assertEqual(media_args[0], 'https://graph.threads.net/v1/me/media')
            self.assertTrue('files' in media_kwargs)
            
            # Second call should be post creation
            post_args, post_kwargs = mock_post.call_args_list[1]
            self.assertEqual(post_args[0], 'https://graph.threads.net/v1/me/posts')
            self.assertEqual(post_kwargs['data']['media_id'], 'media123')
            
        finally:
            # Clean up the temporary file
            os.unlink(temp_path)
    
    @patch('requests.post')
    def test_api_error_handling(self, mock_post):
        """Test handling of API errors"""
        # Mock an error response
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = '{"error":{"message":"Invalid parameter","code":100}}'
        mock_post.return_value = mock_response
        
        # Test posting with an error response
        result = self.threads_api.post_content("Test error handling")
        
        # Verify the result
        self.assertFalse(result['success'])
        self.assertTrue('API error: 400' in result['error'])
    
    def tearDown(self):
        # Clean up environment variables
        for key in ['THREADS_CLIENT_ID', 'THREADS_CLIENT_SECRET', 'THREADS_REDIRECT_URI',
                   'THREADS_ACCESS_TOKEN', 'THREADS_REFRESH_TOKEN', 'THREADS_TOKEN_EXPIRY']:
            if key in os.environ:
                del os.environ[key]

if __name__ == '__main__':
    unittest.main() 