import json
import os
import re
from openai import OpenAI
from state import GiftState

# Load config
def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[load_config] 加载失败: {e}")
        return {"deepseek_api_key": "your-api-key-here"}

_config = load_config()

client = OpenAI(
    api_key=_config.get("deepseek_api_key", "your-api-key-here"),
    base_url="https://api.deepseek.com"
)

# Load gifts database
_GIFTS_DB = None

def load_gifts_db():
    global _GIFTS_DB
    if _GIFTS_DB is None:
        gifts_path = os.path.join(os.path.dirname(__file__), "gifts.json")
        try:
            with open(gifts_path, 'r', encoding='utf-8') as f:
                _GIFTS_DB = json.load(f)
        except Exception as e:
            print(f"[load_gifts_db] 加载失败: {e}")
            _GIFTS_DB = []
    return _GIFTS_DB

def parse_budget(budget_str):
    """解析预算字符串，返回(最小值, 最大值)"""
    if not budget_str:
        return (0, float('inf'))

    # 提取数字
    numbers = re.findall(r'\d+', budget_str.replace(',', ''))
    if not numbers:
        return (0, float('inf'))

    numbers = [int(n) for n in numbers]

    # 处理范围，如 "300-500"
    if '-' in budget_str or '到' in budget_str or '~' in budget_str:
        if len(numbers) >= 2:
            return (min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))

    # 处理 "左右"、"大概" 等
    if '左右' in budget_str or '大概' in budget_str or '左右' in budget_str:
        base = numbers[0]
        return (int(base * 0.8), int(base * 1.2))

    # 处理 "以内"、"以下"
    if '以内' in budget_str or '以下' in budget_str or '内' in budget_str:
        return (0, numbers[0])

    # 处理 "以上"
    if '以上' in budget_str:
        return (numbers[0], float('inf'))

    # 默认返回单个数字，允许 ±20% 浮动
    base = numbers[0]
    return (int(base * 0.8), int(base * 1.2))

def match_gifts(recipient, occasion, budget, category=None, preference=None, top_k=4):
    """从gifts.json中匹配符合条件的礼物"""
    gifts = load_gifts_db()
    
    budget_min, budget_max = parse_budget(budget)

    matched = []
    for gift in gifts:
        score = 0

        # 预算匹配 (权重最高)
        price = gift.get('价格', 0)
        if budget_min <= price <= budget_max:
            score += 10
        elif price <= budget_max * 1.2:  # 允许20%上浮
            score += 5

        # 对象匹配
        gift_obj = gift.get('对象', '')
        if recipient and recipient in gift_obj:
            score += 3

        # 场合匹配
        gift_occ = gift.get('场合', '')
        if occasion and occasion in gift_occ:
            score += 3

        # 品类匹配
        gift_cat = gift.get('品类', '')
        if category and category in gift_cat:
            score += 2

        # 有分数才加入候选
        if score > 0:
            matched.append((score, gift))

    # 按分数降序，同分随机打乱
    matched.sort(key=lambda x: x[0], reverse=True)

    # 返回前top_k个
    return [gift for _, gift in matched[:top_k]]

def format_gift_recommendation(gift):
    """将gifts.json中的商品格式化为推荐格式"""
    return {
        "name": f"{gift['品牌']} {gift['名称']}",
        "price": f"¥{gift['价格']}",
        "reason": f"适合{gift['场合']}送给{gift['对象']}，品质优良",
        "tags": [gift['品类'], gift['场合']],
        "emoji": get_emoji_for_category(gift['品类'])
    }

def get_emoji_for_category(category):
    """根据品类返回对应的emoji"""
    emoji_map = {
        "手机": "📱",
        "耳机": "🎧",
        "护肤品": "🧴",
        "运动鞋": "👟",
        "家电": "🏠",
        "玩具": "🧸",
        "珠宝": "💎",
        "箱包": "👜",
        "食品": "🍫",
        "手表": "⌚",
        "服饰": "👔",
        "数码": "📷",
        "健康": "💊",
        "酒水": "🍷",
        "文创": "📚",
        "厨具": "🍳",
        "家具": "🛋️",
        "美妆": "💄",
        "旅游": "✈️",
        "知识": "📖",
        "娱乐": "🎬"
    }
    return emoji_map.get(category, "🎁")

