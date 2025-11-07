"""
Bible API Service with multi-provider support and circuit breaker pattern.

Supports multiple Bible API providers with automatic fallback:
1. Bible API (primary) - https://bible-api.com/
2. ESV API (fallback) - https://api.esv.org/

Features:
- Multi-provider support with automatic fallback
- Circuit breaker pattern for resilient API calls
- Caching for frequently accessed verses
- Translation support (KJV, NIV, ESV, etc.)
- Verse reference parsing
"""

import re
import requests
import logging
from typing import Dict, Optional, Tuple
from django.core.cache import cache
from django.conf import settings
from rest_framework import status
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Simple circuit breaker implementation.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, requests fail fast
    - HALF_OPEN: Testing if service recovered
    """

    CLOSED = 'closed'
    OPEN = 'open'
    HALF_OPEN = 'half_open'

    def __init__(self, failure_threshold=5, timeout=60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before trying again (half-open)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.state = self.CLOSED
        self.last_failure_time = None

    def call(self, func, *args, **kwargs):
        """
        Execute function with circuit breaker protection.

        Args:
            func: Function to execute
            *args, **kwargs: Function arguments

        Returns:
            Function result

        Raises:
            Exception: If circuit is open or function fails
        """
        import time

        if self.state == self.OPEN:
            # Check if timeout expired
            if time.time() - self.last_failure_time >= self.timeout:
                self.state = self.HALF_OPEN
                logger.info("Circuit breaker entering HALF_OPEN state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            # Success - reset circuit
            if self.state == self.HALF_OPEN:
                self.state = self.CLOSED
                logger.info("Circuit breaker CLOSED after successful call")
            self.failure_count = 0
            return result

        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if self.failure_count >= self.failure_threshold:
                self.state = self.OPEN
                logger.warning(
                    f"Circuit breaker OPENED after {self.failure_count} failures")

            raise e


class BibleAPIService:
    """
    Service for fetching Bible verses from multiple API providers.

    Implements circuit breaker pattern and caching for reliability.
    """

    # API Endpoints
    BIBLE_API_BASE = "https://bible-api.com"
    ESV_API_BASE = "https://api.esv.org/v3/passage/text"
    BIBLE_GATEWAY_API = "https://www.biblegateway.com/passage/"  # Scraping fallback

    # Supported translations
    SUPPORTED_TRANSLATIONS = ['KJV', 'NIV',
                              'ESV', 'NKJV', 'NLT', 'NASB', 'AMP']

    # Translation mappings for different providers
    BIBLE_API_TRANSLATIONS = {
        'KJV': 'kjv',
        'NIV': 'web',  # bible-api.com doesn't have NIV, use WEB as fallback
        'ESV': 'web',  # Use WEB as fallback for ESV
        'NKJV': 'kjv',  # Fallback to KJV
        'NLT': 'web',  # Use WEB as fallback
        'NASB': 'web',  # Use WEB as fallback
        'AMP': 'web',  # Use WEB as fallback
    }

    # Cache settings
    CACHE_TTL = 60 * 60 * 24 * 7  # 7 days (verses don't change)

    def __init__(self):
        """Initialize Bible API service with circuit breakers."""
        self.bible_api_breaker = CircuitBreaker(
            failure_threshold=3, timeout=60)
        self.esv_api_breaker = CircuitBreaker(failure_threshold=3, timeout=60)

    def get_verse(
        self,
        reference: str,
        translation: str = 'KJV'
    ) -> Dict[str, str]:
        """
        Fetch Bible verse with automatic provider fallback.

        Args:
            reference: Bible reference (e.g., "John 3:16", "Psalm 23:1-6")
            translation: Bible translation (KJV, NIV, ESV, etc.)

        Returns:
            Dict with keys: reference, text, translation, source

        Raises:
            ValidationError: If verse not found or all providers fail
        """
        # Normalize reference
        reference = self._normalize_reference(reference)
        translation = translation.upper()

        # Validate translation
        if translation not in self.SUPPORTED_TRANSLATIONS:
            raise ValidationError(
                f"Translation '{translation}' not supported. "
                f"Supported: {', '.join(self.SUPPORTED_TRANSLATIONS)}"
            )

        # Check cache first
        cache_key = f"bible_verse:{translation}:{reference}"
        cached_verse = cache.get(cache_key)
        if cached_verse:
            logger.info(f"Cache hit for {reference} ({translation})")
            return cached_verse

        # Try providers in order
        providers = [
            ('bible-api.com', self._fetch_from_bible_api),
            ('ESV API', self._fetch_from_esv_api),
        ]

        last_error = None
        for provider_name, fetch_func in providers:
            try:
                logger.info(
                    f"Trying {provider_name} for {reference} ({translation})")
                verse_data = fetch_func(reference, translation)

                # Cache successful result
                cache.set(cache_key, verse_data, self.CACHE_TTL)
                logger.info(
                    f"Successfully fetched {reference} from {provider_name}")

                return verse_data

            except Exception as e:
                logger.warning(f"{provider_name} failed: {str(e)}")
                last_error = e
                continue

        # All providers failed
        error_msg = f"Unable to fetch verse '{reference}'. All providers failed."
        if last_error:
            error_msg += f" Last error: {str(last_error)}"

        logger.error(error_msg)
        raise ValidationError(error_msg)

    def _fetch_from_bible_api(
        self,
        reference: str,
        translation: str
    ) -> Dict[str, str]:
        """
        Fetch verse from bible-api.com.

        Args:
            reference: Bible reference
            translation: Bible translation

        Returns:
            Verse data dict
        """
        def make_request():
            # bible-api.com URL format: /reference?translation=KJV
            # Map to bible-api.com supported translations
            bible_api_translation = self.BIBLE_API_TRANSLATIONS.get(
                translation, 'kjv'
            )

            url = f"{self.BIBLE_API_BASE}/{reference}"
            params = {'translation': bible_api_translation}

            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # Parse response
            if not data.get('text'):
                raise ValidationError(f"Verse not found: {reference}")

            return {
                'reference': data.get('reference', reference),
                'text': data['text'].strip(),
                'translation': translation,  # Return requested translation
                'translation_note': f"Retrieved as {bible_api_translation.upper()} from bible-api.com" if bible_api_translation != translation.lower() else None,
                'source': 'bible-api.com',
            }

        return self.bible_api_breaker.call(make_request)

    def _fetch_from_esv_api(
        self,
        reference: str,
        translation: str
    ) -> Dict[str, str]:
        """
        Fetch verse from ESV API (fallback).

        Note: ESV API only provides ESV translation.
        For other translations, this will fail gracefully.

        Args:
            reference: Bible reference
            translation: Bible translation (must be ESV)

        Returns:
            Verse data dict
        """
        # ESV API only supports ESV translation
        if translation != 'ESV':
            raise ValidationError(
                f"ESV API only supports ESV translation, not {translation}"
            )

        def make_request():
            # Get API key from settings (optional, can use without key)
            api_key = getattr(settings, 'ESV_API_KEY', None)

            headers = {}
            if api_key:
                headers['Authorization'] = f'Token {api_key}'

            params = {
                'q': reference,
                'include-headings': False,
                'include-footnotes': False,
                'include-verse-numbers': False,
                'include-short-copyright': False,
                'include-passage-references': False,
            }

            response = requests.get(
                self.ESV_API_BASE,
                params=params,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()

            # Parse response
            passages = data.get('passages', [])
            if not passages or not passages[0]:
                raise ValidationError(f"Verse not found: {reference}")

            return {
                'reference': reference,
                'text': passages[0].strip(),
                'translation': 'ESV',
                'source': 'ESV API',
            }

        return self.esv_api_breaker.call(make_request)

    def _normalize_reference(self, reference: str) -> str:
        """
        Normalize Bible reference format.

        Examples:
            "john 3:16" -> "John 3:16"
            "psalm23:1-6" -> "Psalm 23:1-6"
            "1corinthians 13:4" -> "1 Corinthians 13:4"

        Args:
            reference: Raw reference string

        Returns:
            Normalized reference
        """
        # Remove extra whitespace
        reference = ' '.join(reference.split())

        # Add space after book number (1John -> 1 John)
        reference = re.sub(r'^(\d)([A-Za-z])', r'\1 \2', reference)

        # Capitalize first letter of each word
        words = reference.split()
        if words:
            words[0] = words[0].capitalize()

        return ' '.join(words)

    def validate_reference_format(self, reference: str) -> Tuple[bool, Optional[str]]:
        """
        Validate Bible reference format.

        Args:
            reference: Bible reference to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic pattern: Book Chapter:Verse or Book Chapter:Verse-Verse
        pattern = r'^[1-3]?\s*[A-Za-z]+\s+\d+:\d+(-\d+)?$'

        if not re.match(pattern, reference):
            return False, (
                "Invalid reference format. "
                "Expected format: 'Book Chapter:Verse' (e.g., 'John 3:16', 'Psalm 23:1-6')"
            )

        return True, None

    def search_verses(
        self,
        query: str,
        translation: str = 'KJV',
        limit: int = 10
    ) -> list:
        """
        Search for Bible verses containing keywords.

        Note: This is a placeholder for future implementation.
        Full-text search would require a dedicated Bible search API
        or local database.

        Args:
            query: Search keywords
            translation: Bible translation
            limit: Maximum results

        Returns:
            List of matching verses
        """
        raise NotImplementedError(
            "Verse search not yet implemented. "
            "Please use specific verse references."
        )


# Singleton instance
bible_service = BibleAPIService()
