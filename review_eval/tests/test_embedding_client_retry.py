"""Tests for embedding client retry logic."""

import asyncio
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from review_eval.semantic.embeddings.client import (
    EmbeddingClient,
    RateLimitError,
    ServerError,
    TimeoutError,
    with_retry,
)


class TestRetryDecorator:
    """Tests for the retry decorator."""

    @pytest.mark.asyncio
    async def test_successful_call_no_retry(self):
        """Test that successful calls don't trigger retries."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry_succeeds(self):
        """Test that rate limit errors are retried and eventually succeed."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RateLimitError("Rate limit exceeded")
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_server_error_retry_succeeds(self):
        """Test that server errors are retried and eventually succeed."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ServerError("Internal server error")
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_error_retry_succeeds(self):
        """Test that timeout errors are retried and eventually succeed."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Request timed out")
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_httpx_timeout_retry_succeeds(self):
        """Test that httpx timeout exceptions are retried and eventually succeed."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")
            return "success"

        result = await mock_function()
        assert result == "success"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that max retries are respected and final exception is raised."""
        call_count = 0

        @with_retry(max_retries=2, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Always fails")

        with pytest.raises(RateLimitError, match="Always fails"):
            await mock_function()

        assert call_count == 3  # Initial call + 2 retries

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors are not retried."""
        call_count = 0

        @with_retry(max_retries=3, base_delay=0.01)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")

        with pytest.raises(ValueError, match="This should not be retried"):
            await mock_function()

        assert call_count == 1  # No retries

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        """Test that delays follow exponential backoff pattern."""
        delays = []

        # Mock asyncio.sleep to capture delays
        async def mock_sleep(delay):
            delays.append(delay)

        call_count = 0

        @with_retry(max_retries=3, base_delay=1.0)
        async def mock_function():
            nonlocal call_count
            call_count += 1
            raise RateLimitError("Always fails")

        with patch('asyncio.sleep', side_effect=mock_sleep):
            with pytest.raises(RateLimitError):
                await mock_function()

        # Should have 3 delays (for 3 retries after initial failure)
        assert len(delays) == 3
        # Base delays should be roughly 1, 2, 4 seconds (plus jitter)
        assert 1.0 <= delays[0] <= 2.0  # 1 + jitter
        assert 2.0 <= delays[1] <= 3.0  # 2 + jitter
        assert 4.0 <= delays[2] <= 5.0  # 4 + jitter


class TestEmbeddingClientRetry:
    """Tests for embedding client with retry logic."""

    def setup_method(self):
        """Set up test client."""
        self.client = EmbeddingClient(api_key="test_key", model="test/model")

    @pytest.mark.asyncio
    async def test_successful_embedding_request(self):
        """Test successful embedding request with mock response."""
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.return_value = mock_response
            mock_client_class.return_value = mock_client

            result = await self.client._embed_batch(["test text"])

            assert result == [[0.1, 0.2, 0.3]]
            assert mock_client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_retry_success(self):
        """Test that rate limit errors are retried and eventually succeed."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock()
            if call_count < 3:
                mock_response.status_code = 429
                mock_response.text = "Rate limit exceeded"
            else:
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": [{"embedding": [0.1, 0.2, 0.3]}]
                }
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                result = await self.client._embed_batch(["test text"])

            assert result == [[0.1, 0.2, 0.3]]
            assert call_count == 3  # 2 failures + 1 success

    @pytest.mark.asyncio
    async def test_server_error_retry_success(self):
        """Test that server errors are retried and eventually succeed."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock()
            if call_count < 2:
                mock_response.status_code = 500
                mock_response.text = "Internal server error"
            else:
                mock_response.status_code = 200
                mock_response.json.return_value = {
                    "data": [{"embedding": [0.1, 0.2, 0.3]}]
                }
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                result = await self.client._embed_batch(["test text"])

            assert result == [[0.1, 0.2, 0.3]]
            assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.asyncio
    async def test_timeout_error_retry_success(self):
        """Test that timeout errors are retried and eventually succeed."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise httpx.TimeoutException("Request timed out")

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3]}]
            }
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                result = await self.client._embed_batch(["test text"])

            assert result == [[0.1, 0.2, 0.3]]
            assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test that retries are exhausted and final error is raised."""
        def mock_post(*args, **kwargs):
            mock_response = AsyncMock()
            mock_response.status_code = 429
            mock_response.text = "Rate limit exceeded"
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                with pytest.raises(RateLimitError, match="Rate limit exceeded"):
                    await self.client._embed_batch(["test text"])

    @pytest.mark.asyncio
    async def test_non_retryable_error_no_retry(self):
        """Test that non-retryable errors (400, 401, etc.) are not retried."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            mock_response = AsyncMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with pytest.raises(Exception):  # Should be EmbeddingAPIError
                await self.client._embed_batch(["test text"])

            assert call_count == 1  # No retries for 401

    @pytest.mark.asyncio
    async def test_connection_error_retry_success(self):
        """Test that connection errors are retried and eventually succeed."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise httpx.ConnectError("Connection failed")

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3]}]
            }
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                result = await self.client._embed_batch(["test text"])

            assert result == [[0.1, 0.2, 0.3]]
            assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.asyncio
    async def test_logging_retry_attempts(self, caplog):
        """Test that retry attempts are logged."""
        call_count = 0

        def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count < 3:
                mock_response = AsyncMock()
                mock_response.status_code = 429
                mock_response.text = "Rate limit exceeded"
                return mock_response

            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [{"embedding": [0.1, 0.2, 0.3]}]
            }
            return mock_response

        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.post.side_effect = mock_post
            mock_client_class.return_value = mock_client

            with patch('asyncio.sleep'):  # Speed up test by mocking sleep
                with caplog.at_level('WARNING'):
                    await self.client._embed_batch(["test text"])

            # Check that retry warnings were logged
            warning_logs = [record for record in caplog.records if record.levelname == 'WARNING']
            assert len(warning_logs) == 2  # Two retries
            assert "_embed_batch failed on attempt" in warning_logs[0].message
            assert "Retrying in" in warning_logs[0].message