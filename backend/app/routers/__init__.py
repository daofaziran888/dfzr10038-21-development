"""业务路由汇总：所有模块共用一套资源路由，由领域服务完成分派。"""
from __future__ import annotations

from app.routers import rejection, resource

# 逐行拒绝归因是固定前缀路由，需放在通用 /api/{module} 动态路由之前注册。
ROUTERS = [rejection, resource]
