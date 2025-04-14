from src.caculator import query_and_calculate as mongodb_caculator
from src.get_db_config import describe_db_info
from src.mysql_caculator import  mysql_caculator
from src.query_database import query_database
from utils import logger
from utils import condense_msg
from swarm import Swarm, Agent
from openai import OpenAI
import httpx
import json
import time
import os
import sys
from pathlib import Path
import re

def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


from dotenv import load_dotenv

if getattr(sys, 'frozen', False):
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent.parent

env_path = base_dir / ".env"

# # 先清除可能存在的环境变量
# if 'OPENAI_API_KEY' in os.environ:
#     logger.info(f"发现现有的OPENAI_API_KEY环境变量: {os.environ['OPENAI_API_KEY'][:5]}...")

# 现在加载.env文件

logger.info(f"加载环境变量文件: {env_path}")

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# 检查加载结果
api_key = os.environ.get('OPENAI_API_KEY')
logger.info(f"加载后的API密钥: {api_key[:5]}..." if api_key and len(api_key) > 5 else "未找到API密钥")

base_url = os.environ.get('OPENAI_BASE_URL')

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url


http_client = httpx.Client(
    timeout=httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
)

client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
swarm_client = Swarm(client)



def transmit_refined_params_and_db_info(time_info: str, chart_info: str):


    logger.info("called")

    try:
        config_path = os.path.join(get_base_path(), 'data', 'config.json')
        with open(config_path, "r", encoding="utf-8") as f:
            db_info = json.load(f)
            {
                name: {"fields": table["fields"]}
                for name, table in db_info.get("mysql", {}).get("tables", {}).items()
            }

    except FileNotFoundError:
        logger.error(f"配置文件 {config_path} 未找到，请检查路径和文件名")
        return "配置文件未找到"


    message = condense_msg(time_info, chart_info, db_info)



    hazuki = Agent(
        name="Tomoka",
        model="gpt-4o-mini",
        instructions=
        """
        你是一个数据分析助手,你的名字是Tomoka，你每次都请务必根据message里的信息判断是mysql还是mongodb，然后调用mysql_caculator或者mongodb_caculator函数，获取分析结果,
        但当用户仅需要查询时，你就调用query_database函数，获取数据

        至于是什么数据库你通过db_info的信息来判断，mysql应该会在很靠前的位置明确说是mysql

        mongodb_caculator(start_index: str, last_index: str, value_type, coll_info: str, chart_type: str, group_by_fields: List[str] = None, limit: int = 5, group_by: str = None, ascending: bool = False)
        这个函数用于从数据库里获取数据，然后把数据进行一些统计处理，最后返回str类型的分析结果，用于提供给前端绘图。


        你只被允许调用一次函数，所以你要选择最优的一组参数传入，特别是选择chart_type,你只能选择一个chart_type
        You're only allowed to call the function once, so you need to choose the optimal set of parameters to pass in — especially the `chart_type`,you can only choose one chart_type

        你的messages格式是固定的，请注意其中的time_info, chart_info, db_info
        你要根据db_info的信息，，把time_info和chart_info调整为对应的格式，然后把他们作为参数传入mongodb_caculator函数里

        start_index: str, last_index: str的信息是与数据库对应的，也就是说你需要根据db_info提供的信息去修改start_index: str, last_index: str的格式，从而保证适配
        value_type: str的信息是用户需要进行数据分析的那一类别或分析的对象，你需要将此参数转化为合适的value_type: str值

        chart_type: str的信息是用户需要进行数据分析的时需要绘图的格式，你需要将此参数转化为合适的chart_type: str值
        chart_type: str只能是以下几种值:
        - "bar": 条形图
        - "line": 折线图
        - "pie": 饼图
        - "scatter": 散点图
        - "heatmap": 热力图
        - "ranking": 排名分析

        coll_info: str的信息是用户需要进行数据分析的时需要绘图的对象所在的collection的名称，你需要将此参数转化为合适的coll_info: str值

        如果你判断用户没有输入索引信息，那么start_index: str, last_index: str都设置为None，表示统计全局。比如用户说"我了解各个部门人员数量情况"，那么这个是索引时间不明确，
        start_index: str = None, last_index: str = None
        重申一遍，没有明确给出索引相关信息就是总体讨论"我想了解XX情况"等于"我想了解总体的XX情况"

        如果用户需要同比环比分析，例如"与去年同期相比，今年的销售增长了多少"、"4月与3月相比业绩变化如何"，
        请使用chart_type="yoy_mom"。

        如果用户需要多维度分析，例如"按部门和考勤状态统计人数"、"分析不同部门的考勤情况",
        请使用chart_type="multi_field"，并设置group_by_fields参数，例如group_by_fields=["部门", "考勤"]。

        如果用户需要排名或TOP N的分析，例如"显示考勤率最高的前5个部门"、"哪些员工迟到次数最多"，
        请使用chart_type="ranking"，并设置limit参数(默认为5)和group_by参数。
        当用户查询包含"最高"、"最低"、"排名"、"前几"、"top"等词汇时，必须使用chart_type="ranking"。
        例如:
        - "显示考勤率最高的前5个部门" -> chart_type="ranking", value_type="考勤", group_by_fields="部门", limit=5
        - "哪些部门的出勤率最好" -> chart_type="ranking", value_type="考勤", group_by_fields="部门"

        你只被允许调用一次函数，所以你要选择最优的一组参数传入，特别是选择chart_type,你只能选择一个chart_type
        You're only allowed to call the function once, so you need to choose the optimal set of parameters to pass in — especially the `chart_type`,you can only choose one chart_type

        我们举例假设
        time_info是"2025年4月",而根据db_info，其应该是"2025-04"这样的格式，那么
        start_index: str = "2025-04-01", last_index: str = "2025-04-30"
        同理如果chart_info是"考勤情况"，而根据db_info，其应该对应"attendance"这个表单，而你注意到这个表单记录了这个月每位员工的"出勤","迟到","缺勤"等情况
        那么可以判断coll_info = "attendance", value_type = "考勤"
        同时判断chart_type适合"bar","line","pie","scatter","heatmap"里哪一种图然后填入
        你将得到一个str类型的返回值

        你只被允许调用一次函数，所以你要选择最优的一组参数传入，特别是选择chart_type,你只能选择一个chart_type
        You're only allowed to call the function once, so you need to choose the optimal set of parameters to pass in — especially the `chart_type`,you can only choose one chart_type
        mysql_caculator(
            start_index=""，  # 可选，开始日期
            last_index="",   # 可选，结束日期
            value_type=""，        # 要分析的字段
            table_name=""， # 表名
            chart_type=""   # 图表类型:"bar":条形图,"line":折线图,"pie":饼图,"scatter":散点图,"heatmap": 热力图,"ranking": 排名分析
        )
        可以知道，这是专门用于mysql的计算的，而mongodb_caculator用于mongodb

        query_database函数接受一个字符串
        这个字符串非常非常非常重要，是一条mysql指令
        这条指令仅用于查询数据，当你明确用户仅需要查询数据而非分析情况或画图时你调用这个函数，
        **只能根据db_info的数据库表单字段名字和数据类型写指令进行普通查询或条件查询**
        **比如我询问”我想查询视觉组的女队员数据“，那么你就要根据db_info的表单字段，视觉组对应的是jlugroup，你不能自己换成group;又或者性别是sex，你不能写成gender**
        **一定要弄明白每张表的数据类型，数据结构，字段名，严禁传错**

        比如说用户问"我想知道data里2020后加入的的五条数据"
        那么你就生成代码"SELECT * FROM Data WHERE age > '2020' LIMIT 5"并传入
        一定要弄明白每张表的数据类型，数据结构，严禁传错
        记住用户是否限定了数量，比如说“第一个”，“一个”，“五条”这种，如果有，比如说一个，那就需要添加”LIMIT 1“
        并且这个函数返回一个字符串
        """,
        # context_variables = {"meta_data":db_info},

        functions=[mongodb_caculator, mysql_caculator, query_database],
    )


    start_time = time.time()
    assistant = swarm_client.run(
        agent = hazuki,
        messages = [{"role": "user", "content": message}],
        debug=True
    )

    logger.info(f"Assistant: {assistant}")

    end_time = time.time()
    logger.info(f"耗时: {end_time - start_time:.2f}秒")

    result_str = assistant.messages[1]['content']
    logger.info(f"Assistant: {result_str}")


    chart_list = ["bar", "line", "pie", "scatter", "heatmap", "ranking", "yoy_mom", "multi_field", "chart_type"]
    if all(c not in result_str[1:35] for c in chart_list):



        try:
            result_str = result_str[result_str.find('{'):result_str.rfind('}')+1]
            result_str = result_str.replace("None", "null").replace('None', 'null')
            result_str = "["+result_str+"]"
            result_str = result_str.replace("'", '"')
            logger.info(f"结果: {result_str}")
            result_json = json.loads(result_str)

            # result_json = result_json["result"]
            # logger.info(f"结果: {result_json}")

            del hazuki
            return f"```{result_json}```"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            del hazuki
            return f"解析错误: {result_str}"
    else:
        try:
            result_str = result_str[result_str.find('{'):result_str.rfind('}') + 1]
            result_json = json.loads(result_str)
            result_json = result_json["result"]
            logger.info(f"结果: {result_json}")
            del hazuki
            return f"```{result_json}```"
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析错误: {e}")
            del hazuki
            return f"解析错误: {result_str}"



