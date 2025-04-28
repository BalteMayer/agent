from baidusearch.baidusearch import search
from utils import logger


def search_web(query: str):
    """
    使用百度搜索API进行搜索，并返回结果。

    参数:
        query (str): 搜索关键词。

    返回:
        list: 搜索结果列表，每个结果包含标题、摘要和链接。
    """
    try:
        logger.info("called search_web")
        results = search(query,5)
        for item in results:
            item['abstract'] = item['abstract'].replace(chr(10), '').replace(' ', '')[:20]
        results_typed = f"%%%%{results}%%%%"
        logger.info(f"complete:{results_typed}")
        return f"%%%%{results}%%%%"
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    # 示例搜索关键词
    query = "人工智能趋势"
    search_results = search_web(query)

    print(f"搜索结果:{search_results}")