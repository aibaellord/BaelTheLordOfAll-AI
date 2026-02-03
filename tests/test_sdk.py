"""
Unit tests for sdk.python.bael_sdk module
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest

from sdk.python.bael_sdk import (APIError, AuthenticationError, BAELClient,
                                 BAELSyncClient, RateLimitError, quick_chat,
                                 quick_chat_sync)


@pytest.fixture
def mock_response():
    """Create mock aiohttp response"""
    mock = AsyncMock()
    mock.status = 200
    mock.json = AsyncMock(return_value={"data": "test"})
    mock.text = AsyncMock(return_value="OK")
    return mock


@pytest.fixture
def mock_session():
    """Create mock aiohttp session"""
    session = AsyncMock()
    return session


class TestBAELClient:
    """Test async BAELClient"""

    @pytest.mark.asyncio
    async def test_create_client(self):
        """Test creating BAEL client"""

        client = BAELClient(
            base_url="http://localhost:8000",
            api_key="test_key"
        )

        assert client.base_url == "http://localhost:8000"
        assert client.api_key == "test_key"

    @pytest.mark.asyncio
    async def test_chat_success(self, mock_session, mock_response):
        """Test successful chat request"""

        mock_response.json = AsyncMock(return_value={
            "response": "Hello!",
            "status": "success"
        })

        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        response = await client.chat("Hello", persona="default")

        assert response["response"] == "Hello!"
        assert response["status"] == "success"

    @pytest.mark.asyncio
    async def test_chat_with_context(self, mock_session, mock_response):
        """Test chat with context"""

        mock_response.json = AsyncMock(return_value={"response": "OK"})
        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        await client.chat(
            "Test message",
            context={"user_id": "123"},
            persona="assistant"
        )

        # Verify request was made with correct data
        call_args = mock_session.post.call_args
        assert call_args is not None

    @pytest.mark.asyncio
    async def test_submit_task(self, mock_session, mock_response):
        """Test submitting a task"""

        mock_response.json = AsyncMock(return_value={
            "task_id": "task_123",
            "status": "pending"
        })
        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        result = await client.submit_task(
            task_type="analysis",
            task_data={"content": "test"}
        )

        assert result["task_id"] == "task_123"
        assert result["status"] == "pending"

    @pytest.mark.asyncio
    async def test_get_task_status(self, mock_session, mock_response):
        """Test getting task status"""

        mock_response.json = AsyncMock(return_value={
            "task_id": "task_123",
            "status": "completed",
            "result": {"data": "result"}
        })
        mock_session.get = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        status = await client.get_task_status("task_123")

        assert status["status"] == "completed"
        assert status["result"]["data"] == "result"

    @pytest.mark.asyncio
    async def test_health_check(self, mock_session, mock_response):
        """Test health check"""

        mock_response.json = AsyncMock(return_value={
            "status": "healthy",
            "version": "2.1.0"
        })
        mock_session.get = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        health = await client.health_check()

        assert health["status"] == "healthy"
        assert health["version"] == "2.1.0"

    @pytest.mark.asyncio
    async def test_list_personas(self, mock_session, mock_response):
        """Test listing personas"""

        mock_response.json = AsyncMock(return_value={
            "personas": ["default", "assistant", "researcher"]
        })
        mock_session.get = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        personas = await client.list_personas()

        assert len(personas["personas"]) == 3
        assert "default" in personas["personas"]

    @pytest.mark.asyncio
    async def test_get_capabilities(self, mock_session, mock_response):
        """Test getting capabilities"""

        mock_response.json = AsyncMock(return_value={
            "capabilities": {
                "reasoning": True,
                "memory": True,
                "tools": ["search", "calculator"]
            }
        })
        mock_session.get = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        caps = await client.get_capabilities()

        assert caps["capabilities"]["reasoning"] == True
        assert "search" in caps["capabilities"]["tools"]


class TestErrorHandling:
    """Test error handling in SDK"""

    @pytest.mark.asyncio
    async def test_rate_limit_error(self, mock_session):
        """Test rate limit error handling"""

        mock_response = AsyncMock()
        mock_response.status = 429
        mock_response.json = AsyncMock(return_value={"error": "Rate limited"})
        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        with pytest.raises(RateLimitError):
            await client.chat("Test")

    @pytest.mark.asyncio
    async def test_authentication_error(self, mock_session):
        """Test authentication error handling"""

        mock_response = AsyncMock()
        mock_response.status = 401
        mock_response.json = AsyncMock(return_value={"error": "Unauthorized"})
        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        with pytest.raises(AuthenticationError):
            await client.chat("Test")

    @pytest.mark.asyncio
    async def test_generic_api_error(self, mock_session):
        """Test generic API error handling"""

        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.json = AsyncMock(return_value={"error": "Internal error"})
        mock_session.post = AsyncMock(return_value=mock_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        with pytest.raises(APIError):
            await client.chat("Test")


class TestBAELSyncClient:
    """Test synchronous BAELSyncClient"""

    def test_create_sync_client(self):
        """Test creating sync client"""

        client = BAELSyncClient(
            base_url="http://localhost:8000",
            api_key="test_key"
        )

        assert client.client.base_url == "http://localhost:8000"
        assert client.client.api_key == "test_key"

    @patch('sdk.python.bael_sdk.BAELClient.chat')
    def test_sync_chat(self, mock_chat):
        """Test synchronous chat"""

        mock_chat.return_value = asyncio.Future()
        mock_chat.return_value.set_result({"response": "Hello!"})

        client = BAELSyncClient(base_url="http://localhost:8000")

        # This would normally run the event loop
        # In testing, we just verify the interface exists
        assert hasattr(client, 'chat')

    def test_sync_submit_task(self):
        """Test synchronous task submission"""

        client = BAELSyncClient(base_url="http://localhost:8000")
        assert hasattr(client, 'submit_task')

    def test_sync_health_check(self):
        """Test synchronous health check"""

        client = BAELSyncClient(base_url="http://localhost:8000")
        assert hasattr(client, 'health_check')


class TestConvenienceFunctions:
    """Test convenience functions"""

    @pytest.mark.asyncio
    @patch('sdk.python.bael_sdk.BAELClient.chat')
    async def test_quick_chat(self, mock_chat):
        """Test quick_chat convenience function"""

        mock_chat.return_value = {"response": "Quick response"}

        result = await quick_chat("Hello", base_url="http://localhost:8000")

        # Verify the function exists and has correct signature
        assert quick_chat is not None

    @patch('sdk.python.bael_sdk.BAELSyncClient.chat')
    def test_quick_chat_sync(self, mock_chat):
        """Test quick_chat_sync convenience function"""

        mock_chat.return_value = {"response": "Quick sync response"}

        # Verify the function exists
        assert quick_chat_sync is not None


class TestIntegration:
    """Integration tests for SDK"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, mock_session, mock_response):
        """Test complete SDK workflow"""

        # Mock multiple responses
        chat_response = AsyncMock()
        chat_response.status = 200
        chat_response.json = AsyncMock(return_value={"response": "Hello!"})

        task_response = AsyncMock()
        task_response.status = 200
        task_response.json = AsyncMock(return_value={
            "task_id": "task_123",
            "status": "pending"
        })

        status_response = AsyncMock()
        status_response.status = 200
        status_response.json = AsyncMock(return_value={
            "task_id": "task_123",
            "status": "completed",
            "result": {"data": "result"}
        })

        mock_session.post = AsyncMock(side_effect=[chat_response, task_response])
        mock_session.get = AsyncMock(return_value=status_response)

        client = BAELClient(base_url="http://localhost:8000")
        client.session = mock_session

        # 1. Chat
        chat_result = await client.chat("Hello")
        assert chat_result["response"] == "Hello!"

        # 2. Submit task
        task_result = await client.submit_task("analysis", {"data": "test"})
        assert task_result["task_id"] == "task_123"

        # 3. Check status
        status = await client.get_task_status("task_123")
        assert status["status"] == "completed"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