def chat(prompt: str, system: str = "", model: str = "deepseek-chat") -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()

def adjust_budget_based_on_feedback(state: GiftState, user_msg: str) -> str:
    """根据用户反馈调整预算"""
    current_budget = state.get("budget", "")
    if not current_budget:
        return current_budget

    # 提取当前预算数字
    import re
    numbers = re.findall(r'\d+', current_budget.replace(',', ''))
    if not numbers:
        return current_budget

    current_value = int(numbers[0])

    # 检测价格反馈意图
    lower_patterns = ['低一点', '便宜', '太贵', '高了', '便宜点', '再低', '预算低', '价格低']
    higher_patterns = ['高一点', '贵一点', '高端', '更好', '再贵', '预算高', '价格高', '上档次']

    is_lower = any(p in user_msg for p in lower_patterns)
    is_higher = any(p in user_msg for p in higher_patterns)

    if is_lower:
        # 降低预算约30-40%
        new_value = int(current_value * 0.65)
        if new_value < 50:
            new_value = 50
        print(f"[budget_adjust] 预算下调: {current_value} -> {new_value}")
        return f"{new_value}元左右"
    elif is_higher:
        # 提高预算约50-80%
        new_value = int(current_value * 1.6)
        print(f"[budget_adjust] 预算上调: {current_value} -> {new_value}")
        return f"{new_value}元左右"

    return current_budget

def detect_product_interest(state: GiftState, user_msg: str) -> dict:
    """检测用户是否对某个推荐商品感兴趣，返回商品索引和意图类型"""
    current_recs = state.get("recommendations", [])
    if not current_recs:
        return {"interested": False}

    # 检测关键词模式
    interest_patterns = [
        r'第([一二三四1234])个',  # 第1个, 第一个
        r'([一二三四1234])号',     # 1号, 一号
        r'第([一二三四1234])款',   # 第1款
    ]

    import re
    selected_index = -1

    # 尝试匹配数字位置
    for pattern in interest_patterns:
        match = re.search(pattern, user_msg)
        if match:
            num_str = match.group(1)
            # 转换中文数字
            cn_to_num = {'一': 1, '二': 2, '三': 3, '四': 4, '1': 1, '2': 2, '3': 3, '4': 4}
            selected_index = cn_to_num.get(num_str, int(num_str) if num_str.isdigit() else 1) - 1
            break

    # 如果没有匹配到数字，检查是否有直接提到商品名称
    if selected_index < 0:
        for i, rec in enumerate(current_recs):
            rec_name = rec.get("name", "")
            # 提取商品名称的关键部分（去掉品牌）
            name_parts = rec_name.split()
            for part in name_parts:
                if len(part) > 2 and part in user_msg:
                    selected_index = i
                    break
            if selected_index >= 0:
                break

    # 检测用户意图：想要更多信息 vs 想要购买
    if selected_index >= 0 and selected_index < len(current_recs):
        is_more_info = any(p in user_msg for p in ['不错', '喜欢', '详细', '更多', '介绍', '了解', '怎么样', '看看'])
        is_buy = any(p in user_msg for p in ['买', '下单', '购买', '要这个', '就要', '确定'])

        if is_more_info or is_buy:
            return {
                "interested": True,
                "index": selected_index,
                "product": current_recs[selected_index],
                "intent": "buy" if is_buy else "more_info"
            }

    return {"interested": False}

