from enum import StrEnum


class RuntimeErrorCode(StrEnum):
    """Stable runtime error codes shared across execution stages."""

    CONFIGURATION_ERROR = "configuration_error"
    DOCTOR_FAILED = "doctor_failed"
    AUTHENTICATION_ERROR = "authentication_error"
    REQUEST_SUBMIT_ERROR = "request_submit_error"
    POLL_TIMEOUT = "poll_timeout"
    NETWORK_CONNECT_TIMEOUT = "network_connect_timeout"
    NETWORK_SSL_ERROR = "network_ssl_error"
    PAYLOAD_PARSE_ERROR = "payload_parse_error"
    WORKBOOK_CAPABILITY_ERROR = "workbook_capability_error"
    WORKBOOK_SIZE_GUARDRAIL_TRIGGERED = "workbook_size_guardrail_triggered"
    WORKBOOK_WRITER_ERROR = "workbook_writer_error"
    PUBLISH_AUTH_ERROR = "publish_auth_error"
    PUBLISH_RATE_LIMIT_ERROR = "publish_rate_limit_error"
