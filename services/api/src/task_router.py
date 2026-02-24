"""
Task Router - CRUD de tareas programadas y run-now.
Montado en /api/v1/tasks
"""

from typing import Any, Optional, Dict
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from src.db.repositories.user_tasks import UserTaskRepository
from src.db.repositories.user_task_results import UserTaskResultRepository
from src.auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["Tasks"], dependencies=[Depends(get_current_user)])


class TaskCreate(BaseModel):
    user_id: str
    type: str
    name: str
    cron_expression: str
    is_active: bool = True
    config: Optional[Dict[str, Any]] = None
    llm_provider_id: Optional[int] = None
    llm_model: Optional[str] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = None
    cron_expression: Optional[str] = None
    is_active: Optional[bool] = None
    config: Optional[Dict[str, Any]] = None


@router.get("")
async def list_tasks(user_id: str):
    tasks = await UserTaskRepository.get_all(user_id)
    return {"items": tasks}


@router.post("")
async def create_task(body: TaskCreate):
    task = await UserTaskRepository.create(body.model_dump())
    return task


@router.get("/{task_id}")
async def get_task(task_id: int):
    task = await UserTaskRepository.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}")
async def update_task(task_id: int, body: TaskUpdate):
    task = await UserTaskRepository.update(task_id, body.model_dump(exclude_none=True))
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.delete("/{task_id}")
async def delete_task(task_id: int):
    ok = await UserTaskRepository.delete(task_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"deleted": True}


@router.post("/{task_id}/run-now")
async def run_task_now(task_id: int):
    task = await UserTaskRepository.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await UserTaskRepository.request_run_now(task_id)
    return {"accepted": True, "task_id": task_id}


@router.get("/{task_id}/results")
async def get_task_results(task_id: int, limit: int = 20):
    task = await UserTaskRepository.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    results = await UserTaskResultRepository.get_by_task(task_id, limit=limit)
    return {"items": results}
