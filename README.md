# <span style="color:Maroon">端口版mongodb，mysql可用</span>

## <span style="color:LightCoral">项目结构与配置</span>

<div style="font-family: 'Microsoft YaHei';">
项目结构如下

```
|__.env
|__main.exe
|__data
    |__logs
    |   |__agent-2025-11-45.log
    |__memory
    |   |__127.0.0.1_202504080000.json
    |__config.json
```
其中.env和config.json都是需要更改的配置文件
config.json的mongodb格式和mysql格式如[config.json-mongodb版](./sample/mongodb_config.json)，[config.json-mysql版](asset/config.json)
所示，你在提取样例数据时请注意，对于长文本应当限制其字数不超过50字，
生成mysql配置文件可以参考[mysql_generator.py](./sample/mysql_generator.py)

.env格式如下
```
OPENAI_API_KEY=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
OPENAI_BASE_URL=https://api.openai.com/v1
```
data中的memory是记录的会话历史
</div>

## <span style="color:LightCoral">请求与相应格式</span>

<div style="font-family: 'Microsoft YaHei';">

#### 首先是**health**,检测端口状态
```bash
curl -X GET http://localhost:8001/health
```
##### 响应如下
```json
{
  "code": 200,
  "data": {
    "status": "healthy",
  }
}
```

#### 对话的POST请求如下

```bash
curl -X POST http://localhost:8001/api/chat \
  -H "Content-Type: application/json" \
  -H "X-Forwarded-For: $[USERNAME]" \
  -d '{
    "message": "tralarero tarlala",
    "session_id": "$[SESSION_ID]",
    "stream": false
}'
```
其中`$[USERNAME]`是用户名，`$[SESSION_ID]`是对话ID,后面不再赘述，`$[SESSION_ID]` 一定要选一个重复率低的，比如时间戳
##### 响应如下
```json
{
    "response": "你好！请问有什么我可以帮助您的？",
    "session_id": "114514"
}
```
我将在后面给出计算数据的result格式
#### 删除会话请求
```bash
curl -X DELETE http://localhost:8001/api/sessions/$[SESSION_ID] \
  -H "X-Forwarded-For: $[USERNAME]"
```
##### 响应如下
```
{ "status": "success" } //成功删除
{ "status": "not_found" } //未找到
```

#### 获取会话历史
```bash
curl --location 'http://localhost:8001/api/sessions' \
--header 'Content-Type: application/json' \
--header 'user_id: user' \
--header 'session_id: 202504080000
```
##### 响应如下
```json
{
    "code": 200,
    "data": {
        "session_id": "202504080000",
        "messages": [
            {
                "role": "user",
                "content": "帮我分析jlu分组情况"
            },
            {
                "role": "assistant",
                "content": "请问您有指定的时间或索引信息吗？这样我可以更好地帮助您进行分析。"
            },
            {
                "role": "user",
                "content": "帮我分析jlu分组情况"
            },
            {
                "role": "assistant",
                "content": "[{'chart_type': 'bar', 'categories': ['视觉组', '机械组', '电控组', '运营组', 'AI组', '软件组'], 'values': [47, 43, 126, 36, 36, 24], 'statistics': {'mean': 52.0, 'median': 39.5, 'max': 126, 'min': 24, 'std': 33.85754470326124, 'variance': 1146.3333333333333}}]\n\n根据分析，jlu分组情况的数据已显示在上方。不同组的人数分布情况可以帮助您针对性地进行资源配置和管理策略调整。"
            },
            {
                "role": "user",
                "content": "帮我分析jlu分组情况"
            },
            {
                "role": "assistant",
                "content": "请问您有指定的时间或索引信息吗？这样我可以更好地帮助您进行分析。"
            },
            {
                "role": "user",
                "content": "帮我分析jlu分组情况，无索引"
            },
            {
                "role": "assistant",
                "content": "[{'chart_type': 'bar', 'categories': ['视觉组', '机械组', '电控组', '运营组', 'AI组', '软件组'], 'values': [47, 43, 126, 36, 36, 24], 'statistics': {'mean': 52.0, 'median': 39.5, 'max': 126, 'min': 24, 'std': 33.85754470326124, 'variance': 1146.3333333333333}}]\n\n分析的结果显示了各个分组的人数分布及统计数据。根据这些信息，可以为每个组配置合适的资源和任务。"
            }
        ],
        "last_modified": null,
        "message_count": 8,
        "timestamp": "2025-04-12 19:23:40",
        "user": "user"
    }
}
```

