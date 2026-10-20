import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.simulation_runner import build_and_solve, list_problems

router = APIRouter(prefix="/api/simulacion", tags=["simulacion"])

_executor = ThreadPoolExecutor(max_workers=1)


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.get("/stream")
async def stream_simulacion(db: Session = Depends(get_db)):
    problems = list_problems(db)
    if not problems:
        async def empty():
            yield _sse("error", {"message": "No hay demanda cargada."})
            yield _sse("done", {"ok": 0, "failed": 0, "total": 0})

        return StreamingResponse(empty(), media_type="text/event-stream")

    total = len(problems)
    keys = list(problems)

    async def generate():
        ok_count = 0
        failed = 0
        loop = asyncio.get_event_loop()
        for index, key in enumerate(keys, start=1):
            yield _sse(
                "progress",
                {
                    "index": index,
                    "total": total,
                    "seccional": key.seccional_nombre,
                    "semana": key.semana,
                    "servicio": key.servicio_nombre,
                },
            )

            def run_one():
                session = SessionLocal()
                try:
                    return build_and_solve(session, key)
                finally:
                    session.close()

            try:
                result = await loop.run_in_executor(_executor, run_one)
                ok_count += 1
                yield _sse("result", result)
            except Exception as exc:
                failed += 1
                yield _sse(
                    "error",
                    {
                        "seccional": key.seccional_nombre,
                        "semana": key.semana,
                        "servicio": key.servicio_nombre,
                        "message": str(exc),
                    },
                )

        yield _sse(
            "done",
            {"ok": ok_count, "failed": failed, "total": total},
        )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
