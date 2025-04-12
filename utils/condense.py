def condense_msg(time_info: str, chart_info: str, database_type: str, db_info: str):
    instruction_info = {
        "索引信息": time_info,
        "图表类型": chart_info,
        "数据库类型":database_type,
        "数据库信息": db_info
    }

    return f"{instruction_info}"
