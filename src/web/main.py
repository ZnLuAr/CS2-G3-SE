"""FastAPI 工厂、ASGI 生命周期与本机 Web API 启动入口。"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app import App
from src.config import AppSettings, load_config
from src.web.errors import register_error_handlers
from src.web.routers.auth import router as auth_router
from src.web.security import TokenManager


def create_app(settings: AppSettings) -> FastAPI:
    """创建 ASGI 应用；数据库和 Worker 在 lifespan 中启动与关闭。"""

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        runtime = App(settings)
        application.state.application = runtime
        application.state.token_manager = TokenManager.from_environment(settings.web)
        try:
            runtime.start(with_worker=True)
        except BaseException:
            try:
                runtime.close()
            except BaseException:
                pass
            raise
        try:
            yield
        finally:
            runtime.close()

    application = FastAPI(
        title="健身房管理系统 API",
        version="1.0.0",
        lifespan=lifespan,
    )
    if settings.web.allowed_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.web.allowed_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )
    application.include_router(auth_router)
    register_error_handlers(application)
    return application


def main() -> None:
    """从 config.json 读取监听配置并运行 Uvicorn。"""
    import uvicorn

    settings = load_config()
    uvicorn.run(
        create_app(settings),
        host=settings.web.host,
        port=settings.web.port,
    )


if __name__ == "__main__":
    main()