def intent_agent(state: GiftState) -> GiftState:
    last_user_msg = ""
    for msg in reversed(state["messages"]):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    # 如果前端传入了selected_index，直接识别为product_inquiry意图
    if state.get("selected_index") is not None and state.get("recommendations"):
        state["user_intent"] = "product_inquiry"
        print(f"[intent_agent] 用户点击了第{state['selected_index'] + 1}个商品卡片")
        return state

    system = """你是挑礼大师的意图识别专家。
你的任务是：
1. 判断用户意图类型：
   - "gift": 用户想要挑选礼物（有明确的送礼需求或询问礼物建议）
   - "chat": 用户进行日常闲聊、提问、打招呼等非礼物相关的对话
   - "product_inquiry": 用户对已推荐的某个商品感兴趣，想要了解更多信息

2. 如果是礼物意图，判断用户类型：exploratory（意图模糊，需启发引导）或 targeted（意图明确，需高效筛选）

3. 如果是礼物意图，从用户输入中提取以下槽位（没有则填null）：
   - recipient: 送礼对象（如：女朋友、妈妈、同事、朋友等）
   - occasion: 送礼场合（如：生日、情人节、结婚、毕业、新年等）
   - budget: 预算（如：500元、1000左右、3000以内等）
   - gift_type: 礼物类型（实用型/纪念型/体验型/装饰型/美食型/数码型等）
   - timeline: 时间要求（如：急用、下周、下个月等）
   - category: 品类偏好（如：化妆品、数码、书籍、首饰等）
   - preference: 风格/偏好（如：实用、浪漫、高端、创意等）
   - price_feedback: 价格反馈（lower-想要更便宜, higher-想要更贵, null-无反馈）

4. 如果用户说"第X个不错"、"喜欢第X个"、"告诉我更多关于第X个"等，识别为 product_inquiry 意图

请严格输出JSON格式，不要有其他内容：
{
  "intent": "gift" 或 "chat" 或 "product_inquiry",
  "user_type": "exploratory" 或 "targeted" 或 null,
  "recipient": "...",
  "occasion": "...",
  "budget": "...",
  "gift_type": "...",
  "timeline": "...",
  "category": "...",
  "preference": "...",
  "price_feedback": "lower" 或 "higher" 或 null
}"""

    history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"][-6:]])
    prompt = f"对话历史：\n{history}\n\n最新用户输入：{last_user_msg}"

    try:
        result = chat(prompt, system=system, model="deepseek-chat")
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        data = json.loads(result)

        # 存储意图类型 (使用 user_intent 避免与 langgraph 保留字冲突)
        state["user_intent"] = data.get("intent", "gift")

        # 检测用户是否对某个商品感兴趣（使用规则匹配作为补充）
        product_interest = detect_product_interest(state, last_user_msg)
        if product_interest.get("interested"):
            state["user_intent"] = "product_inquiry"
            state["selected_product"] = product_interest.get("product")
            state["selected_index"] = product_interest.get("index")
            print(f"[intent_agent] 用户对第{product_interest.get('index') + 1}个商品感兴趣")

        # 只有礼物意图才提取槽位
        if state["user_intent"] == "gift":
            for field in ["recipient", "occasion", "budget", "gift_type", "timeline", "category", "preference"]:
                val = data.get(field)
                if val and val != "null":
                    state[field] = val

            if data.get("user_type"):
                state["user_type"] = data.get("user_type")

            # 处理价格反馈
            price_feedback = data.get("price_feedback")
            if price_feedback or any(p in last_user_msg for p in ['低一点', '便宜', '太贵', '高了', '高一点', '贵一点', '高端', '更好']):
                new_budget = adjust_budget_based_on_feedback(state, last_user_msg)
                if new_budget != state.get("budget"):
                    state["budget"] = new_budget
                    # 记录预算调整，用于清除缓存
                    state["budget_adjusted"] = True
                    print(f"[intent_agent] 预算已调整: {new_budget}")

    except Exception as e:
        print(f"[intent_agent] 解析失败: {e}")
        state["user_intent"] = "gift"  # 默认按礼物意图处理

    return state

