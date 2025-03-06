standards = [
"""
- **核心要素前置**：主实体+关键属性结构（如"新冠疫苗副作用"）
- **时态显性化**：将"明年"等相对时间转为绝对时间（如"2025年总统大选"）
- **去疑问结构化**：
   - 去除"如何"/"怎样"→转名词结构（"制作方法"→"手工皂制作流程"）
   - 转化"为什么"→"原因分析"（如"日元贬值原因"）
- **领域适配**：
   - 学术查询：添加"研究"/"论文"后缀（如"阿尔茨海默症治疗 最新研究"）
   - 时事类：保留精确时间戳（如"2024年5月台海局势"）
- **多实体处理**：用连接符关联（如"中美AI技术发展对比"）
""",
"""
- **多维度覆盖**：生成的关键词应覆盖用户需求的不同维度（如"特斯拉最新车型续航数据"和"特斯拉最新车型充电效率"）
- **冗余控制**：避免生成意义重复的关键词（如"特斯拉续航"和"特斯拉电池续航"）
"""
]

quality_check = """
✓ 长度控制在10-15个汉字
✓ 包含至少2个关键词
✓ 时间/地点等限定词完整保留
✓ 避免否定式表达（"不"->"缺乏"）
"""

SKIP_SEARCH_MAKER = '<|NotKeyword|>'
special = f"""
**特殊情况处理**：
- 如果问题明显不适合使用搜索引擎查询（如主观问题、情感问题、无法通过搜索得到答案的问题），则直接输出 `{SKIP_SEARCH_MAKER}`
"""

one_key_shots = """
示例对照：
{name}：心脏病发作有哪些症状？
转换后：心脏病发作的典型症状

{name}：特斯拉最新车型的续航里程？
转换后：特斯拉最新车型续航数据

{name}：2024年诺贝尔文学奖得主？
转换后：2024诺贝尔文学奖获得者

"""

multi_key_shots = """
示例参考：
{name}：2024年诺贝尔文学奖得主？
转换后：2024诺贝尔文学奖获得者

{name}：特斯拉最新车型的续航里程？
转换后：特斯拉最新车型续航数据 | 特斯拉最新车型电池性能

{name}：如何学习一门新语言最快？
转换后：语言学习高效方法 | 新语言学习技巧 | 语言学习工具推荐

{name}：苹果公司最新发布的iPhone有哪些新功能？
转换后：iPhone最新机型功能解析 | 苹果新品发布会亮点 | iPhone用户体验评测

以下是你要处理的{name}的相关信息：

"""

KEYWORD_EXTRACT_NH_OK_TEMPLATE_ZH = \
"你需将用户提供的问题转换为适合搜索引擎查询的独立问题。\n\n" + \
"处理规范：" + standards[0] + "\n质量检测标准：" + quality_check + special + \
one_key_shots.format(name='问题') + "问题：{question}\n转换后：\n"

KEYWORD_EXTRACT_HH_OK_TEMPLATE_ZH = \
"你需将用户提供的追问转换为适合搜索引擎查询的独立问题。\n\n" + \
"处理规范：" + standards[0] + "\n质量检测标准：" + quality_check + special + \
one_key_shots.format(name='追问') + "历史聊天记录：\n\n {chat_history}\n\n追问：{question}\n转换后：\n"

KEYWORD_EXTRACT_NH_MK_TEMPLATE_ZH = \
"你需要将用户提供的问题转换为适合搜索引擎查询的多个独立关键词，确保每个关键词都能独立覆盖用户需求的不同维度。\n\n" + \
"处理规范：" + ''.join(standards) + "\n质量检测标准：" + quality_check + special + \
multi_key_shots.format(name='问题') + "问题：{question}\n转换后：\n"

KEYWORD_EXTRACT_HH_MK_TEMPLATE_ZH = \
"你需要将用户提供的追问转换为适合搜索引擎查询的多个独立关键词，确保每个关键词都能独立覆盖用户需求的不同维度。\n\n" + \
"处理规范：" + ''.join(standards) + "\n质量检测标准：" + quality_check + special + \
multi_key_shots.format(name='追问') + "历史聊天记录：\n\n {chat_history}\n\n追问：{question}\n转换后：\n"

# KEYWORD_EXTRACT_NH_MK_TEMPLATE_ZH = \
# "你需要将用户提供的问题转换为适合搜索引擎查询的多个独立关键词，确保每个关键词都能独立覆盖用户需求的不同维度。\n\n" + \
# "\n质量检测标准：" + quality_check + special + \
# multi_key_shots.format(name='问题') + "问题：{question}\n转换后：\n"

# KEYWORD_EXTRACT_HH_MK_TEMPLATE_ZH = \
# "你需要将用户提供的追问转换为适合搜索引擎查询的多个独立关键词，确保每个关键词都能独立覆盖用户需求的不同维度。\n\n" + \
# "\n质量检测标准：" + quality_check + special + \
# multi_key_shots.format(name='追问') + "历史聊天记录：\n\n {chat_history}\n\n追问：{question}\n转换后：\n"


KEYWORD_EXTRACT_NH_OK_TEMPLATE_EN = \
"""You will give a follow-up question.  You need to rephrase the follow-up question if needed so it is a standalone question that can be used by the AI model to search the internet.

Example:

Follow-up question: What are the symptoms of a heart attack?

Rephrased question: Symptoms of a heart attack.

Follow-up question: Where is the upcoming Olympics being held?

Rephrased question: Location of the upcoming Olympics.

Follow-up question: Taylor Swift's latest album?

Rephrased question: Name of Taylor Swift's latest album.

Follow-up question: {question}

Rephrased question:
"""

KEYWORD_EXTRACT_HH_OK_TEMPLATE_EN = \
"""You will give a follow-up question.  You need to rephrase the follow-up question if needed so it is a standalone question that can be used by the AI model to search the internet.

Example:

Follow-up question: What are the symptoms of a heart attack?

Rephrased question: Symptoms of a heart attack.

Follow-up question: Where is the upcoming Olympics being held?

Rephrased question: Location of the upcoming Olympics.

Follow-up question: Taylor Swift's latest album?

Rephrased question: Name of Taylor Swift's latest album.


Previous Conversation:

{chat_history}

Follow-up question: {question}

Rephrased question:
"""


