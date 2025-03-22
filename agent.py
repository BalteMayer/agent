import os
from openai import OpenAI
import httpx
from swarm import Swarm, Agent

# API密钥和基础URL设置
api_key = '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'
base_url = 'https://api.openai.com/v1'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url

# 创建具有更长超时时间的HTTP客户端
http_client = httpx.Client(
    timeout=httpx.Timeout(connect=30.0, read=180.0, write=30.0, pool=30.0)
)

# 使用自定义HTTP客户端初始化OpenAI客户端
client = OpenAI(api_key=api_key, base_url=base_url, http_client=http_client)
swarm_client = Swarm(client)

def init_agent(
        model_name: str = 'gpt-4o-mini',
):
    print('agent init')
    # 智能体定义
    return Agent(
        name='Agent Main',
        model=model_name,
        instructions=f"你是一个乐于助人的智能体。",
        functions=[]
    )

if __name__ == '__main__':
    # 智能体定义
    agent_main = init_agent(model_name='gpt-4o')
    # TODO: 新开页面，记忆，functions
    response = swarm_client.run(agent_main,messages=[{"role":"user","content":"你好"}])
    print(response)