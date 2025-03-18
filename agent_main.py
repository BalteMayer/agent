import os
from openai import OpenAI, RateLimitError
from swarm import Swarm, Agent
import cv2 as cv
from utils.loop import run_demo_loop


api_key = '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'
base_url = 'https://api.openai.com/v1'

os.environ['OPENAI_API'] = api_key
os.environ['OPENAI_BASE_URL'] = base_url

client = OpenAI(api_key=api_key, base_url=base_url)

swarm_client = Swarm(client)

# TODO:模型选择，语言选择，数据调用，图表生成，图表返回

model_name = 'gpt-4o-mini'
language = 'zh'
data = 'data'
chart = 'chart'

def choose_model(model_name):
    return model_name



def choose_language(language):
    return language

agent_main = Agent(
    name='Agent Main',
    model=model_name,
    instructions="你是一个乐于助人的智能体",
    stream=True,
)

run_demo_loop(client, agent_main)