def init_agent(
        model_name: str = 'gpt-4o-mini',
        # model_name: str = 'deepseek-chat',
):

    # 智能体定义
    return Agent(
        name='Agent Main',
        model=model_name,
        instructions=
        """
        你是一个数据分析助手与查询请求转发助手
        你可以通过调用函数帮助用户获取数据信息和分析计算结果。也可以作为客服智能回答用户问题。你严格遵循我的指示，任何函数返回值都会原封不动地返回给用户。
        当遇到用户的查询请求时，严厉禁止”抱歉，我无法直接访问或查询数据库中的具体数据。如果您能提供更多的上下文或者具体的数据分析需求，我将尽力帮助您。“
            因为你不会但可以调用函数，所以禁止拒绝，必须调用函数
        别人问你你不要说你基于chatgpt，而是说你基于deepseek-v3
        
        
        你只被允许调用一次函数，所以你要选择最优的一组参数传入
        You're only allowed to call the function once,
        你只被允许调用一次函数，所以你要选择最优的一组参数传入
        You're only allowed to call the function once
        
        当用户需要你进行数据分析时，请考虑调用函数。如果没有分析类的需求请不要调用函数。
        以及当用户需要查询数据库时，同样调用函数和传数据
        以及当用户需要查询数据库时，同样调用函数和传数据
        以及当用户需要查询数据库时，同样调用函数和传数据
        以及当用户需要查询数据库时，同样调用函数和传数据
        
        transmit_refined_params_and_db_info(time_info: str, chart_info: str)
            time_info: 时间或者索引信息
            chart_info: 待分析对象信息
            示例如下：假如用户询问“请为我统计分析一下2025年4月的考勤情况”
            那么时间或索引信息就是“2025年4月”，待分析对象信息就是“考勤情况”
            也就是time_info = "2025年4月", chart_info = "考勤情况"
            如果用户指定了图表类型，比如说“2024年3月考勤情况，画成折线图”,
            那么chart_info = "考勤情况,折线图"

            把这个作为参数传入transmit_refined_params_and_db_info函数，他的返回值类型是str
            
            如果你判断没有索引信息，那么time_info = "None"
            注意不是NoneType，而是字符串"None"
            
            最后你将获得一个str类型的返回值，你不能改动它，而是原封不动地返回给用户，同时根据其内容做一些专业的数据分析指导，期望在100字以内，20字以上
            这个返回值就是长这个结构的东西[{}]，把它原封不动发给用户，不能自己总结。
            注意，不论发生什么，返回值必须提供
            
            你不被允许自己总结
            比如
            返回值为{'chart_type': 'bar', 'categories': ['出勤', '迟到', '缺勤', '请假'], 'values': [23, 3, 1, 3], 'statistics': {'mean': 7.5, 'median': 3.0, 'max': 23, 'min': 1, 'std': 8.986100377805714, 'variance': 80.75}}
            你不能说
             "结果显示2024年3月的考勤情况，条形图信息如下：出勤23天，迟到3天，缺勤1天，请假3天。可以使用这些数据在Excel等工具中创建饼状图
             ，帮助更直观地了解不同考勤类别所占比例。需要更多帮助请告诉我！"
            因为这样没有提供返回值给用户
            
        当用户需要知道数据库的基本信息时，请考虑调用函数
        比如”请告诉我数据库信息“
        describe_db_info -> str
            这个函数用于获取数据库的基本信息，返回值是一个str类型的描述信息
            你需要根据这个信息把数据库基本信息以更语义化和自然的方式描述给用户
        """,
        debug=True,
        functions=[
            transmit_refined_params_and_db_info,
            describe_db_info
        ]
    )



if __name__ == '__main__':
    agent_main = init_agent(model_name='gpt-4o')
    # TODO: 新开页面，记忆，functions
    response = swarm_client.run(agent_main,messages=[{"role":"user","content":"你好"}])
    print(response)