import json
from langgraph.graph import StateGraph, END
from state import GiftState
from agents import intent_agent, slot_agent, recommend_agent, reason_agent, validate_agent, chat_agent, product_inquiry_agent

def should_recommend(state: GiftState) -> str:
    """决定从 slot 节点走向哪个分支"""
    stage = state.get("stage")
    user_intent = state.get("user_intent")

    # 如果用户对产品感兴趣，优先处理产品咨询
    if user_intent == "product_inquiry":
        return "product_inquiry"

    if stage == "chatting":
        return "chat"
    elif stage == "recommending":
        return "recommend"
    return "reply"

def build_graph():
    workflow = StateGraph(GiftState)

    workflow.add_node("intent", intent_agent)
    workflow.add_node("slot", slot_agent)
    workflow.add_node("chat", chat_agent)
    workflow.add_node("product_inquiry", product_inquiry_agent)
    workflow.add_node("recommend", recommend_agent)
    workflow.add_node("validate", validate_agent)
    workflow.add_node("reason", reason_agent)

    workflow.set_entry_point("intent")

    workflow.add_edge("intent", "slot")

    # slot 节点后的条件分支：聊天、产品咨询、推荐、或追问
    workflow.add_conditional_edges(
        "slot",
        should_recommend,
        {
            "chat": "chat",
            "product_inquiry": "product_inquiry",
            "recommend": "recommend",
            "reply": END
        }
    )

    # 聊天和产品咨询节点直接结束
    workflow.add_edge("chat", END)
    workflow.add_edge("product_inquiry", END)

    # 推荐流程
    workflow.add_edge("recommend", "validate")
    workflow.add_edge("validate", "reason")
    workflow.add_edge("reason", END)

    return workflow.compile()

gift_graph = build_graph()

def run_graph(user_message: str, history: list, selected_index: int = None, recommendations: list = None) -> dict:
    messages = history + [{"role": "user", "content": user_message}]

    initial_state: GiftState = {
        "messages": messages,
        "recipient": None,
        "occasion": None,
        "budget": None,
        "gift_type": None,
        "timeline": None,
        "category": None,
        "preference": None,
        "user_type": None,
        "user_intent": "gift",  # 默认意图为礼物推荐
        "stage": "slot_filling",
        "recommendations": recommendations,  # 传入的推荐列表
        "reply": None,
        "turn_count": len([m for m in messages if m["role"] == "user"]),
        "cache_key": None,
        "excluded_gifts": [],
        "budget_adjusted": None,
        "asking_slot": None,
        "slot_options": [],
        "selected_product": None,
        "selected_index": selected_index,  # 用户选中的商品索引
    }

    # 从历史中恢复状态
    for msg in history:
        if msg.get("role") == "_state":
            saved = msg.get("content", {})
            # 确保saved是字典类型
            if isinstance(saved, str):
                try:
                    saved = json.loads(saved)
                except:
                    saved = {}
            for field in ["recipient", "occasion", "budget", "gift_type", "timeline", "category", "preference", "user_type", "user_intent", "excluded_gifts", "budget_adjusted", "asking_slot", "slot_options", "selected_product", "selected_index"]:
                if field in saved and saved[field] is not None:
                    initial_state[field] = saved[field]
            break

    result = gift_graph.invoke(initial_state)

    return {
        "reply": result.get("reply") or "让我想想...",
        "recommendations": result.get("recommendations") or [],
        "stage": result.get("stage"),
        "user_intent": result.get("user_intent", "gift"),
        "asking_slot": result.get("asking_slot"),
        "slot_options": result.get("slot_options", []),
        "slots": {
            "recipient": result.get("recipient"),
            "occasion": result.get("occasion"),
            "budget": result.get("budget"),
            "gift_type": result.get("gift_type"),
            "timeline": result.get("timeline"),
            "category": result.get("category"),
            "preference": result.get("preference"),
            "excluded_gifts": result.get("excluded_gifts", []),
            "budget_adjusted": result.get("budget_adjusted"),
        }
    }
