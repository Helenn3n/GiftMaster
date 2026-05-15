from typing import TypedDict, List, Optional

class GiftState(TypedDict):
    messages: List[dict]
    recipient: Optional[str]      # 送礼对象
    occasion: Optional[str]       # 送礼场合
    budget: Optional[str]         # 预算
    gift_type: Optional[str]      # 礼物类型（实用型、纪念型、体验型、装饰型）
    timeline: Optional[str]       # 时间要求
    category: Optional[str]       # 品类偏好
    preference: Optional[str]     # 风格偏好
    user_type: Optional[str]      # 用户画像
    user_intent: str              # "gift" 或 "chat" 或 "product_inquiry"
    stage: str
    recommendations: Optional[List[dict]]
    reply: Optional[str]
    turn_count: int
    cache_key: Optional[str]
    excluded_gifts: List[str]     # 用户不喜欢的商品名称列表
    budget_adjusted: Optional[bool]  # 预算是否已调整
    asking_slot: Optional[str]    # 当前正在询问的槽位
    slot_options: List[dict]      # 当前槽位的建议选项
    selected_product: Optional[dict]  # 用户选中的商品
    selected_index: Optional[int]     # 用户选中的商品索引