# 各槽位的建议选项
SLOT_OPTIONS = {
    "recipient": [
        {"text": "👩 女朋友/妻子", "value": "女朋友", "tags": ["romantic", "adult", "female"]},
        {"text": "👨 男朋友/丈夫", "value": "男朋友", "tags": ["romantic", "adult", "male"]},
        {"text": "👩‍👧 妈妈", "value": "妈妈", "tags": ["family", "adult", "female"]},
        {"text": "👨‍👦 爸爸", "value": "爸爸", "tags": ["family", "adult", "male"]},
        {"text": "👶 孩子", "value": "孩子", "tags": ["family", "child"]},
        {"text": "👫 朋友", "value": "朋友", "tags": ["social", "adult"]},
        {"text": "👔 同事/领导", "value": "同事", "tags": ["business", "adult"]},
    ],
    "occasion": [
        {"text": "🎂 生日", "value": "生日", "tags": ["universal"], "forbidden": []},
        {"text": "💝 情人节", "value": "情人节", "tags": ["romantic"], "forbidden": ["爸爸", "妈妈", "孩子", "同事"]},
        {"text": "🎄 圣诞节", "value": "圣诞", "tags": ["universal"], "forbidden": []},
        {"text": "🧧 春节", "value": "春节", "tags": ["family", "universal"], "forbidden": []},
        {"text": "💍 结婚/纪念日", "value": "结婚纪念日", "tags": ["romantic"], "forbidden": ["爸爸", "妈妈", "孩子", "同事", "朋友"]},
        {"text": "🎓 毕业", "value": "毕业", "tags": ["social", "milestone"], "forbidden": ["同事", "爸爸", "妈妈"]},
        {"text": "💼 入职/升职", "value": "入职", "tags": ["business"], "forbidden": ["孩子"]},
        {"text": "👩 母亲节", "value": "母亲节", "tags": ["family"], "forbidden": ["爸爸", "男朋友", "孩子", "同事", "朋友"]},
        {"text": "👨 父亲节", "value": "父亲节", "tags": ["family"], "forbidden": ["妈妈", "女朋友", "孩子", "同事", "朋友"]},
    ],
    "budget": [
        {"text": "💰 200元以内", "value": "200元以内"},
        {"text": "💰 500元左右", "value": "500元左右"},
        {"text": "💰 1000元左右", "value": "1000元左右"},
        {"text": "💰 2000元左右", "value": "2000元左右"},
        {"text": "💰 5000元左右", "value": "5000元左右"},
    ],
    "gift_type": [
        {"text": "🛍️ 实用型", "value": "实用型", "desc": "日常可用的好物"},
        {"text": "💎 纪念型", "value": "纪念型", "desc": "可长期保存的珍藏"},
        {"text": "🎫 体验型", "value": "体验型", "desc": "特别的体验经历"},
        {"text": "🎨 装饰型", "value": "装饰型", "desc": "美化生活的艺术品"},
    ]
}

def get_filtered_options(slot_key: str, state: GiftState) -> list:
    """根据已收集的信息过滤选项"""
    options = SLOT_OPTIONS.get(slot_key, [])
    if not options:
        return []

    recipient = state.get("recipient", "")
    occasion = state.get("occasion", "")

    filtered = []
    for opt in options:
        should_skip = False

        # 检查场合是否适合当前送礼对象
        if slot_key == "occasion" and recipient:
            forbidden = opt.get("forbidden", [])
            if recipient in forbidden:
                should_skip = True

        # 检查送礼对象是否适合当前场合
        if slot_key == "recipient" and occasion and not should_skip:
            # 如果已选场合，过滤掉不适合该场合的对象
            for occ_opt in SLOT_OPTIONS.get("occasion", []):
                if occ_opt["value"] == occasion:
                    forbidden = occ_opt.get("forbidden", [])
                    if opt["value"] in forbidden:
                        should_skip = True
                    break

        if not should_skip:
            filtered.append(opt)

    # 调试输出
    if recipient or occasion:
        print(f"[get_filtered_options] slot={slot_key}, recipient={recipient}, occasion={occasion}, "
              f"total={len(options)}, filtered={len(filtered)}")

    return filtered

