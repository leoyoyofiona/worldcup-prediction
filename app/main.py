from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .services import service


app = FastAPI(title="2026 男足世界杯预测模型", version="0.1.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> Response:
    return Response(status_code=204)


@app.get("/api/status")
def get_status():
    return service.status()


@app.post("/api/update")
def update_data():
    return service.start_update()


@app.post("/api/recalculate")
def recalculate_model():
    return service.start_recalculate()


@app.get("/api/matches")
def get_matches():
    return service.matches()


@app.get("/api/tournament")
def get_tournament():
    return service.tournament()


@app.get("/api/betting/daily")
def get_betting_daily():
    return service.betting_daily()


@app.get("/api/matches/{match_id}")
def get_match(match_id: str):
    try:
        return service.match_detail(match_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="比赛不存在")


@app.get("/api/sources")
def get_sources():
    return service.sources()