</div>

## <span style="color:LightCoral">数据计算的请求内容与响应内容</span>


<div style="font-family: 'Microsoft YaHei';">

请求时说明白三点
 - 时间因素，如2025年3月/2025年3月1日到3月22日/不提供(如果是饼图等需要默认计算全部数据的)
 - 计算的对象，如分组情况
 - 数据库类型，如原问题为"毕业踩踩背情况"，需要变更为"毕业踩踩背情况/mysql"，再发请求

我给出一个样例
```bash
curl --location 'http://localhost:8001/api/chat
--header 'X-Forwarded-For=user' \
--header 'Content-Type: application/json' \
--data '{
  "message": "帮我分析一下jlu分组情况，饼图/mysql",
  "session_id": "202504080000",
  "stream": false
}'
```
会以
```
2025-04-12 11:55:51,265 - agent - INFO - 开始查询MySQL数据: Data, 字段: jlugroup起始索引: None, 结束索引: None, 图表类型: pie
```
这种形式查询

接着返回
```json
{
    "response": "[{'chart_type': 'pie', 'labels': ['视觉组', '机械组', '电控组', '运营组', 'AI组', '软件组'], 'values': [47, 43, 126, 36, 36, 24], 'percentages': [15.06, 13.78, 40.38, 11.54, 11.54, 7.69]}]\n\n您可以使用这些数据验证各组在jlu分组情况所占的比例，这种情况适合使用饼图来表示，以便更直观地了解各组的比例分配。如果需要进一步分析，请告诉我。",
    "session_id": "202504080000"
}
```
这就是一次含有数据分析的对话的完整流程

### 注意在响应里的result外面包了一个[]，我怕gpt抽风你们拿不出数据来

接下来我给出result格式
### result格式如下

#### 条形图/bar
```python
"result": {
    "chart_type": "bar",
    "categories": ["类别1", "类别2", ...],  // X轴标签
    "values": [值1, 值2, ...],             // 每个类别的计数/值
    "statistics": {
      "mean": 平均值,
      "median": 中位数,
      "max": 最大值,
      "min": 最小值,
      "std": 标准差,
      "variance": 方差
    }
  }
```

#### 折线图/line
```python
  "result": {
    "chart_type": "line",
    "x_axis": ["时间点1", "时间点2", ...],  // X轴时间序列
    "values": [值1, 值2, ...],            // Y轴值
    "trend": 趋势斜率,                    // 线性趋势斜率
    "prediction_next": 下一个预测值,       // 预测的下一个值
    "moving_average": [移动平均值1, ...]   // 移动平均
  }
```

#### 饼图/pie
```python
  "result": {
    "chart_type": "pie",
    "labels": ["标签1", "标签2", ...],     // 饼图扇区标签
    "values": [值1, 值2, ...],            // 每个扇区的值
    "percentages": [百分比1, 百分比2, ...]  // 每个扇区的百分比
  }
```

#### 散点图/scatter
```python
"result": {
    "chart_type": "scatter",
    "x": [x1, x2, ...],              // X轴坐标
    "y": [y1, y2, ...],              // Y轴坐标
    "x_field": "X轴字段名",           // X轴使用的字段
    "y_field": "Y轴字段名",           // Y轴使用的字段
    "correlation": 相关系数,          // 两个变量的相关系数
    "regression": {
      "slope": 斜率,                 // 回归线斜率
      "intercept": 截距,             // 回归线截距
      "line": [回归线y1, y2, ...]     // 回归线上的点
    }
  }
```

#### 热力图/heatmap
```python
"result": {
    "chart_type": "heatmap",
    "x_labels": ["x标签1", "x标签2", ...],  // X轴标签
    "y_labels": ["y标签1", "y标签2", ...],  // Y轴标签
    "x_field": "X轴字段名",                // X轴使用的字段
    "y_field": "Y轴字段名",                // Y轴使用的字段
    "matrix": [[值1,1, 值1,2, ...], [...]],  // 热力图矩阵
    "max_value": 最大值,                   // 矩阵中的最大值
    "min_value": 最小值                    // 矩阵中的最小值
}
```
#### 排名/rank
```python
"result": {
  "chart_type": "ranking",
  "ranks": [                         // 排名数据
    {
      "group_by字段名": "分组值",
      "total": 总数,
      "matches": 匹配数,
      "percentage": 百分比,
      "rank": 排名
    },
    ...
  ],
  "group_by": "分组字段",              // 用于分组的字段
  "value_type": "分析的字段",          // 分析的值字段
  "stats": {                         // 统计信息
    "average_percentage": 平均百分比,
    "max_percentage": 最大百分比,
    "min_percentage": 最小百分比
  }
}
```