def slot_agent(state: GiftState) -> GiftState:
    """槽位填充智能体 - 确保收集完整信息后才推荐"""
    # 如果是闲聊意图，直接进入聊天模式
    if state.get("user_intent") == "chat":
        state["stage"] = "chatting"
        return state

    # 定义所有必需的槽位
    required_slots = {
        "recipient": "送礼对象（如：女朋友、妈妈、同事）",
        "occasion": "送礼场合（如：生日、节日、纪念日）",
        "budget": "预算范围（如：500元、1000左右）",
        "gift_type": "礼物类型（实用型、纪念型、体验型、装饰型）"
    }

    # 检查缺失的槽位
    missing = []
    for key, desc in required_slots.items():
        if not state.get(key):
            missing.append({"key": key, "desc": desc})

    if missing:
        # 构建已知信息摘要
        known_items = []
        if state.get("recipient"): known_items.append(f"送给{state['recipient']}")
        if state.get("occasion"): known_items.append(f"{state['occasion']}")
        if state.get("budget"): known_items.append(f"预算{state['budget']}")
        if state.get("gift_type"): known_items.append(f"想要{state['gift_type']}")

        known_str = "、".join(known_items) if known_items else "还没有了解到具体信息"

        # 获取第一个缺失的关键信息
        first_missing = missing[0]
        missing_key = first_missing["key"]
        missing_desc = first_missing["desc"]

        # 获取该槽位的建议选项（根据上下文过滤）
        options = get_filtered_options(missing_key, state)
        options_text = "\n".join([f"  {i+1}. {opt['text']}" for i, opt in enumerate(options[:5])])

        system = """你是挑礼大师，一个温暖有趣的礼物推荐助手。

你的任务是根据已收集的信息，自然友好地引导用户提供缺失的关键信息。

重要原则：
1. 必须先收集以下4个关键信息才能推荐：送礼对象、送礼场合、预算、礼物类型
2. 不要机械罗列问题，要像朋友聊天一样自然
3. 先简单总结已了解的信息，然后顺势询问缺失的信息
4. 提供几个常见选项供用户选择，同时告诉用户也可以自行输入
5. 回复控制在2-3句话内，温暖亲切

礼物类型说明：
- 实用型：日常使用频率高的物品（如：家电、数码、护肤品）
- 纪念型：有纪念意义可长期保存（如：首饰、手表、定制礼品）
- 体验型：提供体验而非实物（如：旅游、课程、演出门票）
- 装饰型：美化生活空间的物品（如：摆件、艺术品、鲜花）"""

        prompt = f"""已收集信息：{known_str}

还需要了解：{missing_desc}

你可以这样回复用户：
1. 先简单总结已知信息
2. 自然地问出缺失的信息
3. 提供几个常见选项（用emoji让选项更生动）
4. 最后加上"你也可以告诉我其他选项"

常见选项：
{options_text}

请生成自然的引导话术："""

        reply = chat(prompt, system=system)
        state["reply"] = reply
        state["stage"] = "slot_filling"
        # 保存当前询问的槽位和选项，供前端使用
        state["asking_slot"] = missing_key
        state["slot_options"] = options
    else:
        # 所有信息已收集完整，进入推荐阶段
        state["stage"] = "recommending"
        state["asking_slot"] = None
        state["slot_options"] = []

    return state

def chat_agent(state: GiftState) -> GiftState:
    """通用聊天智能体 - 处理非礼物相关的日常对话"""
    history = "\n".join([f"{m['role']}: {m['content']}" for m in state["messages"][-10:]])

    system = """你是挑礼大师，一个温暖、有趣、知识渊博的AI助手。
你不仅可以帮用户挑选礼物，还可以和用户进行自然的日常聊天。

在聊天时：
1. 保持友好、幽默的语气，像朋友一样交流
2. 可以回答各种问题，分享观点和建议
3. 如果话题自然过渡到礼物相关，可以顺势引导用户表达送礼需求
4. 不要强行推销礼物推荐功能，让对话自然流畅
5. 回复控制在3-5句话内，简洁而有温度"""

    prompt = f"以下是你和用户的对话历史：\n{history}\n\n请自然回应用户的最新消息："

    try:
        reply = chat(prompt, system=system)
        state["reply"] = reply
        state["stage"] = "chatting"
    except Exception as e:
        print(f"[chat_agent] 聊天失败: {e}")
        state["reply"] = "抱歉，我刚才走神了，能再说一遍吗？"
        state["stage"] = "chatting"

    return state

