"""
Framework-wide constants.

This module contains constants used throughout the Flaxon framework.
"""

from __future__ import annotations

# ============================================================
# HTTP Constants
# ============================================================

DEFAULT_HTTP_PORT = 8000
DEFAULT_HTTP_HOST = "127.0.0.1"

# Default maximum body size (10 MB)
DEFAULT_MAX_BODY_SIZE = 10 * 1024 * 1024

# Default timeout values (seconds)
DEFAULT_READ_TIMEOUT = 30
DEFAULT_WRITE_TIMEOUT = 30
DEFAULT_CONNECT_TIMEOUT = 5

# ============================================================
# Framework Constants
# ============================================================

# Default application name
DEFAULT_APP_NAME = "flaxon-app"

# Environment names
ENV_DEVELOPMENT = "development"
ENV_TESTING = "testing"
ENV_STAGING = "staging"
ENV_PRODUCTION = "production"

# Valid environments
VALID_ENVIRONMENTS = {
    ENV_DEVELOPMENT,
    ENV_TESTING,
    ENV_STAGING,
    ENV_PRODUCTION,
}

# ============================================================
# Security Constants
# ============================================================

# Minimum secret key length
MIN_SECRET_KEY_LENGTH = 32

# Default rate limit settings
DEFAULT_RATE_LIMIT_REQUESTS = 60
DEFAULT_RATE_LIMIT_WINDOW = 60  # seconds

# ============================================================
# WebSocket Constants
# ============================================================

# Default WebSocket close codes
WS_CLOSE_NORMAL = 1000
WS_CLOSE_GOING_AWAY = 1001
WS_CLOSE_PROTOCOL_ERROR = 1002
WS_CLOSE_UNSUPPORTED_DATA = 1003
WS_CLOSE_NO_STATUS = 1005
WS_CLOSE_ABNORMAL = 1006
WS_CLOSE_INVALID_PAYLOAD = 1007
WS_CLOSE_POLICY_VIOLATION = 1008
WS_CLOSE_MESSAGE_TOO_BIG = 1009
WS_CLOSE_MANDATORY_EXTENSION = 1010
WS_CLOSE_INTERNAL_ERROR = 1011
WS_CLOSE_SERVICE_RESTART = 1012
WS_CLOSE_TRY_AGAIN_LATER = 1013
WS_CLOSE_BAD_GATEWAY = 1014
WS_CLOSE_TLS_HANDSHAKE = 1015

# ============================================================
# Error Codes
# ============================================================

# HTTP error code prefix
HTTP_ERROR_PREFIX = "FX-HTTP-"

# Validation error code
VALIDATION_ERROR_CODE = "FX-VAL-001"

# Rate limit error code
RATE_LIMIT_ERROR_CODE = "FX-RATE-001"

# Server error code
SERVER_ERROR_CODE = "FX-SRV-500"

# Debug error code
DEBUG_ERROR_CODE = "FX-DEV-500"

# ============================================================
# Header Names
# ============================================================

# Request ID header
REQUEST_ID_HEADER = "x-request-id"

# Correlation ID header (for distributed tracing)
CORRELATION_ID_HEADER = "x-correlation-id"

# ============================================================
# Middleware Order
# ============================================================

# Recommended middleware order (first = outermost)
MIDDLEWARE_ORDER = [
    "ProxyHeadersMiddleware",  # Trust proxy headers first
    "TrustedHostMiddleware",  # Validate host before anything else
    "RequestIDMiddleware",  # Add request ID early for logging
    "CORSMiddleware",  # CORS before authentication
    "BodyLimitMiddleware",  # Limit body size early
    "TimeoutMiddleware",  # Timeout before processing
    "RateLimitMiddleware",  # Rate limit after validation
    "AuthenticationMiddleware",  # Authenticate before authorization
    "AuthorizationMiddleware",  # Authorize before business logic
    "LoggingMiddleware",  # Log after authentication
    "RecoveryMiddleware",  # Catch exceptions last (outermost)
]

# ============================================================
# MIME Types
# ============================================================

MIME_JSON = "application/json"
MIME_HTML = "text/html"
MIME_TEXT = "text/plain"
MIME_XML = "application/xml"
MIME_FORM = "application/x-www-form-urlencoded"
MIME_MULTIPART = "multipart/form-data"
MIME_OCTET_STREAM = "application/octet-stream"
MIME_PDF = "application/pdf"
MIME_JPEG = "image/jpeg"
MIME_PNG = "image/png"
MIME_GIF = "image/gif"
MIME_SVG = "image/svg+xml"
MIME_WEBP = "image/webp"
MIME_CSS = "text/css"
MIME_JS = "application/javascript"
MIME_CSV = "text/csv"

# ============================================================
# Default Templates
# ============================================================

DEFAULT_TEMPLATE_DIR = "templates"
DEFAULT_TEMPLATE_EXTENSION = ".html"

# ============================================================
# File Upload Constants
# ============================================================

DEFAULT_MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
DEFAULT_UPLOAD_DIR = "uploads"