## <span style="color:LightCoral">适配映射笑传之change change Bar</span>

### pie

```
defineProps({
  chartId: String，                 // Unique ID (auto-generated by default)
  pieData: Array<PieDataItem>,     // Pie chart data (required)
  title: String，                   // Chart title (optional)
});

piedata
[
  { name: "类别A", value: 40 },
  { name: "类别B", value: 25 },
  { name: "类别C", value: 35 },
]
```

### bar

```
defineProps({
  chartId: String，                // 唯一ID (默认会自动生成)
  xAxisData: Array<string>,       // X轴数据 (必传)
  barData: Array<Array<number>>,  // 柱状图数据 (必传，支持多组数据)
  seriesNames: Array<string>,     // 系列名称 (可选)
  title: String，                  // 图表标题 (可选)
  yAxisUnit: String，              // Y轴单位 (可选)
});
```

### line

```
defineProps({
  chartId: String，          // 唯一ID
  data: Array<number>,      // 必传的面积图数据数组
  xAxisLabels: Array<string>, // 可选的X轴标签
  title: String，            // 可选图表标题
});
```

### 上面的是你前端原始的数据结构，我都没有chartId，但第一个字段总是chart_type

给出一个实例
```
"[{'chart_type': 'pie', 'pieData': [{'name': '视觉组', 'value': 47}, {'name': '机械组', 'value': 43}, {'name': '电控组', 'value': 126}, {'name': '运营组', 'value': 36}, {'name': 'AI组', 'value': 36}, {'name': '软件组', 'value': 24}], 'title': 'Data'}]\n\n利用这些数据制作一个饼图，将有助于清晰展示各个分组在整体中的比例分布，有利于团队资源管理和决策。如需更多分析，请随时告知。"
```
被包在"``````"里，且后面有个\n\n(不一定有)


### 错误/error
```python
{
  "error": "错误信息",
  "chart_type": "请求的图表类型",
  "table": "请求的表名",
  "value_type": "请求的分析字段",
  "time_range": {
    "start": "请求的开始日期",
    "end": "请求的结束日期"
  }
}
```
</div>

### 错误码
# API请求与错误码对应表

## `/api/chat` POST请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 聊天请求处理成功 |
| 服务响应超时 | 504 | 处理请求超时，建议用户稍后重试 |
| 处理过程中出现错误 | 500 | 内部服务器处理错误 |
| LLM响应中包含错误字段 | 500 | 底层模型处理失败 |

## `/api/sessions/{session_id}/messages` GET请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 成功获取会话消息 |
| 会话不存在 | 404 | 未明确定义，但逻辑上应返回404 |

## `/api/init` POST请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 成功初始化智能体配置 |
| 配置错误 | 400 | 未明确定义，但配置错误应返回400 |

## `/api/sessions/{session_id}` DELETE请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 会话成功删除 |
| 会话不存在 | 404 | 未找到指定会话 |
| 删除过程错误 | 500 | 删除会话失败 |

## `/health` GET请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 服务正常 | 200 | 服务健康状态良好 |

## `/api/sessions` GET请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 成功获取指定会话数据 |
| 缺少session_id | 400 | 请求头中必须包含session_id |
| 获取数据失败 | 500 | 获取会话数据失败 |

## `/api/sessions/list` GET请求

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 成功 | 200 | 成功获取所有会话列表 |
| 获取列表失败 | 500 | 获取会话列表失败 |

## WebSocket `/api/chat/stream`（被注释掉的功能）

| 情况 | 错误码 | 描述 |
|------|--------|------|
| 连接成功 | - | 建立WebSocket连接 |
| 消息为空 | - | 返回错误JSON但无HTTP状态码 |
| 连接断开 | - | WebSocket断开连接处理 |