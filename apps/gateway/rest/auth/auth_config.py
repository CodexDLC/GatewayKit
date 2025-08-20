from apps.gateway.rest.auth.auth_routes import auth_routes_router

auth_routers = [
    {
        "router": auth_routes_router,
        "tags": ["Authentication"],
    },
]