def product_inquiry_agent(state: GiftState) -> GiftState:
    """商品咨询智能体 - 基于推荐列表和用户选中的商品生成详细介绍"""
    recommendations = state.get("recommendations", [])
    index = state.get("selected_index") or 0

    # 从推荐列表中获取用户选中的商品
    if recommendations and 0 <= index < len(recommendations):
        product = recommendations[index]
    else:
        # 兜底：使用已保存的选中商品或默认值
        product = state.get("selected_product") or {"name": "这款礼物"}

    # 将商品完整信息转为JSON字符串
    import json
    product_info = json.dumps(product, ensure_ascii=False, indent=2)

    system = """你是挑礼大师，专业的礼物推荐专家。
用户对你推荐的某个商品感兴趣，想要了解更多信息。

请基于商品的完整信息，发挥你的专业知识，为用户生成：
1. 商品亮点介绍（2-3个核心卖点，突出品质感和实用性）
2. 送礼场景匹配度（为什么这个礼物适合当前的送礼对象和场合）
3. 使用场景描绘（让收礼人感受到这份礼物的价值）
4. 贴心提示（1-2句购买或使用建议）

要求：
- 用温暖、真诚的语气，像朋友分享好物一样
- 内容要具体生动，避免泛泛而谈
- 控制在5-7句话内，每句话不要太长
- 适当使用emoji增加亲和力"""

    prompt = f"""用户看中了第{index + 1}个推荐商品。

商品完整信息：
{product_info}

送礼场景：
- 对象：{state.get('recipient', '未知')}
- 场合：{state.get('occasion', '未知场合')}
- 礼物类型：{state.get('gift_type', '未指定')}
- 预算：{state.get('budget', '未指定')}

请为用户详细介绍这个商品，让它听起来很有吸引力："""

    try:
        reply = chat(prompt, system=system)
        state["reply"] = reply
        state["stage"] = "chatting"
    except Exception as e:
        print(f"[product_inquiry_agent] 生成详情失败: {e}")
        product_name = product.get("name") if isinstance(product, dict) else "这款礼物"
        state["reply"] = f"{product_name}是个非常不错的选择！✨ 相信收到的人一定会很喜欢！🎁"
        state["stage"] = "chatting"

    return state

_recommend_cache: dict = {}

