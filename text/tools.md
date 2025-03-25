# `chart.py` 详细说明文档

## 概述

`chart.py` 是一个综合性的数据可视化工具，专门为 tarsgo 数据库设计，能够生成多种类型的图表来分析和展示数据。该程序可以连接到 MySQL 数据库，提取数据，并使用 Matplotlib 和 Seaborn 库创建各种可视化图表，帮助用户理解数据模式和趋势。

## 功能特点

1. **多种图表类型**：支持创建折线图、柱状图、饼图、散点图、热力图、箱线图、雷达图等多种可视化图表
2. **灵活的数据查询**：可以自定义 SQL 查询，以从数据库中提取特定范围的数据
3. **自动格式化**：图表自动配置适当的标题、标签和颜色
4. **中文支持**：完全支持中文字符的显示
5. **可定制的输出**：可以调整图表尺寸、分辨率和保存格式
6. **图表组合**：支持在同一个图表中组合多种数据或创建子图

## 安装要求

要运行 `chart.py`，您需要安装以下依赖项：

```bash
pip install mysql-connector-python pandas matplotlib seaborn numpy
```

## 图表类型和功能

### 1. 物资使用趋势折线图

```python
def plot_material_usage_trend(start_date, end_date, top_n=5):
    """
    绘制指定时间段内物资使用趋势的折线图
    
    参数:
    start_date (str): 开始日期，格式为 'YYYY-MM-DD'
    end_date (str): 结束日期，格式为 'YYYY-MM-DD'
    top_n (int): 显示使用次数最多的前N种物资
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个折线图，显示一段时间内最常用的物资的使用频率变化。

### 2. 物资类别分布饼图

```python
def plot_material_category_pie():
    """
    绘制物资类别分布饼图
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个饼图，显示不同类别物资的分布比例。

### 3. 部门物资使用情况柱状图

```python
def plot_department_usage_bar(period='month'):
    """
    绘制各部门物资使用情况的柱状图
    
    参数:
    period (str): 统计周期，可选 'week', 'month', 'quarter', 'year'
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个柱状图，比较不同部门/组别的物资使用情况。

### 4. 用户活跃度热力图

```python
def plot_user_activity_heatmap(year):
    """
    绘制用户活跃度热力图
    
    参数:
    year (int): 要分析的年份
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个热力图，显示一年中不同月份和星期几的用户活跃度。

### 5. 签到时长分布直方图

```python
def plot_signin_duration_histogram():
    """
    绘制签到时长分布直方图
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个直方图，显示用户签到时长的分布情况。

### 6. 物资进出库对比堆叠柱状图

```python
def plot_inout_stacked_bar(last_n_months=6):
    """
    绘制物资进出库对比堆叠柱状图
    
    参数:
    last_n_months (int): 分析最近几个月的数据
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个堆叠柱状图，对比显示最近几个月的物资入库和出库情况。

### 7. 用户组人数分布雷达图

```python
def plot_user_group_radar():
    """
    绘制各用户组人数分布雷达图
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个雷达图，显示不同用户组/技术组的人数分布。

### 8. 物资价值箱线图

```python
def plot_material_price_boxplot():
    """
    绘制不同类别物资价值的箱线图
    
    返回:
    str: 保存的图片文件名
    """
```

此函数生成一个箱线图，显示不同类别物资价格的分布和异常值。

### 9. 地理位置散点图

```python
def plot_user_location_scatter():
    """
    绘制用户地理位置分布散点图
    
    返回:
    str: 保存的图片文件名
    """
```

此函数创建一个散点图，显示用户地理位置的分布情况（基于地址信息）。

## 函数组合示例

### 创建物资进出库和价格趋势组合图

```python
def create_material_combination_chart(material_name, last_n_months=12):
    """
    创建特定物资的进出库量和价格趋势的组合图
    
    参数:
    material_name (str): 物资名称
    last_n_months (int): 分析最近几个月的数据
    
    返回:
    str: 保存的图片文件名
    """
```

此函数创建一个组合图表，同时显示物资的进出库数量和价格变化趋势。

## 使用示例

以下是如何使用 `chart.py` 的示例：

```python
# 导入模块
from chart import (plot_material_usage_trend, plot_material_category_pie,
                   plot_department_usage_bar, plot_user_activity_heatmap)

# 生成一年内物资使用趋势图
trend_img = plot_material_usage_trend('2024-01-01', '2024-12-31', top_n=10)
print(f"趋势图已保存为: {trend_img}")

# 生成物资类别分布饼图
pie_img = plot_material_category_pie()
print(f"饼图已保存为: {pie_img}")

# 生成月度部门使用情况柱状图
bar_img = plot_department_usage_bar(period='month')
print(f"柱状图已保存为: {bar_img}")

# 生成2024年用户活跃度热力图
heatmap_img = plot_user_activity_heatmap(2024)
print(f"热力图已保存为: {heatmap_img}")
```

## 配置说明

在 `chart.py` 的开头部分，您可以调整以下配置：

```python
# 数据库连接配置
DB_CONFIG = {
    'user': 'your_username',
    'password': 'your_password',
    'host': 'localhost',
    'database': 'tarsgo',
    'raise_on_warnings': True
}

# 图表样式配置
CHART_STYLE = {
    'figsize': (12, 8),        # 图表尺寸
    'dpi': 300,                # 分辨率
    'fontsize': 12,            # 字体大小
    'title_fontsize': 16,      # 标题字体大小
    'save_format': 'png',      # 保存格式
    'color_palette': 'viridis' # 颜色主题
}

# 中文字体配置
FONT_PATH = r"C:\Windows\Fonts\simhei.ttf"  # Windows系统
# FONT_PATH = r"/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"  # Linux系统
# FONT_PATH = r"/System/Library/Fonts/PingFang.ttc"  # MacOS系统
```

您可以根据自己的环境和需求调整这些配置。

## 错误处理

`chart.py` 包含完善的错误处理机制，对于常见错误会提供有用的错误消息：

- 数据库连接错误
- 查询执行错误
- 空数据集处理
- 图表生成异常

当发生错误时，程序会输出详细的错误信息，并在可能的情况下继续执行。

## 扩展功能

`chart.py` 设计为可扩展的，您可以通过以下方式添加新功能：

1. 添加新的图表类型函数
2. 修改现有查询以获取不同的数据
3. 调整图表样式和格式
4. 添加交互式功能（如需要）

## 最佳实践

- 对于大型数据集，考虑在查询中添加 LIMIT 子句
- 为了更好的可视化效果，限制图表中显示的类别或项目数量
- 使用有意义的文件名保存图表
- 定期更新分析以反映最新数据

## 后续开发计划

- 添加交互式图表支持
- 实现自动报告生成功能
- 添加更多高级图表类型
- 支持导出为其他格式（如PDF报告）
- 添加数据预处理和清洗功能

---

如有任何问题或建议，请联系开发团队。