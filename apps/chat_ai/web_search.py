import json
import time
from urllib.parse import urlparse

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import F

from chat_ai.executor.sanitizer import sanitize_text, summarize
from chat_ai.models import AgentRun, ApiCallAudit


class WebSearchError(Exception):
    pass


class WebSearchConfigurationError(WebSearchError):
    pass


class WebSearchClient:
    providers = {'tavily', 'searxng'}

    def __init__(self):
        self.provider = str(
            getattr(settings, 'CHAT_AI_WEB_SEARCH_PROVIDER', 'tavily') or 'tavily'
        ).lower()
        self.base_url = str(
            getattr(settings, 'CHAT_AI_WEB_SEARCH_BASE_URL', '') or ''
        ).rstrip('/')
        self.api_key = str(getattr(settings, 'CHAT_AI_WEB_SEARCH_API_KEY', '') or '')
        self.proxy = str(getattr(settings, 'CHAT_AI_WEB_SEARCH_PROXY', '') or '')
        self.timeout = max(1, int(getattr(settings, 'CHAT_AI_WEB_SEARCH_TIMEOUT', 10)))
        self.max_results = min(
            10, max(1, int(getattr(settings, 'CHAT_AI_WEB_SEARCH_MAX_RESULTS', 5)))
        )
        self.max_response_bytes = max(
            1024,
            int(getattr(settings, 'CHAT_AI_WEB_SEARCH_MAX_RESPONSE_BYTES', 1024 * 1024)),
        )

    def _endpoint(self):
        if self.provider not in self.providers:
            raise WebSearchConfigurationError('Unsupported web search provider.')
        if not self.base_url:
            raise WebSearchConfigurationError('Web search base URL is not configured.')
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise WebSearchConfigurationError('Web search base URL is invalid.')
        if parsed.username or parsed.password:
            raise WebSearchConfigurationError(
                'Credentials must not be embedded in the web search base URL.'
            )
        if self.provider == 'tavily' and not self.api_key:
            raise WebSearchConfigurationError('Web search API key is not configured.')
        if parsed.path.rstrip('/').endswith('/search'):
            return self.base_url
        return f'{self.base_url}/search'

    def _client_kwargs(self):
        kwargs = {
            'timeout': self.timeout,
            'follow_redirects': False,
            'trust_env': False,
        }
        if self.proxy:
            kwargs['proxy'] = self.proxy
        return kwargs

    async def _request(self, client, endpoint, query):
        if self.provider == 'tavily':
            request = client.build_request(
                'POST',
                endpoint,
                headers={'Authorization': f'Bearer {self.api_key}'},
                json={
                    'query': query,
                    'topic': 'general',
                    'search_depth': 'basic',
                    'max_results': self.max_results,
                    'include_answer': False,
                    'include_images': False,
                    'include_raw_content': False,
                },
            )
        else:
            request = client.build_request(
                'GET',
                endpoint,
                params={
                    'q': query,
                    'format': 'json',
                    'categories': 'general',
                    'safesearch': 1,
                },
            )
        return await client.send(request, stream=True)

    @staticmethod
    def _public_results(results):
        return [
            {'title': item['title'], 'url': item['url']}
            for item in results
        ]

    def _normalize_results(self, payload):
        raw_results = payload.get('results') if isinstance(payload, dict) else []
        if not isinstance(raw_results, list):
            raise WebSearchError('Web search provider returned an invalid response.')
        results = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            url = sanitize_text(item.get('url') or '')[:2048].strip()
            parsed = urlparse(url)
            if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
                continue
            title = sanitize_text(item.get('title') or url)[:300].strip()
            content = sanitize_text(
                item.get('content') or item.get('snippet') or ''
            )[:1200].strip()
            result = {'title': title, 'url': url, 'content': content}
            score = item.get('score')
            if isinstance(score, (int, float)):
                result['score'] = score
            results.append(result)
            if len(results) >= self.max_results:
                break
        return results

    async def _audit(
        self, *, agent_run, endpoint, query, results=None, status_code=0,
        duration_ms=0, error='',
    ):
        await sync_to_async(ApiCallAudit.objects.create, thread_sensitive=True)(
            agent_run=agent_run,
            conversation_id=agent_run.conversation_id,
            message_id=agent_run.assistant_message_id,
            user_id=agent_run.user_id,
            org_id=str(agent_run.org_id),
            operation_id=f'web_search:{self.provider}',
            method='POST' if self.provider == 'tavily' else 'GET',
            path=endpoint,
            request_summary=summarize({'query': query}),
            response_summary=summarize({
                'results': self._public_results(results or []),
            }),
            status_code=status_code,
            risk_level='read',
            duration_ms=duration_ms,
            error=sanitize_text(error)[:1024],
        )
        await sync_to_async(
            AgentRun.objects.filter(pk=agent_run.pk).update,
            thread_sensitive=True,
        )(api_call_count=F('api_call_count') + 1)

    async def search(self, query, agent_run):
        query = sanitize_text(query)[:512].strip()
        if not query:
            raise WebSearchError('A web search query is required.')
        endpoint = self._endpoint()
        started = time.monotonic()
        status_code = 0
        try:
            async with httpx.AsyncClient(**self._client_kwargs()) as client:
                response = await self._request(client, endpoint, query)
                try:
                    status_code = response.status_code
                    chunks = bytearray()
                    async for chunk in response.aiter_bytes():
                        chunks.extend(chunk)
                        if len(chunks) > self.max_response_bytes:
                            raise WebSearchError(
                                'Web search response exceeded the configured size limit.'
                            )
                    raw = bytes(chunks)
                finally:
                    await response.aclose()
            if status_code in {401, 403}:
                raise WebSearchError('Web search credentials were rejected.')
            if status_code == 429:
                raise WebSearchError('Web search rate limit was exceeded.')
            if status_code < 200 or status_code >= 300:
                raise WebSearchError('Web search provider is unavailable.')
            try:
                payload = json.loads(raw.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise WebSearchError(
                    'Web search provider returned an invalid response.'
                ) from exc
            results = self._normalize_results(payload)
            duration_ms = int((time.monotonic() - started) * 1000)
            await self._audit(
                agent_run=agent_run,
                endpoint=endpoint,
                query=query,
                results=results,
                status_code=status_code,
                duration_ms=duration_ms,
            )
            return {
                'query': query,
                'provider': self.provider,
                'results': results,
                'untrusted_external_content': True,
            }
        except httpx.TimeoutException as exc:
            error = WebSearchError('Web search request timed out.')
            await self._audit(
                agent_run=agent_run,
                endpoint=endpoint,
                query=query,
                status_code=status_code,
                duration_ms=int((time.monotonic() - started) * 1000),
                error=error.__class__.__name__,
            )
            raise error from exc
        except (httpx.HTTPError, WebSearchError) as exc:
            error = exc if isinstance(exc, WebSearchError) else WebSearchError(
                'Web search provider is unavailable.'
            )
            await self._audit(
                agent_run=agent_run,
                endpoint=endpoint,
                query=query,
                status_code=status_code,
                duration_ms=int((time.monotonic() - started) * 1000),
                error=error.__class__.__name__,
            )
            raise error from exc