def recommend_agent(state: GiftState) -> GiftState:
    """使用LLM从gifts.json中选择推荐礼物"""
    # 构建缓存key，包含所有关键信息（包括已排除的商品）
    excluded = state.get("excluded_gifts", [])
    cache_key = f"{state.get('recipient')}|{state.get('occasion')}|{state.get('budget')}|{state.get('gift_type')}|{state.get('category')}|{state.get('preference')}|{','.join(excluded)}"
    state["cache_key"] = cache_key

    if cache_key in _recommend_cache:
        print("[recommend_agent] 命中缓存")
        state["recommendations"] = _recommend_cache[cache_key]
        return state

    # 加载gifts.json
    gifts = load_gifts_db()

    # 过滤掉用户明确不喜欢的商品
    if excluded:
        gifts = [g for g in gifts if f"{g['品牌']} {g['名称']}" not in excluded]

    system = """你是挑礼大师，专业的礼物推荐专家。
你的任务是从提供的商品列表中，根据用户需求挑选3-4款最合适的礼物。

输出格式要求（严格JSON数组）：
[{
  "name": "品牌 商品名称",
  "price": "¥价格",
  "reason": "推荐理由（1句话，结合场合、对象、商品特点、礼物类型）",
  "tags": ["品类", "场合", "礼物类型"],
  "emoji": "代表性emoji"
}]

注意：
1. 必须从提供的商品列表中选择，不能编造商品
2. 价格必须符合用户预算要求
3. 考虑送礼对象、场合和礼物类型的匹配度
4. 礼物类型偏好：
   - 实用型：优先选择日常可用的家电、数码、护肤品等
   - 纪念型：优先选择首饰、手表、珠宝等可长期保存的
   - 体验型：优先选择旅游、课程、门票等体验类
   - 装饰型：优先选择摆件、艺术品、文创等装饰类
5. 只输出JSON，不要有其他内容"""

    # 构建商品列表文本
    gifts_text = "\n".join([
        f"- {g['品牌']} {g['名称']} | 价格:¥{g['价格']} | 品类:{g['品类']} | 场合:{g['场合']} | 对象:{g['对象']}"
        for g in gifts
    ])

    prompt = f"""用户需求：
- 送礼对象：{state.get('recipient', '未知')}
- 场合：{state.get('occasion', '未知')}
- 预算：{state.get('budget', '未知')}
- 礼物类型：{state.get('gift_type', '不限')}
- 品类偏好：{state.get('category', '不限')}
- 风格偏好：{state.get('preference', '不限')}

可选商品列表（共{len(gifts)}件）：
{gifts_text}

请从以上商品列表中，为用户推荐3-4款最合适的礼物。"""

    try:
        result = chat(prompt, system=system)
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        recommendations = json.loads(result)
        state["recommendations"] = recommendations
        _recommend_cache[cache_key] = recommendations
        print(f"[recommend_agent] LLM从gifts.json中选择了 {len(recommendations)} 个礼物")
    except Exception as e:
        print(f"[recommend_agent] LLM解析失败: {e}")
        # 如果LLM失败，使用简单的规则匹配作为fallback
        matched_gifts = match_gifts(
            recipient=state.get('recipient'),
            occasion=state.get('occasion'),
            budget=state.get('budget'),
            category=state.get('category'),
            preference=state.get('preference'),
            top_k=4
        )
        if matched_gifts:
            recommendations = [format_gift_recommendation(gift) for gift in matched_gifts]
            state["recommendations"] = recommendations
            _recommend_cache[cache_key] = recommendations
        else:
            state["recommendations"] = []

    return state

def reason_agent(state: GiftState) -> GiftState:
    recs = state.get("recommendations", [])

    if not recs:
        state["reply"] = "抱歉，我暂时没有找到合适的推荐，能告诉我更多信息吗？"
        return state

    system = """你是挑礼大师，用温暖有趣的语气介绍推荐结果。
开场先简短呼应用户的送礼场景（1句话），然后引导用户查看推荐卡片，最后问用户是否有其他偏好。
总共3-4句话，自然流畅，不要机械列举商品。"""

    rec_names = "、".join([r.get("name", "") for r in recs])
    prompt = f"""送礼场景：送给{state.get('recipient')}，{state.get('occasion')}，预算{state.get('budget')}
推荐商品：{rec_names}
请生成引导语："""

    reply = chat(prompt, system=system)
    state["reply"] = reply
    state["stage"] = "refining"

    return state

def validate_agent(state: GiftState) -> GiftState:
    recs = state.get("recommendations", [])
    if not recs:
        return state

    system = """你是质量校验专家。
检查推荐商品是否符合用户需求，剔除明显不合适的（如超出预算、不符合场合）。
输出保留的商品JSON数组，格式与输入相同。
如果全部合适，原样返回。"""

    prompt = f"""用户需求：送给{state.get('recipient')}，{state.get('occasion')}，预算{state.get('budget')}
推荐商品：{json.dumps(recs, ensure_ascii=False)}
请校验并返回合适的商品："""

    try:
        result = chat(prompt, system=system)
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0].strip()
        elif "```" in result:
            result = result.split("```")[1].split("```")[0].strip()
        validated = json.loads(result)
        if isinstance(validated, list) and len(validated) > 0:
            state["recommendations"] = validated
    except Exception as e:
        print(f"[validate_agent] 校验失败，使用原始结果: {e}")

    return state
