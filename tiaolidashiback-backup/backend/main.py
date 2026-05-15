from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Union
import os

from graph import run_graph

app = FastAPI(title="挑礼大师 API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

class Message(BaseModel):
    role: str
    content: Union[str, dict]  # 支持字符串或字典（用于_state消息）

class ChatRequest(BaseModel):
    message: str
    history: List[Message] = []
    selected_index: Optional[int] = None  # 用户选中的商品索引
    recommendations: List[dict] = []  # 当前推荐商品列表

class ChatResponse(BaseModel):
    reply: str
    recommendations: list = []
    stage: Optional[str] = None
    asking_slot: Optional[str] = None  # 当前正在询问的槽位
    slot_options: list = []  # 当前槽位的建议选项
    slots: Optional[dict] = None  # 包含 recipient, occasion, budget, gift_type, excluded_gifts 等槽位信息

@app.get("/")
async def root():
    landing_path = os.path.join(frontend_path, "landing.html")
    if os.path.exists(landing_path):
        return FileResponse(landing_path)
    return {"message": "挑礼大师后端运行中！前端文件未找到，请检查 frontend/landing.html"}

@app.get("/chat")
async def chat_page():
    index_path = os.path.join(frontend_path, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "聊天页面未找到，请检查 frontend/index.html"}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    history = [{"role": m.role, "content": m.content} for m in request.history]
    result = run_graph(
        user_message=request.message,
        history=history,
        selected_index=request.selected_index,
        recommendations=request.recommendations
    )
    return ChatResponse(
        reply=result["reply"],
        recommendations=result["recommendations"],
        stage=result["stage"],
        asking_slot=result.get("asking_slot"),
        slot_options=result.get("slot_options", []),
        slots=result["slots"]
    )

@app.get("/health")
async def health():
    return {"status": "ok", "service": "挑礼大师"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7890)