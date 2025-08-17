
from game_server.app_gateway.rest_routers.auth.auth_routes import auth_routes_router


auth_routers = [
    {
        "router": auth_routes_router,
        "prefix": "/auth",
        "tags": ["Authentication"],
    },
    
]