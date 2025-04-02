import os
from openai import OpenAI
import httpx
from swarm import Swarm, Agent
from utils.condense import condense_msg
from utils.caculator import query_and_calculate as query_and_compute
import json
import time


# API密钥和基础URL设置
api_key = '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'
base_url = 'https://api.openai.com/v1'
# api_key = 'sk-195bd56c24a14123be57b0d94fa45e3d'
# base_url = 'https://api.deepseek.com/v1'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url


http_client = httpx.Client(
    timeout=httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
)

client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
swarm_client = Swarm(client)



def transmit_refined_params_and_db_info(time_info: str, chart_info: str):

    print("OK")
    print(time_info)

    with open("config.json", "r", encoding="utf-8") as f:
        db_info: str = json.dumps(json.load(f), ensure_ascii=False)

    print("OK")
    message = condense_msg(time_info, chart_info, db_info)
    print(message)
    print("OK")

    hazuki = Agent(
        name="Tomoka",
        model="gpt-4o-mini",
        instructions=
        """
        你是一个数据分析助手,你的名字是Tomoka，你每次都请务必根据message里的信息调用query_and_compute函数，获取分析结果,
        query_and_compute(start_index: str, last_index: str, value_info, chart_type: str, group_by_fields: List[str] = None, limit: int = 5, group_by: str = None, ascending: bool = False)
        这个函数用于从数据库里获取数据，然后把数据进行一些统计处理，最后返回str类型的分析结果，用于提供给前端绘图。
        
        你的messages格式是固定的，请注意其中的time_info, chart_info, db_info
        你要根据db_info的信息，，把time_info和chart_info调整为对应的格式，然后把他们作为参数传入query_and_compute函数里
        
        start_index: str, last_index: str的信息是与数据库对应的，也就是说你需要根据db_info提供的信息去修改start_index: str, last_index: str的格式，从而保证适配
        value_info: str的信息是用户需要进行数据分析的那一类别或分析的对象，你需要将此参数转化为合适的value_info: str值
        
        chart_type: str的信息是用户需要进行数据分析的时需要绘图的格式，你需要将此参数转化为合适的chart_type: str值
        chart_type: str只能是以下几种值:
        - "bar": 条形图
        - "line": 折线图 
        - "pie": 饼图
        - "scatter": 散点图
        - "heatmap": 热力图
        - "yoy_mom": 同比环比分析
        - "multi_field": 多字段组合分析
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
        
        我们举例假设
        time_info是"2025年4月",而根据db_info，其应该是"2025-04"这样的格式，那么
        start_index: str = "2025-04-01", last_index: str = "2025-04-30"
        同理如果chart_info是"考勤情况"，而根据db_info，其应该对应"attendance"这个表单，而你注意到这个表单记录了这个月每位员工的"出勤","迟到","缺勤"等情况
        那么可以判断coll_info = "attendance", value_info = "考勤"
        同时判断chart_type适合"bar","line","pie","scatter","heatmap"里哪一种图然后填入       
        你将得到一个str类型的返回值
        """,
        functions=[query_and_compute]
    )
    print("OK")

    start_time = time.time()
    assistant = swarm_client.run(
        agent = hazuki,
        messages = [{"role": "user", "content": message}]
    )
    end_time = time.time()
    print(f"耗时: {end_time - start_time:.2f}秒")


    print("OK")
    del hazuki
    print("OK")
    return assistant


def init_agent(
        model_name: str = 'gpt-4o-mini',
        # model_name: str = 'deepseek-chat',
):
    print('agent init')
    # 智能体定义
    return Agent(
        name='Agent Main',
        model=model_name,
        instructions=
        """
        你是一个数据分析助手。你可以通过调用函数帮助用户获取数据信息和分析计算结果。也可以作为客服智能回答用户问题。
        当用户需要你进行数据分析时，请考虑调用函数
        transmit_refined_params_and_db_info(time_info: str, chart_info: str)
        time_info: 时间或者索引信息
        chart_info: 待分析对象信息
        示例如下：假如用户询问“请为我统计分析一下2025年4月的考勤情况”
        那么时间或索引信息就是“2025年4月”，待分析对象信息就是“考勤情况”
        也就是time_info = "2025年4月", chart_info = "考勤情况"
        把这个作为参数传入transmit_refined_params_and_db_info函数，他的返回值类型是str
        
        如果你判断没有索引信息，那么time_info = "None"
        注意不是NoneType，而是字符串"None"
        
        """,
        functions=[
            transmit_refined_params_and_db_info
        ]
    )



if __name__ == '__main__':
    agent_main = init_agent(model_name='gpt-4o')
    # TODO: 新开页面，记忆，functions
    response = swarm_client.run(agent_main,messages=[{"role":"user","content":"你好"}])
    print(response)