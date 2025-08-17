from .health import health_router

health_routers = [
    {
        "router": health_router,
        "prefix": "",
        "tags": ["Health Check"]
    }
]