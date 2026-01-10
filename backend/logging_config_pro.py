"""Configuración de logging estructurado profesional"""
import structlog
import logging.config
import os

# Configurar structlog con filtros PII
def filter_pii(logger, method_name, event_dict):
    """Filtrar información sensible de logs"""
    sensitive_keys = ['password', 'token', 'secret', 'email', 'phone', 'ssn']
    
    for key in sensitive_keys:
        if key in event_dict:
            if os.environ.get('DEBUG', 'False').lower() == 'true':
                event_dict[key] = f"[DEBUG:{event_dict[key][:3]}...]"
            else:
                event_dict[key] = "[REDACTED]"
    
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO"),
        filter_pii,
        structlog.processors.JSONRenderer() if os.environ.get('DEBUG', 'False').lower() != 'true' 
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    logger_factory=structlog.WriteLoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configuración Django logging por dominio
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'structured': {
            'format': '%(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'structured',
        },
        'file_app': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/app.log',
            'maxBytes': 1024*1024*10,  # 10MB
            'backupCount': 5,
            'formatter': 'structured',
        },
        'file_security': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/security.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 10,  # Más retención para seguridad
            'formatter': 'structured',
        },
        'file_payroll': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/payroll.log',
            'maxBytes': 1024*1024*10,
            'backupCount': 12,  # Retención anual para auditoría
            'formatter': 'structured',
        },
    },
    'loggers': {
        # CRÍTICO: Payroll (auditoría legal)
        'apps.payroll_api': {
            'handlers': ['console', 'file_payroll'],
            'level': 'INFO',
            'propagate': False,
        },
        # CRÍTICO: POS (transacciones financieras)
        'apps.pos_api': {
            'handlers': ['console', 'file_app'],
            'level': 'INFO',
            'propagate': False,
        },
        # CRÍTICO: Auth (seguridad)
        'apps.auth_api': {
            'handlers': ['console', 'file_security'],
            'level': 'INFO',
            'propagate': False,
        },
        # CRÍTICO: Tenants (multi-tenancy)
        'apps.tenants_api': {
            'handlers': ['console', 'file_security'],
            'level': 'INFO',
            'propagate': False,
        },
        # Subscriptions (billing)
        'apps.subscriptions_api': {
            'handlers': ['console', 'file_app'],
            'level': 'INFO',
            'propagate': False,
        },
        # Django internals
        'django.request': {
            'handlers': ['console', 'file_security'],
            'level': 'WARNING',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['console', 'file_security'],
            'level': 'WARNING',
            'propagate': False,
        },
        # Root logger
        '': {
            'handlers': ['console'],
            'level': 'DEBUG' if os.environ.get('DEBUG', 'False').lower() == 'true' else 'INFO',
        },
    },
}