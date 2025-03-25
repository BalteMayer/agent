import mysql.connector
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import calendar
import matplotlib.font_manager as fm
from matplotlib.font_manager import FontProperties
from wordcloud import WordCloud
import jieba
from sklearn.preprocessing import MinMaxScaler
import matplotlib.ticker as mticker
import datetime


# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

# 数据库连接配置
config = {
    'user': 'BALTE',
    'password': 'your_new_password',
    'host': 'localhost',
    'database': 'tarsgo',
    'raise_on_warnings': True
}


def connect_to_database():
    """连接到MySQL数据库"""
    try:
        conn = mysql.connector.connect(**config)
        print("成功连接到MySQL数据库")
        return conn
    except mysql.connector.Error as err:
        print(f"连接到MySQL数据库失败: {err}")
        return None


def execute_query(query, params=None):
    """执行SQL查询并返回结果"""
    conn = connect_to_database()
    if not conn:
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)

        results = cursor.fetchall()
        return results
    except mysql.connector.Error as err:
        print(f"查询执行失败: {err}")
        return None
    finally:
        cursor.close()
        conn.close()


# ======== 1. 折线图绘制函数 ========

def plot_sign_in_trend(start_date, end_date):
    """
    绘制一段时间内的每日签到人数趋势折线图

    参数:
        start_date (str): 开始日期，格式为 'YYYY-MM-DD'
        end_date (str): 结束日期，格式为 'YYYY-MM-DD'
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    save_path = f"data/sign_in_trend/sign_in_trend_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    query = """
    SELECT DATE(signin) as date, COUNT(*) as count
    FROM sign_daytask
    WHERE DATE(signin) BETWEEN %s AND %s
    GROUP BY DATE(signin)
    ORDER BY DATE(signin)
    """

    results = execute_query(query, (start_date, end_date))

    if not results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 创建日期范围并填充缺失的日期
    date_range = pd.date_range(start=start_date, end=end_date)
    date_df = pd.DataFrame({'date': date_range})
    date_df['date'] = date_df['date'].dt.date

    df['date'] = pd.to_datetime(df['date']).dt.date
    full_df = pd.merge(date_df, df, on='date', how='left')
    full_df['count'] = full_df['count'].fillna(0)

    # 绘制折线图
    plt.figure(figsize=(12, 6))
    plt.plot(full_df['date'], full_df['count'], marker='o', linestyle='-', linewidth=2, markersize=6)

    # 设置图表属性
    plt.title(f'每日签到人数趋势 ({start_date} 至 {end_date})', fontsize=16)
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('签到人数', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)

    # 设置x轴日期格式
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=3))
    plt.gcf().autofmt_xdate()

    # 添加数据标签
    for x, y in zip(full_df['date'], full_df['count']):
        if y > 0:  # 只标注有签到的日期
            plt.text(x, y + 0.5, f'{int(y)}', ha='center', va='bottom', fontsize=9)

    # 添加平均线
    avg = full_df['count'].mean()
    plt.axhline(y=avg, color='r', linestyle='--', alpha=0.7)
    plt.text(full_df['date'].iloc[-1], avg, f'平均: {avg:.1f}',
             ha='right', va='bottom', color='r', fontsize=10)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()
    return save_path


def plot_member_activity(top_n=10, time_period='month'):
    """
    绘制成员活跃度折线图，显示不同时间段内的积累活跃时间

    参数:
        top_n (int): 显示前N名活跃成员
        time_period (str): 时间段类型，可选 'week', 'month', 'quarter'
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    save_path = f"data/member_activity/member_activity_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    # 获取当前日期
    now = datetime.now()

    # 根据时间段类型计算起始日期
    if time_period == 'week':
        # 最近4周的数据
        weeks = 4
        start_date = (now - timedelta(days=weeks * 7)).strftime('%Y-%m-%d')
        period_label = '周'
        date_format = '%Y-%m-%d'
        group_format = '%Y-%U'  # 年-周
    elif time_period == 'quarter':
        # 最近4个季度的数据
        quarters = 4
        month = now.month - (now.month - 1) % 3  # 当前季度的第一个月
        start_date = (datetime(now.year - 1 if month > 9 else now.year,
                               (month - 9) % 12 + 1 if month > 9 else month + 3, 1))
        period_label = '季度'
        date_format = '%Y-%m'
        group_format = '%Y-%m'  # 使用年-月，稍后会手动分组为季度
    else:  # 默认为month
        # 最近6个月的数据
        months = 6
        start_date = (datetime(now.year if now.month > months else now.year - 1,
                               (now.month - months) % 12 + 1 if now.month > months else now.month + 12 - months, 1))
        period_label = '月'
        date_format = '%Y-%m'
        group_format = '%Y-%m'  # 年-月

    # 格式化起始日期
    if isinstance(start_date, str):
        start_date_str = start_date
    else:
        start_date_str = start_date.strftime('%Y-%m-%d')

    # 获取最活跃的N名成员
    query_active = """
    SELECT nickname, SUM(CAST(totaltime AS UNSIGNED)) as total_minutes
    FROM sign_daytask
    WHERE signin >= %s
    GROUP BY nickname
    ORDER BY total_minutes DESC
    LIMIT %s
    """

    active_members = execute_query(query_active, (start_date_str, top_n))

    if not active_members:
        print("没有查询到数据")
        return

    # 获取这些成员在各时间段的活跃数据
    member_names = [member['nickname'] for member in active_members]
    placeholders = ', '.join(['%s'] * len(member_names))

    query_timeseries = f"""
    SELECT nickname, DATE(signin) as date, SUM(CAST(totaltime AS UNSIGNED)) as minutes
    FROM sign_daytask
    WHERE signin >= %s AND nickname IN ({placeholders})
    GROUP BY nickname, DATE(signin)
    ORDER BY nickname, DATE(signin)
    """

    params = [start_date_str] + member_names
    time_data = execute_query(query_timeseries, params)

    if not time_data:
        print("没有查询到时间序列数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(time_data)
    df['date'] = pd.to_datetime(df['date'])

    # 根据不同的时间段进行分组
    if time_period == 'week':
        df['period'] = df['date'].dt.strftime('%Y-%U')
        # 添加周标签
        period_mapping = {}
        for period in df['period'].unique():
            year, week = period.split('-')
            period_mapping[period] = f"{year}年第{week}周"
        df['period_label'] = df['period'].map(period_mapping)
    elif time_period == 'quarter':
        # 计算季度
        df['month'] = df['date'].dt.month
        df['quarter'] = ((df['date'].dt.month - 1) // 3 + 1).astype(int)
        df['period'] = df['date'].dt.strftime('%Y') + '-Q' + df['quarter'].astype(str)
        df['period_label'] = df.apply(lambda x: f"{x['date'].year}年Q{x['quarter']}", axis=1)
    else:  # month
        df['period'] = df['date'].dt.strftime('%Y-%m')
        df['period_label'] = df['date'].dt.strftime('%Y年%m月')

    # 按成员和时间段分组求和
    grouped = df.groupby(['nickname', 'period', 'period_label'])['minutes'].sum().reset_index()

    # 确保所有时间段都存在
    all_periods = sorted(grouped['period'].unique())
    all_period_labels = {}
    for _, row in grouped[['period', 'period_label']].drop_duplicates().iterrows():
        all_period_labels[row['period']] = row['period_label']

    # 创建完整数据集
    result = []
    for member in member_names:
        for period in all_periods:
            row = grouped[(grouped['nickname'] == member) & (grouped['period'] == period)]
            if len(row) > 0:
                result.append({
                    'nickname': member,
                    'period': period,
                    'period_label': all_period_labels[period],
                    'minutes': row['minutes'].values[0]
                })
            else:
                result.append({
                    'nickname': member,
                    'period': period,
                    'period_label': all_period_labels[period],
                    'minutes': 0
                })

    full_df = pd.DataFrame(result)

    # 计算每个成员的总活跃时间（用于排序和标注）
    member_totals = full_df.groupby('nickname')['minutes'].sum().reset_index()
    member_totals = member_totals.sort_values('minutes', ascending=False)

    # 为了更好的可视化，将分钟转换为小时
    full_df['hours'] = full_df['minutes'] / 60

    # 绘制折线图
    plt.figure(figsize=(14, 8))

    # 颜色映射
    colors = plt.cm.tab10.colors

    # 按总活跃时间排序的成员列表
    sorted_members = member_totals['nickname'].tolist()

    for i, member in enumerate(sorted_members):
        member_data = full_df[full_df['nickname'] == member].sort_values('period')
        plt.plot(member_data['period_label'], member_data['hours'],
                 marker='o', label=member, color=colors[i % len(colors)],
                 linewidth=2, markersize=6)

    # 设置图表属性
    periods_type = {
        'week': '周',
        'month': '月',
        'quarter': '季度'
    }
    plt.title(f'成员活跃度趋势图 (按{periods_type.get(time_period, "月")})', fontsize=16)
    plt.xlabel(f'{period_label}', fontsize=12)
    plt.ylabel('活跃时间（小时）', fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()
    return save_path


# ======== 2. 柱状图绘制函数 ========

def plot_group_member_count():
    """
    绘制各组成员数量柱状图

    参数:
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    save_path = f"data/group_member_count/group_member_count_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    # 查询各组成员数量
    query = """
    SELECT jlugroup, COUNT(*) as count
    FROM sign_person
    GROUP BY jlugroup
    ORDER BY count DESC
    """

    results = execute_query(query)

    if not results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 绘制柱状图
    plt.figure(figsize=(12, 7))
    bars = plt.bar(df['jlugroup'], df['count'], color=plt.cm.tab10.colors)

    # 设置图表属性
    plt.title('各组成员数量统计', fontsize=16)
    plt.xlabel('组别', fontsize=14)
    plt.ylabel('成员数量', fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)

    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                 f'{int(height)}',
                 ha='center', va='bottom', fontsize=12)

    # 添加总计
    total = df['count'].sum()
    plt.text(len(df) / 2, max(df['count']) * 1.1, f'总计: {total}人',
             ha='center', va='bottom', fontsize=14, color='red',
             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=30, ha='right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()
    return save_path


def plot_material_consumption(top_n=10, period=None, save_path=None):
    """
    绘制物资消耗量柱状图，显示消耗最多的前N种物资

    参数:
        top_n (int): 显示前N种消耗最多的物资
        period (tuple): 时间段，格式为('YYYY-MM-DD', 'YYYY-MM-DD')，若为None则查询所有数据
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    # 构建查询条件
    where_clause = ""
    params = []

    if period:
        where_clause = "WHERE outbound_date BETWEEN %s AND %s"
        params = list(period)

    # 查询物资消耗量
    query = f"""
    SELECT item_name, SUM(quantity) as total_quantity, quantity_unit
    FROM Material_Outbound
    {where_clause}
    GROUP BY item_name, quantity_unit
    ORDER BY total_quantity DESC
    LIMIT %s
    """

    params.append(top_n)
    results = execute_query(query, params)

    if not results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 为了展示，将物资名称和单位合并
    df['item_with_unit'] = df.apply(lambda x: f"{x['item_name']} ({x['quantity_unit']})", axis=1)

    # 绘制水平柱状图
    plt.figure(figsize=(12, 8))
    bars = plt.barh(df['item_with_unit'], df['total_quantity'], color=plt.cm.viridis(np.linspace(0, 0.8, len(df))))

    # 设置图表属性
    title = '物资消耗量统计 (前{}种)'.format(top_n)
    if period:
        title += f" ({period[0]} 至 {period[1]})"
    plt.title(title, fontsize=16)
    plt.xlabel('消耗数量', fontsize=14)
    plt.ylabel('物资名称', fontsize=14)
    plt.grid(True, axis='x', linestyle='--', alpha=0.7)

    # 添加数据标签
    for i, bar in enumerate(bars):
        width = bar.get_width()
        plt.text(width + (max(df['total_quantity']) * 0.01), bar.get_y() + bar.get_height() / 2.,
                 f'{int(width)}',
                 ha='left', va='center', fontsize=11)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()


def plot_group_activity_comparison(start_date=None, end_date=None, by='hours', save_path=None):
    """
    绘制不同组别活跃度对比柱状图

    参数:
        start_date (str, optional): 开始日期，格式为 'YYYY-MM-DD'
        end_date (str, optional): 结束日期，格式为 'YYYY-MM-DD'
        by (str): 比较方式，可选 'hours'(活跃时长) 或 'count'(签到人次)
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    # 构建查询条件
    where_clause = ""
    params = []

    if start_date and end_date:
        where_clause = "WHERE DATE(signin) BETWEEN %s AND %s"
        params = [start_date, end_date]

    # 根据比较方式选择查询内容
    if by == 'hours':
        query = f"""
        SELECT jlugroup, SUM(CAST(totaltime AS UNSIGNED))/60 as total_hours
        FROM sign_daytask
        {where_clause}
        GROUP BY jlugroup
        ORDER BY total_hours DESC
        """
        value_column = 'total_hours'
        value_label = '活跃时长（小时）'

    else:  # count
        query = f"""
        SELECT jlugroup, COUNT(*) as sign_count
        FROM sign_daytask
        {where_clause}
        GROUP BY jlugroup
        ORDER BY sign_count DESC
        """
        value_column = 'sign_count'
        value_label = '签到人次'

    results = execute_query(query, params)

    if not results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 绘制柱状图
    plt.figure(figsize=(12, 7))

    # 使用渐变色
    colors = plt.cm.YlOrRd(np.linspace(0.3, 0.9, len(df)))

    bars = plt.bar(df['jlugroup'], df[value_column], color=colors)

    # 设置图表属性
    title = '各组活跃度对比'
    if start_date and end_date:
        title += f" ({start_date} 至 {end_date})"
    plt.title(title, fontsize=16)
    plt.xlabel('组别', fontsize=14)
    plt.ylabel(value_label, fontsize=14)
    plt.grid(True, axis='y', linestyle='--', alpha=0.7)

    # 添加数据标签
    for bar in bars:
        height = bar.get_height()
        value_text = f'{int(height)}' if by == 'count' else f'{height:.1f}'
        plt.text(bar.get_x() + bar.get_width() / 2., height + (max(df[value_column]) * 0.01),
                 value_text,
                 ha='center', va='bottom', fontsize=11)

    # 添加组别人数标注 (从sign_person表获取)
    group_counts_query = """
    SELECT jlugroup, COUNT(*) as member_count
    FROM sign_person
    GROUP BY jlugroup
    """

    group_counts = execute_query(group_counts_query)
    if group_counts:
        group_count_df = pd.DataFrame(group_counts)
        # 合并数据
        merged_df = pd.merge(df, group_count_df, on='jlugroup', how='left')

        # 在柱子下方添加人数标注
        for i, row in merged_df.iterrows():
            plt.text(i, -max(df[value_column]) * 0.03,
                     f"{int(row['member_count'])}人",
                     ha='center', va='top', fontsize=9, color='blue')

    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=30, ha='right')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()


def plot_stacked_material_movement(period=('2023-01-01', '2023-12-31'), top_n=8, save_path=None):
    """
    绘制物资出入库堆叠柱状图，对比不同物资的入库和出库数量

    参数:
        period (tuple): 时间段，格式为('YYYY-MM-DD', 'YYYY-MM-DD')
        top_n (int): 显示活动最频繁的前N种物资
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    # 查询入库数据
    inbound_query = """
    SELECT item_name, SUM(quantity) as total_quantity
    FROM Material_Inbound
    WHERE entry_date BETWEEN %s AND %s
    GROUP BY item_name
    """

    # 查询出库数据
    outbound_query = """
    SELECT item_name, SUM(quantity) as total_quantity
    FROM Material_Outbound
    WHERE outbound_date BETWEEN %s AND %s
    GROUP BY item_name
    """

    inbound_results = execute_query(inbound_query, period)
    outbound_results = execute_query(outbound_query, period)

    if not inbound_results and not outbound_results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    inbound_df = pd.DataFrame(inbound_results) if inbound_results else pd.DataFrame(
        columns=['item_name', 'total_quantity'])
    outbound_df = pd.DataFrame(outbound_results) if outbound_results else pd.DataFrame(
        columns=['item_name', 'total_quantity'])

    # 重命名列以区分入库和出库
    inbound_df = inbound_df.rename(columns={'total_quantity': 'inbound_quantity'})
    outbound_df = outbound_df.rename(columns={'total_quantity': 'outbound_quantity'})

    # 合并数据
    merged_df = pd.merge(inbound_df, outbound_df, on='item_name', how='outer').fillna(0)

    # 计算总活动量（入库+出库）并排序
    merged_df['total_activity'] = merged_df['inbound_quantity'] + merged_df['outbound_quantity']
    merged_df = merged_df.sort_values('total_activity', ascending=False).head(top_n)

    # 绘制堆叠柱状图
    fig, ax = plt.subplots(figsize=(14, 8))

    # 绘制入库和出库数据
    inbound_bars = ax.bar(merged_df['item_name'], merged_df['inbound_quantity'],
                          color='green', alpha=0.7, label='入库数量')
    outbound_bars = ax.bar(merged_df['item_name'], -merged_df['outbound_quantity'],
                           color='red', alpha=0.7, label='出库数量')

    # 设置图表属性
    ax.set_title(f'物资出入库对比 ({period[0]} 至 {period[1]})', fontsize=16)
    ax.set_xlabel('物资名称', fontsize=14)
    ax.set_ylabel('数量', fontsize=14)
    ax.legend(fontsize=12)
    ax.grid(True, axis='y', linestyle='--', alpha=0.7)

    # 添加数据标签
    for bar in inbound_bars:
        height = bar.get_height()
        if height > 0:
            ax.text(bar.get_x() + bar.get_width() / 2., height + 0.1,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=10, color='green')

    for bar in outbound_bars:
        height = bar.get_height()
        if height < 0:
            ax.text(bar.get_x() + bar.get_width() / 2., height - 0.1,
                    f'{int(abs(height))}',
                    ha='center', va='top', fontsize=10, color='red')

    # 旋转x轴标签以避免重叠
    plt.xticks(rotation=45, ha='right')

    # 添加水平零线
    ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)

    # 设置y轴刻度格式为绝对值
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: f'{abs(x):.0f}'))

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()


