import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import settings
from app.database import Base, engine, SessionLocal
from app.models import ErrorLog, PageVisit
from app.services.energy_engine import active_plants, generate_reading
from app.services.alert_service import evaluate_reading
from app.routers import (
    energy, billing, alerts, auth, admin, plants, reports, maintenance, logs, backup, public,
    plant_profile, settings as settings_router,
)

Base.metadata.create_all(bind=engine)

app = FastAPI(title=settings.APP_NAME)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

_UNTRACKED_PREFIXES = ("/api", "/static", "/openapi.json", "/docs", "/redoc")


@app.middleware("http")
async def track_page_visits(request: Request, call_next):
    if request.method == "GET" and not request.url.path.startswith(_UNTRACKED_PREFIXES):
        db = SessionLocal()
        try:
            db.add(PageVisit(path=request.url.path))
            db.commit()
        finally:
            db.close()
    return await call_next(request)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    db = SessionLocal()
    try:
        db.add(ErrorLog(path=request.url.path, message=f"{exc}\n{traceback.format_exc()[-800:]}"))
        db.commit()
    finally:
        db.close()
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(public.router)
app.include_router(plant_profile.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(plants.router)
app.include_router(reports.router)
app.include_router(maintenance.router)
app.include_router(logs.router)
app.include_router(backup.router)
app.include_router(settings_router.router)
app.include_router(energy.router)
app.include_router(billing.router)
app.include_router(alerts.router)

scheduler = BackgroundScheduler()


def _tick():
    db = SessionLocal()
    try:
        for plant in active_plants(db):
            reading = generate_reading(db, plant)
            evaluate_reading(db, reading)
    finally:
        db.close()


@app.on_event("startup")
def startup():
    _tick()  # seed one reading immediately so the dashboard isn't empty on first load
    scheduler.add_job(_tick, "interval", seconds=settings.SIM_INTERVAL_SECONDS, id="sensor_tick")
    scheduler.start()


@app.on_event("shutdown")
def shutdown():
    scheduler.shutdown()


@app.get("/")
def landing(request: Request):
    return templates.TemplateResponse(request, "landing.html", {"app_name": settings.APP_NAME})


@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"app_name": settings.APP_NAME})


@app.get("/admin")
def admin_page(request: Request):
    return templates.TemplateResponse(request, "admin.html", {"app_name": settings.APP_NAME})


@app.get("/profile")
def profile_page(request: Request):
    return templates.TemplateResponse(request, "profile.html", {"app_name": settings.APP_NAME})


@app.get("/plant-details")
def plant_details_page(request: Request):
    return templates.TemplateResponse(request, "plant_details.html", {"app_name": settings.APP_NAME})


@app.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"app_name": settings.APP_NAME})


@app.get("/signup")
def signup_page(request: Request):
    return templates.TemplateResponse(request, "signup.html", {"app_name": settings.APP_NAME})


_PUBLIC_PAGES = {
    "/company": "company.html",
    "/solar-for-home": "solar-for-home.html",
    "/solar-for-business": "solar-for-business.html",
    "/portfolio": "portfolio.html",
    "/investors": "investors.html",
    "/contact": "contact.html",
}

for _path, _template in _PUBLIC_PAGES.items():
    def _make_view(template_name: str):
        def _view(request: Request):
            return templates.TemplateResponse(request, template_name, {"app_name": settings.APP_NAME})
        return _view

    app.get(_path)(_make_view(_template))
