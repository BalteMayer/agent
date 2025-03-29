import json
with open("../config.json", "r", encoding="utf-8") as f:
    db_info: str = json.dumps(json.load(f), ensure_ascii=False)
print(db_info)