# ======== 3. 饼图绘制函数 ========

def plot_gender_distribution(table='Data', save_path=None):
    """
    绘制性别分布饼图

    参数:
        table (str): 数据表名，可选 'Data', 'members', 或 'SignUpData'
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    # 根据表名选择性别字段
    field_map = {
        'Data': 'sex',
        'members': 'gender',
        'SignUpData': 'sex'
    }

    sex_field = field_map.get(table, 'sex')

    # 构建查询
    query = f"""
    SELECT {sex_field} as gender, COUNT(*) as count
    FROM {table}
    WHERE {sex_field} IS NOT NULL AND {sex_field} != ''
    GROUP BY {sex_field}
    """

    results = execute_query(query)

    if not results:
        print("没有查询到数据")
        return

    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 确保性别值是标准的"男"/"女"
    gender_map = {
        '男': '男', 'male': '男', 'M': '男', 'm': '男',
        '女': '女', 'female': '女', 'F': '女', 'f': '女'
    }

    df['gender'] = df['gender'].map(lambda x: gender_map.get(x, x))

    # 按性别分组汇总
    grouped = df.groupby('gender')['count'].sum().reset_index()

    # 绘制饼图
    plt.figure(figsize=(10, 8))

    # 设置颜色和突出显示
    colors = ['#4E79A7', '#F28E2B']  # 蓝色和橙色
    explode = [0.05] * len(grouped)  # 所有部分稍微突出

    wedges, texts, autotexts = plt.pie(
        grouped['count'],
        labels=grouped['gender'],
        autopct='%1.1f%%',
        startangle=90,
        explode=explode,
        colors=colors,
        shadow=True,
        textprops={'fontsize': 14}
    )

    # 设置自动文本标签的样式
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(12)
        autotext.set_fontweight('bold')

    # 添加数量标注
    for i, (wedge, count) in enumerate(zip(wedges, grouped['count'])):
        angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
        x = wedge.r * 0.6 * np.cos(np.deg2rad(angle))
        y = wedge.r * 0.6 * np.sin(np.deg2rad(angle))
        plt.text(x, y, f"{int(count)}人", ha='center', va='center', fontsize=12, fontweight='bold', color='white')

    # 设置图表属性
    plt.title(f'{table}表 - 性别分布', fontsize=16, pad=20)

    # 添加总计
    total = grouped['count'].sum()
    plt.text(0, -1.2, f'总计: {total}人', ha='center', fontsize=14,
             bbox=dict(facecolor='white', alpha=0.8, boxstyle='round,pad=0.5'))

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"图表已保存至: {save_path}")
    else:
        plt.show()

    plt.close()



def plot_material_category_distribution():
    """
    绘制物资类别分布饼图

    参数:
        save_path (str, optional): 图表保存路径，若为None则显示图表

    返回:
        None
    """
    save_path = f"data/material_distribution/material_distribution_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
    # 查询物资类别分布
    query = """
    SELECT mc.category, COUNT(ms.ID) as count
    FROM Material_Store ms
    JOIN Material_Category mc ON ms.category = mc.ID
    GROUP BY mc.category
    ORDER BY count DESC
    """

    results = execute_query(query)

    if not results:
        print("没有查询到数据")
        return
    
    # 转换为DataFrame
    df = pd.DataFrame(results)

    # 绘制饼图
    plt.figure(figsize=(12, 9))

    # 设置颜色映射和突出显示
    colors = plt.cm.Paired(np.arange(len(df)) / len(df))

    # 计算突出显示值 - 第一个部分最突出
    explode = np.zeros(len(df))
    if len(explode) > 10:
        explode[0] = 0.01
    # 绘制饼图和百分比标签
    wedges, texts, autotexts = plt.pie(
        df['count'],
        labels=df['category'],
        autopct='%1.1f%%',
        startangle=90,
        explode=explode,
        colors=colors,
        shadow=False,
        textprops={'fontsize': 12},
        wedgeprops={'edgecolor': 'white', 'linewidth': 1},  # 添加这一行来移除缝隙
        center=(0, 0)  # 确保居中对齐
    )
    
    # 设置自动文本标签的样式
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(10)
        autotext.set_fontweight('bold')

    # 为小部分添加引线
    small_wedges = [wedge for i, wedge in enumerate(wedges) if df['count'].iloc[i] / df['count'].sum() < 0.05]
    for wedge in small_wedges:
        angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
        x = np.cos(np.deg2rad(angle))
        y = np.sin(np.deg2rad(angle))
        plt.plot([x * 0.8, x * 1.3], [y * 0.8, y * 1.3], 'k-')
    
    # 添加数量标注
    for i, (wedge, count) in enumerate(zip(wedges, df['count'])):
        if df['count'].iloc[i] / df['count'].sum() >= 0.05:  # 只为较大部分添加标注
            angle = (wedge.theta2 - wedge.theta1) / 2.0 + wedge.theta1
            x = wedge.r * 0.7 * np.cos(np.deg2rad(angle))
            y = wedge.r * 0.7 * np.sin(np.deg2rad(angle))
            plt.text(x, y, f"{int(count)}项", ha='center', va='center', fontsize=10, fontweight='bold', color='white')
    
    # 设置图表属性
    plt.title('物资类别分布', fontsize=16, pad=20)
    
    # 添加图例
    plt.legend(wedges, df['category'], title="物资类别", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))
    
    # 添加总计
    total = df['count'].sum()
    plt.text(0, -1.2, f'总物资项: {total}项', ha='center', fontsize=12, fontweight='bold')
    
    # 调整布局以确保所有元素可见
    plt.tight_layout()
    
    # 保存或显示图表

    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    plt.close()
    


    return save_path