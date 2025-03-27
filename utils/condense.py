def condense_msg(time_info: str, chart_info: str, db_info: str):
    instruction_info = {
        "索引信息": time_info,
        "图表类型": chart_info,
        "数据库信息": db_info
    }

    return f"{instruction_info}"
