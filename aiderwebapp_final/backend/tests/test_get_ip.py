import sys
import unittest
from unittest.mock import patch, MagicMock

# Mock out missing dependencies for the environment so main.py can be imported
sys.modules['pydantic'] = MagicMock()
sys.modules['fastapi'] = MagicMock()
sys.modules['fastapi.middleware.cors'] = MagicMock()
sys.modules['fastapi.staticfiles'] = MagicMock()
sys.modules['uvicorn'] = MagicMock()

import os
# Add backend directory to sys.path so main can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import main

class TestGetIp(unittest.TestCase):
    @patch('main.socket.socket')
    def test_get_ip_success(self, mock_socket_class):
        # Arrange
        mock_socket_instance = MagicMock()
        mock_socket_class.return_value = mock_socket_instance
        # getsockname returns a tuple (ip, port)
        mock_socket_instance.getsockname.return_value = ("192.168.1.100", 54321)

        # Act
        result = main.get_ip()

        # Assert
        self.assertEqual(result, "192.168.1.100")
        mock_socket_class.assert_called_once_with(main.socket.AF_INET, main.socket.SOCK_DGRAM)
        mock_socket_instance.connect.assert_called_once_with(("8.8.8.8", 80))
        mock_socket_instance.getsockname.assert_called_once()
        mock_socket_instance.close.assert_called_once()

    @patch('main.socket.socket')
    def test_get_ip_exception(self, mock_socket_class):
        # Arrange
        # Simulate an exception when trying to create a socket or connect
        mock_socket_class.side_effect = Exception("Network error")

        # Act
        result = main.get_ip()

        # Assert
        self.assertEqual(result, "localhost")
        mock_socket_class.assert_called_once_with(main.socket.AF_INET, main.socket.SOCK_DGRAM)

if __name__ == '__main__':
    unittest.main()
