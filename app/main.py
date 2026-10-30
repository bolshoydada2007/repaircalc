# Точка входа приложения.
# Шаг 8: подключён роутер подбора по фото.

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.calc_router import router as calc_router
from app.api.photo_router import router as photo_router
from app.api.smart_router import router as smart_router
from app.api.plan_router import router as plan_router



app = FastAPI(
    title="RepairCalc",
    description="Микросервис умных калькуляторов ремонта (каталог maxidom.ru)",
    version="0.4.0",
)

app.include_router(calc_router)
app.include_router(photo_router)
app.include_router(smart_router)
app.include_router(plan_router)



@app.get("/health")
def health():
    """Healthcheck: сервис запущен и отвечает."""
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="static", html=True), name="static")
