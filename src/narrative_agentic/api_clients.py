"""
API Clients for OpenAI and Gemini.

Provides unified interface for making API calls to both services.
"""

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Iterator, Generator
from enum import Enum
import urllib.request
import urllib.error


class APIError(Exception):
    """Base exception for API errors."""
    pass


class APIRateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    pass


class APIAuthenticationError(APIError):
    """Raised when API authentication fails."""
    pass


class TaskType(Enum):
    """Types of tasks for API routing."""
    CODING = "coding"           # Code generation, review, debugging
    GENERAL = "general"         # General conversation, questions
    ANALYSIS = "analysis"       # Code analysis, review
    CREATIVE = "creative"       # Creative writing, design ideas
    TECHNICAL = "technical"     # Technical explanations


@dataclass
class APIResponse:
    """Standardized API response."""
    content: str
    model: str
    usage: dict = field(default_factory=dict)
    finish_reason: str = ""
    raw_response: dict = field(default_factory=dict, repr=False)
    
    @property
    def input_tokens(self) -> int:
        return self.usage.get("input_tokens", 0) or self.usage.get("prompt_tokens", 0)
    
    @property
    def output_tokens(self) -> int:
        return self.usage.get("output_tokens", 0) or self.usage.get("completion_tokens", 0)
    
    @property
    def total_tokens(self) -> int:
        return self.usage.get("total_tokens", self.input_tokens + self.output_tokens)


@dataclass
class APIRequest:
    """Standardized API request."""
    messages: list[dict]  # List of {"role": "user|assistant|system", "content": "..."}
    temperature: float = 0.7
    max_tokens: int = 4096
    stream: bool = False
    task_type: TaskType = TaskType.GENERAL


class BaseAPIClient(ABC):
    """Base class for API clients."""
    
    def __init__(self, api_key: str, model: str = ""):
        self.api_key = api_key
        self.model = model
        self._last_error: Optional[str] = None
    
    @abstractmethod
    def complete(self, request: APIRequest) -> APIResponse:
        """Make a completion request."""
        pass
    
    @abstractmethod
    def complete_stream(self, request: APIRequest) -> Generator[str, None, None]:
        """Make a streaming completion request."""
        pass
    
    def is_available(self) -> bool:
        """Check if the API is available (has key)."""
        return bool(self.api_key)
    
    def get_last_error(self) -> Optional[str]:
        return self._last_error


