from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.config import settings
from app.database import init_db, close_db
from app.middleware import RequestLoggingMiddleware
from app.routes import api_router
from app.logging_config import logger  # Import logger

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Initialize Sentry if DSN is provided
if settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        integrations=[
            FastApiIntegration(
                transaction_style="url",
                middleware_spans=True,
                send_default_pii=True,
            )
        ],
        traces_sample_rate=1.0,
    )

# Initialize OpenTelemetry if enabled
if settings.ENABLE_OPENTELEMETRY:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

    tracer_provider = TracerProvider()
    otlp_exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    trace.set_tracer_provider(tracer_provider)

def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """
    application = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        docs_url=f"{settings.API_V1_STR}/docs",
        redoc_url=f"{settings.API_V1_STR}/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
    )

    # Add CORS middleware
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add GZip compression middleware
    application.add_middleware(GZipMiddleware, minimum_size=1000)

    # Add custom request logging middleware
    application.add_middleware(RequestLoggingMiddleware)

    # Add rate limiting
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Include API router
    application.include_router(api_router, prefix=settings.API_V1_STR)

    # Add startup and shutdown events
    @application.on_event("startup")
    async def startup_event():
        logger.info("Initializing database...")
        await init_db()
        logger.info("Database initialized successfully")

    @application.on_event("shutdown")
    async def shutdown_event():
        logger.info("Closing database connections...")
        await close_db()
        logger.info("Database connections closed")

    return application


app = create_application()

# Health check endpoint
@app.get("/health")
# @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def health_check():
    """
    Health check endpoint to verify the application is running.
    """
    logger.debug("Health check requested")
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "environment": settings.SENTRY_ENVIRONMENT,
    }
