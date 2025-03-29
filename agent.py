import os
from openai import OpenAI
import httpx
from swarm import Swarm, Agent
import cv2 as cv
from tools.chart import plot_material_category_distribution, plot_sign_in_trend, plot_group_member_count
from utils.condense import condense_msg
import json
import time


# API密钥和基础URL设置
api_key = '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'
base_url = 'https://api.openai.com/v1'
# api_key = 'sk-195bd56c24a14123be57b0d94fa45e3d'
# base_url = 'https://api.deepseek.com/v1'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url

# 创建具有更长超时时间的HTTP客户端
http_client = httpx.Client(
    timeout=httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
)

# 使用自定义HTTP客户端初始化OpenAI客户端
client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
swarm_client = Swarm(client)


class database:
    pass


def query_and_compute(start_index: str, last_index: str, chart_info):
    with open("config.json", "r", encoding="utf-8") as f:
        db_info: str = json.dumps(json.load(f), ensure_ascii=False)
    print(start_index, last_index, chart_info, db_info)
    return f"根据数据库信息{db_info}，查询{start_index}到{last_index}的数据，然后进行统计分析"

def transmit_refined_params_and_db_info(time_info: str, chart_info: str):

    print("OK")

    # 读取 JSON 文件并转换为字符串
    with open("config.json", "r", encoding="utf-8") as f:
        db_info: str = json.dumps(json.load(f), ensure_ascii=False)

    print("OK")
    message = condense_msg(time_info, chart_info, db_info)
    print(message)
    print("OK")

    hazuki = Agent(
        name="hazuki",
        model="gpt-4o-mini",
        instructions=
        """
        你是一个数据分析助手，你每次都请务必根据message里的信息调用query_and_compute函数，获取分析结果,
        query_and_compute(start_index: str, last_index: str, chart_info: str,)
        这个函数用于从数据库里获取数据，然后把数据进行一些统计处理，最后返回str类型的分析结果，用于提供给前端绘图。
        你的messages格式是固定的，请注意其中的time_info, chart_info, db_info
        你要根据db_info的信息，，把time_info和chart_info调整为对应的格式，然后把他们作为参数传入query_and_compute函数里
        time_info的信息是与数据库对应的，也就是说你需要根据db_info提供的信息去修改time_info的格式，从而保证适配。
        chart_info的信息是用户需要进行数据分析的那一类别或分析的对象，你需要将此参数转化为合适的cahrt_info值
        chart_info只能是以下几种值:"bar","line","pie","scatter","heatmap"。其分别对应条形图，折线图，饼图，散点图，热力图。而你需要根据chart_info的内容，选择合适的图表类型，将其作为参数。
        
        我们举例假设
        time_info是"2025年4月",而根据db_info，其应该是"2025-04"这样的格式，那么
        start_index: str = "2025-04-01", last_index: str = "2025-04-30"
        同理如果chart_info是"考勤情况"，而根据db_info，其应该对应"attendance"这个表单，而你注意到这个表单记录了这个月每位员工的"出勤","迟到","缺勤"情况。那么你可以据此判断应该绘制一个饼状图
        那么你判断chart_type适合哪一种图然后填入       
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
        """,
        functions=[
            transmit_refined_params_and_db_info
        ]
    )



if __name__ == '__main__':
    # 智能体定义
    agent_main = init_agent(model_name='gpt-4o')
    # TODO: 新开页面，记忆，functions
    response = swarm_client.run(agent_main,messages=[{"role":"user","content":"你好"}])
    print(response)