class OpenAIClient(BaseAPIClient):
    """
    OpenAI API client using only standard library.
    
    Supports chat completions API.
    Uses GPT-5.2 Codex Mini.
    """
    
    def __init__(self, api_key: str, model: str = "gpt-4o", base_url: str = "https://api.openai.com/v1"):
        super().__init__(api_key, model)
        self.base_url = base_url.rstrip("/")
    
    def _make_request(self, endpoint: str, data: dict) -> dict:
        """Make an HTTP request to the OpenAI API."""
        url = f"{self.base_url}{endpoint}"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", error_body)
            except:
                error_msg = error_body
            
            if e.code == 401:
                raise APIAuthenticationError(f"OpenAI authentication failed: {error_msg}")
            elif e.code == 429:
                raise APIRateLimitError(f"OpenAI rate limit exceeded: {error_msg}")
            else:
                raise APIError(f"OpenAI API error ({e.code}): {error_msg}")
        except urllib.error.URLError as e:
            raise APIError(f"Network error: {e.reason}")
    
    def complete(self, request: APIRequest) -> APIResponse:
        """Make a chat completion request."""
        if not self.api_key:
            raise APIAuthenticationError("OpenAI API key not configured")
        
        data = {
            "model": self.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        
        try:
            response_data = self._make_request("/chat/completions", data)
            
            choice = response_data["choices"][0]
            message = choice["message"]
            
            return APIResponse(
                content=message.get("content", ""),
                model=response_data.get("model", self.model),
                usage=response_data.get("usage", {}),
                finish_reason=choice.get("finish_reason", ""),
                raw_response=response_data,
            )
        except APIError:
            raise
        except Exception as e:
            self._last_error = str(e)
            raise APIError(f"OpenAI API request failed: {e}")
    
    def complete_stream(self, request: APIRequest) -> Generator[str, None, None]:
        """Make a streaming chat completion request."""
        if not self.api_key:
            raise APIAuthenticationError("OpenAI API key not configured")
        
        data = {
            "model": self.model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }
        
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except (json.JSONDecodeError, KeyError):
                            continue
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise APIError(f"OpenAI streaming error: {error_body}")


class GeminiClient(BaseAPIClient):
    """
    Google Gemini API client using only standard library.
    
    Uses Gemini 3 Flash Preview.
    """
    
    def __init__(self, api_key: str, model: str = "gemini-3-flash-preview"):
        super().__init__(api_key, model)
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"
    
    def _convert_messages(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        Convert OpenAI-style messages to Gemini format.
        
        Returns (system_instruction, contents)
        """
        system_instruction = ""
        contents = []
        
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            
            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}]
                })
            elif role == "assistant":
                contents.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        
        return system_instruction, contents
    
    def _make_request(self, endpoint: str, data: dict) -> dict:
        """Make an HTTP request to the Gemini API."""
        url = f"{self.base_url}{endpoint}?key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        request = urllib.request.Request(
            url,
            data=json.dumps(data).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            try:
                error_data = json.loads(error_body)
                error_msg = error_data.get("error", {}).get("message", error_body)
            except:
                error_msg = error_body
            
            if e.code == 400 and "API key not valid" in error_msg:
                raise APIAuthenticationError(f"Gemini authentication failed: {error_msg}")
            elif e.code == 429:
                raise APIRateLimitError(f"Gemini rate limit exceeded: {error_msg}")
            else:
                raise APIError(f"Gemini API error ({e.code}): {error_msg}")
        except urllib.error.URLError as e:
            raise APIError(f"Network error: {e.reason}")
    
    def complete(self, request: APIRequest) -> APIResponse:
        """Make a content generation request."""
        if not self.api_key:
            raise APIAuthenticationError("Gemini API key not configured")
        
        system_instruction, contents = self._convert_messages(request.messages)
        
        # Build request body
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }
        
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        endpoint = f"/models/{self.model}:generateContent"
        
        try:
            response_data = self._make_request(endpoint, body)
            
            # Extract content from response
            candidates = response_data.get("candidates", [])
            if not candidates:
                raise APIError("No response from Gemini API")
            
            content_parts = candidates[0].get("content", {}).get("parts", [])
            text = "".join(part.get("text", "") for part in content_parts)
            
            # Extract usage info
            usage = response_data.get("usageMetadata", {})
            
            return APIResponse(
                content=text,
                model=self.model,
                usage={
                    "input_tokens": usage.get("promptTokenCount", 0),
                    "output_tokens": usage.get("candidatesTokenCount", 0),
                    "total_tokens": usage.get("totalTokenCount", 0),
                },
                finish_reason=candidates[0].get("finishReason", ""),
                raw_response=response_data,
            )
        except APIError:
            raise
        except Exception as e:
            self._last_error = str(e)
            raise APIError(f"Gemini API request failed: {e}")
    
    def complete_stream(self, request: APIRequest) -> Generator[str, None, None]:
        """Make a streaming content generation request."""
        if not self.api_key:
            raise APIAuthenticationError("Gemini API key not configured")
        
        system_instruction, contents = self._convert_messages(request.messages)
        
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            }
        }
        
        if system_instruction:
            body["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }
        
        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                for line in response:
                    line = line.decode("utf-8").strip()
                    if line.startswith("data: "):
                        data_str = line[6:]
                        try:
                            chunk = json.loads(data_str)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                content_parts = candidates[0].get("content", {}).get("parts", [])
                                for part in content_parts:
                                    text = part.get("text", "")
                                    if text:
                                        yield text
                        except (json.JSONDecodeError, KeyError):
                            continue
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise APIError(f"Gemini streaming error: {error_body}")


class APIRouter:
    """
    Routes requests to the appropriate API based on task type.
    
    - CODING tasks → OpenAI
    - GENERAL tasks → Gemini
    """
    
    def __init__(self, openai_client: Optional[OpenAIClient] = None, 
                 gemini_client: Optional[GeminiClient] = None):
        self.openai = openai_client
        self.gemini = gemini_client
    
    def route(self, task_type: TaskType) -> BaseAPIClient:
        """Determine which API to use for a task type."""
        # Route ALL tasks through OpenAI first (Gemini as fallback only)
        if self.openai and self.openai.is_available():
            return self.openai
        elif self.gemini and self.gemini.is_available():
            return self.gemini
        else:
            raise APIError(f"No API configured for {task_type.value} tasks")
    
    def complete(self, request: APIRequest) -> APIResponse:
        """Complete a request using the appropriate API."""
        client = self.route(request.task_type)
        return client.complete(request)
    
    def complete_stream(self, request: APIRequest) -> Generator[str, None, None]:
        """Stream a completion using the appropriate API."""
        client = self.route(request.task_type)
        return client.complete_stream(request)
    
    def is_configured(self) -> dict:
        """Check which APIs are configured."""
        return {
            "openai": self.openai is not None and self.openai.is_available(),
            "gemini": self.gemini is not None and self.gemini.is_available(),
            "coding_available": self.openai is not None and self.openai.is_available(),
            "general_available": self.gemini is not None and self.gemini.is_available(),
        }


def create_clients_from_config() -> tuple[Optional[OpenAIClient], Optional[GeminiClient]]:
    """Create API clients from saved configuration."""
    from .config import get_api_config
    
    config = get_api_config()
    
    openai_client = None
    gemini_client = None
    
    if config.openai_api_key:
        openai_client = OpenAIClient(
            api_key=config.openai_api_key,
            model=config.openai_coding_model or config.openai_model,
            base_url=config.openai_base_url,
        )
    
    if config.gemini_api_key:
        gemini_client = GeminiClient(
            api_key=config.gemini_api_key,
            model=config.gemini_general_model or config.gemini_model,
        )
    
    return openai_client, gemini_client


def get_router() -> APIRouter:
    """Get an API router with configured clients."""
    openai_client, gemini_client = create_clients_from_config()
    return APIRouter(openai_client, gemini_client)
