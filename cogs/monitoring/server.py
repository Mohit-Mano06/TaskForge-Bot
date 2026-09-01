import os

from aiohttp import web


class MetricsServer:
    def __init__(self):
        self.host = os.getenv("METRICS_HOST", "127.0.0.1")
        self.port = int(os.getenv("METRICS_PORT", "9100"))
        self.runner = None

    async def start(self):
        if self.runner is not None:
            return
        app = web.Application()
        app.router.add_get("/healthz", self.healthz)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        await web.TCPSite(self.runner, self.host, self.port).start()

    async def stop(self):
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None

    async def healthz(self, request):
        return web.Response(text="ok\n")