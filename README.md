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
config.json的mongodb格式和mysql格式如[config.json-mongodb版](./sample/mongodb_config.json)，[config.json-mysql版](./sample/config.json)
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
  "status": "healthy"
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

#### 错误/error
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