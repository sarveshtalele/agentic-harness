"""The model list (admin) and the models each person may pick."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.core import auth, models
from backend.maf import llm

router = APIRouter()

class ModelIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    label: str | None = None
    enabled: bool | None = None
    is_default: bool | None = None


@router.get("/api/models")
def list_models():
    return models.list_models()


@router.post("/api/models", status_code=201)
def add_model(body: ModelIn):
    """Added by hand, so the admin means it: it starts enabled. Only a loaded name starts off."""
    try:
        return models.update(body.name, {}) if body.name in {m["name"] for m in models.list_models()} else models.add(body.name, body.label or "", enabled=True)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.patch("/api/models")
def patch_model(body: ModelIn):
    try:
        return models.update(body.name, body.model_dump(exclude={"name"}, exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.delete("/api/models", status_code=204)
def delete_model(name: str):
    try:
        models.remove(name)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return Response(status_code=204)


@router.post("/api/models/load")
async def load_models():
    """Lists the names the proxy offers. They are added switched off: a listed name may not work, so each needs its Test and an explicit switch on."""
    listed = await llm.proxy_models()
    known = {m["name"] for m in models.list_models()}
    for name in listed:
        if name not in known:
            models.add(name)
    return {"listed": len(listed), "added": [n for n in listed if n not in known], "models": models.list_models()}


@router.post("/api/models/tool-check")
async def check_model_tools(body: ModelIn):
    """One real tool-call round trip through the endpoint (`llm.tool_check`). The result is kept on the model row."""
    models.get(body.name)  # 404 for a name that is not in the list
    return await llm.tool_check(body.name)


@router.get("/api/settings/models")
def my_models():
    """Only models this person may use, for the run forms and chat. The default marks what applies when nothing is picked."""
    user = auth.describe(auth.current_user.get())
    checks = models.tool_checks()
    if user["role"] == "admin":
        names = [m["name"] for m in models.list_models() if m["enabled"]]
        return {"models": names, "default": models.system_default(llm.public()["model"]), "tools": {n: checks[n] for n in names if n in checks}}
    allowed = models.allowed(user["id"])
    return {"models": allowed, "default": user["model"] if user["model"] in allowed else "", "tools": {n: checks[n] for n in allowed if n in checks}}
