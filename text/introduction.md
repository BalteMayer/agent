# 数据库介绍文档 / Database Introduction Document

## 概述 / Overview

本数据库（tarsgo）是一个综合性管理系统，主要用于管理组织成员信息、物资管理、签到系统和文章发布等功能。数据库包含多个相互关联的表，用于存储不同类型的数据。

This database (tarsgo) is a comprehensive management system, primarily used for managing organization members, materials, sign-in systems, and article publishing functions. The database contains multiple interconnected tables for storing different types of data.

## 数据库结构 / Database Structure

数据库共包含17个表，可分为以下几个主要功能模块：

The database contains 17 tables, which can be divided into the following main functional modules:

1. **用户管理 / User Management**
   - users
   - members
   - data
   - tarsgo_user
   - tarsgo_auth
   - Material_User

2. **物资管理 / Material Management**
   - Material_Category
   - Material_Inbound
   - Material_Outbound
   - Material_Log
   - Material_Store
   - Material_Usage
   - Material_site
   - Financial_Log

3. **签到系统 / Sign-in System**
   - sign_daytask
   - sign_person

4. **内容管理 / Content Management**
   - Article
   - SignUpData
   - options

## 表结构详细说明 / Detailed Table Structure

### 1. 用户管理模块 / User Management Module

#### 1.1 users 表 / users Table

基本用户表，存储基础用户信息。

Basic user table, storing fundamental user information.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| id | bigint(20) | 主键 ID / Primary Key ID |
| created_at | datetime(3) | 创建时间 / Creation Time |
| updated_at | datetime(3) | 更新时间 / Update Time |
| deleted_at | datetime(3) | 删除时间 / Deletion Time |
| username | varchar(191) | 用户名 / Username |
| email | varchar(191) | 电子邮件 / Email |
| password | varchar(191) | 密码（加密） / Password (encrypted) |

**样例数据 / Sample Data:**
```
{
  "id": 1,
  "created_at": "2023-05-15 09:30:00",
  "updated_at": "2023-06-01 14:22:30",
  "deleted_at": null,
  "username": "liuwei2023",
  "email": "liuwei2023@example.com",
  "password": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
}
```

#### 1.2 members 表 / members Table

团队成员表，存储更详细的成员信息。

Team members table, storing more detailed member information.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| id | bigint(20) | 主键 ID / Primary Key ID |
| name | varchar(100) | 姓名 / Name |
| gender | varchar(10) | 性别 / Gender |
| grade | varchar(20) | 年级 / Grade |
| group | varchar(50) | 组别 / Group |
| identity | varchar(50) | 身份 / Identity |
| branch | varchar(50) | 分支 / Branch |
| campus | varchar(50) | 校区 / Campus |
| major | varchar(100) | 专业 / Major |
| phone | varchar(20) | 电话 / Phone |
| email | varchar(100) | 电子邮件 / Email |
| qq | varchar(20) | QQ号 / QQ Number |
| we_chat | varchar(50) | 微信 / WeChat |
| created_at | datetime(3) | 创建时间 / Creation Time |
| updated_at | datetime(3) | 更新时间 / Update Time |

**样例数据 / Sample Data:**
```
{
  "id": 1,
  "name": "张明",
  "gender": "男",
  "grade": "2022",
  "group": "电控组",
  "identity": "正式队员",
  "branch": "主分支",
  "campus": "南湖校区",
  "major": "电子工程",
  "phone": "13812345678",
  "email": "zhangming@example.com",
  "qq": "123456789",
  "we_chat": "zhangming_wechat",
  "created_at": "2023-09-01 08:00:00",
  "updated_at": "2023-09-01 08:00:00"
}
```

#### 1.3 data 表 / data Table

扩展的用户数据表，包含更全面的个人信息。

Extended user data table, containing more comprehensive personal information.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| id | bigint(20) | 主键 ID / Primary Key ID |
| name | varchar(100) | 姓名 / Name |
| gender | varchar(10) | 性别 / Gender |
| grade | varchar(20) | 年级 / Grade |
| group | varchar(50) | 组别 / Group |
| identity | longtext | 身份 / Identity |
| branch | varchar(50) | 分支 / Branch |
| campus | varchar(50) | 校区 / Campus |
| major | varchar(100) | 专业 / Major |
| phone | longtext | 电话 / Phone |
| email | longtext | 电子邮件 / Email |
| qq | longtext | QQ号 / QQ Number |
| we_chat | varchar(50) | 微信 / WeChat |
| created_at | datetime(3) | 创建时间 / Creation Time |
| updated_at | datetime(3) | 更新时间 / Update Time |
| nickname | longtext | 昵称 / Nickname |
| IDcard | longtext | 身份证号 / ID Card |
| sex | longtext | 性别 / Sex |
| age | bigint(20) | 年龄 / Age |
| address | longtext | 地址 / Address |
| classification | longtext | 分类 / Classification |
| school | longtext | 学校 / School |
| subjects | longtext | 科目 / Subjects |
| wechat | longtext | 微信 / WeChat |
| webID | longtext | 网站ID / Web ID |
| jlugroup | longtext | 吉大组别 / JLU Group |
| study | longtext | 学习 / Study |
| state | longtext | 状态 / State |

**样例数据 / Sample Data:**
```
{
  "id": 1,
  "name": "王芳",
  "gender": "女",
  "grade": "2023",
  "group": "AI组",
  "identity": "预备队员",
  "branch": "研发分支",
  "campus": "前卫南区",
  "major": "人工智能",
  "phone": "13987654321",
  "email": "wangfang@example.com",
  "qq": "987654321",
  "we_chat": "wangfang_wechat",
  "created_at": "2023-10-15 14:30:00",
  "updated_at": "2023-11-01 09:45:00",
  "nickname": "小王",
  "IDcard": "210503199801234567",
  "sex": "女",
  "age": 23,
  "address": "吉林省长春市南关区",
  "classification": "2023",
  "school": "计算机学院",
  "subjects": "人工智能",
  "wechat": "wangfang_wechat",
  "webID": "JLU123456",
  "jlugroup": "AI组",
  "study": "本科",
  "state": "在队"
}
```

#### 1.4 tarsgo_user 表 / tarsgo_user Table

用户权限管理表，关联到权限等级。

User permission management table, linked to permission levels.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| username | varchar(50) | 用户名 / Username |
| password | varchar(50) | 密码 / Password |
| identity | varchar(50) | 身份 / Identity |
| status | int(11) | 状态 / Status |
| group | int(11) | 组别（外键，关联到 tarsgo_auth 表） / Group (foreign key, linked to tarsgo_auth table) |

**样例数据 / Sample Data:**
```
{
  "ID": 10,
  "username": "ai",
  "password": "e10adc3949ba59abbe56e057f20f883e",
  "identity": "AI组",
  "status": 0,
  "group": 1
}
```

#### 1.5 tarsgo_auth 表 / tarsgo_auth Table

权限等级定义表。

Permission level definition table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| role | varchar(50) | 角色名称 / Role Name |
| level | int(11) | 权限等级 / Permission Level |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "role": "组长",
  "level": 1
}
```

#### 1.6 Material_User 表 / Material_User Table

物资管理系统的用户表。

User table for the material management system.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| username | varchar(255) | 用户名 / Username |
| password | varchar(255) | 密码 / Password |
| nickname | varchar(255) | 昵称 / Nickname |
| flag | int(11) | 是否启用 / Enabled Flag |

**样例数据 / Sample Data:**
```
{
  "ID": 22,
  "username": "kaguya",
  "password": "8fe5fc78a95fbde89b7fa300be95fb47",
  "nickname": "四宫辉夜",
  "flag": 0
}
```

### 2. 物资管理模块 / Material Management Module

#### 2.1 Material_Category 表 / Material_Category Table

物资分类表。

Material category table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| category | varchar(255) | 物资类别 / Material Category |
| is_consumable | int(11) | 是否为消耗品 / Is Consumable |
| is_valuable | int(11) | 是否为贵重物品 / Is Valuable |

**样例数据 / Sample Data:**
```
{
  "ID": 3,
  "category": "贵重物品",
  "is_consumable": 0,
  "is_valuable": 1
}
```

#### 2.2 Material_Inbound 表 / Material_Inbound Table

物资入库记录表。

Material inbound record table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| item_name | varchar(255) | 物资名称 / Item Name |
| category | int(11) | 物资类别（外键） / Category (foreign key) |
| stocker | varchar(255) | 入库人 / Stocker |
| quantity | int(11) | 物资数量 / Quantity |
| quantity_unit | varchar(255) | 数量单位 / Quantity Unit |
| site | int(11) | 所在位置（外键） / Location Site (foreign key) |
| purpose | int(11) | 物资用途（外键） / Purpose (foreign key) |
| entry_date | timestamp | 入库日期 / Entry Date |
| flag | int(11) | 审批状态 / Approval Status |
| approver | varchar(255) | 审批人 / Approver |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "item_name": "焊锡",
  "category": 1,
  "stocker": "测试人员",
  "quantity": 100,
  "quantity_unit": "个",
  "site": 1,
  "purpose": 1,
  "entry_date": "2023-07-14 04:29:32",
  "flag": 1,
  "approver": "姚秀玲"
}
```

#### 2.3 Material_Outbound 表 / Material_Outbound Table

物资出库记录表。

Material outbound record table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| item_name | varchar(255) | 物资名称 / Item Name |
| category | int(11) | 物资类别（外键） / Category (foreign key) |
| outbound_personnel | varchar(255) | 出库人 / Outbound Personnel |
| quantity | int(11) | 物资数量 / Quantity |
| quantity_unit | varchar(255) | 数量单位 / Quantity Unit |
| site | int(11) | 所在位置（外键） / Location Site (foreign key) |
| purpose | int(11) | 物资用途（外键） / Purpose (foreign key) |
| usage_description | longtext | 物资使用简述 / Usage Description |
| outbound_date | timestamp | 出库日期 / Outbound Date |
| flag | int(11) | 审批状态 / Approval Status |
| approver | varchar(255) | 审批人 / Approver |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "item_name": "杜邦线",
  "category": 1,
  "outbound_personnel": "邱钢",
  "quantity": 20,
  "quantity_unit": "根",
  "site": 1,
  "purpose": 1,
  "usage_description": "用于测试",
  "outbound_date": "2023-07-14 14:53:01",
  "flag": 1,
  "approver": "邱钢"
}
```

#### 2.4 Material_Log 表 / Material_Log Table

物资操作日志表。

Material operation log table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| item_name | varchar(255) | 物资名称 / Item Name |
| category | int(11) | 物资类别（外键） / Category (foreign key) |
| operator | varchar(255) | 操作者 / Operator |
| operation_type | int(11) | 操作类型 / Operation Type |
| operation_date | timestamp | 操作日期 / Operation Date |
| site | int(11) | 所在位置（外键） / Location Site (foreign key) |
| quantity | int(11) | 物资数量 / Quantity |
| quantity_unit | varchar(255) | 数量单位 / Quantity Unit |
| purpose | int(11) | 物资用途（外键） / Purpose (foreign key) |
| usage_description | longtext | 物资使用简述 / Usage Description |
| approver | varchar(255) | 审批人 / Approver |

**样例数据 / Sample Data:**
```
{
  "ID": 9,
  "item_name": "电源线",
  "category": 1,
  "operator": "杨瑞",
  "operation_type": 0,
  "operation_date": "2023-08-25 07:04:43",
  "site": 1,
  "quantity": 200,
  "quantity_unit": "根",
  "purpose": 1,
  "usage_description": "undefined",
  "approver": "QG"
}
```

#### 2.5 Material_Store 表 / Material_Store Table

物资库存表。

Material inventory table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| item_name | varchar(255) | 物资名称 / Item Name |
| category | int(11) | 物资类别（外键） / Category (foreign key) |
| quantity | int(11) | 物资数量 / Quantity |
| quantity_unit | varchar(25) | 物资单位 / Quantity Unit |
| site | int(11) | 所在位置（外键） / Location Site (foreign key) |
| purpose | int(11) | 物资用途（外键） / Purpose (foreign key) |

**样例数据 / Sample Data:**
```
{
  "ID": 6,
  "item_name": "锟斤拷锟斤拷",
  "category": 3,
  "quantity": 20,
  "quantity_unit": "糖",
  "site": 1,
  "purpose": 1
}
```

#### 2.6 Material_Usage 表 / Material_Usage Table

物资用途表。

Material usage table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| purpose | varchar(255) | 物资用途 / Material Purpose |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "purpose": "打RM比赛"
}
```

#### 2.7 Material_site 表 / Material_site Table

物资位置表。

Material location site table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| site | varchar(255) | 物资位置 / Material Site |

**样例数据 / Sample Data:**
```
{
  "ID": 2,
  "site": "南湖车库"
}
```

#### 2.8 Financial_Log 表 / Financial_Log Table

财务记录表。

Financial record table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| name | varchar(255) | 名称 / Name |
| model | varchar(255) | 型号 / Model |
| quantity | int(11) | 数量 / Quantity |
| unit | varchar(255) | 单位 / Unit |
| price | float | 单价 / Price |
| extra_price | float | 运费 / Extra Price |
| purchase_link | longtext | 购买链接 / Purchase Link |
| post_date | timestamp | 时间 / Post Date |
| purchaser | varchar(255) | A购人 / Purchaser |
| phone | varchar(255) | 联系方式 / Phone |
| campus | varchar(255) | 校区 / Campus |
| usage_description | longtext | 用途 / Usage Description |
| group_name | varchar(255) | 技术组 / Group Name |
| troop_type | varchar(255) | 兵种 / Troop Type |
| project | varchar(255) | 项目 / Project |
| remarks | longtext | 备注 / Remarks |

**样例数据 / Sample Data:**
```
{
  "ID": 222,
  "name": "紧定螺丝",
  "model": "M3*12 [50只]平端",
  "quantity": 1,
  "unit": "个",
  "price": 4.32,
  "extra_price": 0,
  "purchase_link": "https://detail.tmall.com/item.htm?[...省略]",
  "post_date": "2023-09-15 10:30:00",
  "purchaser": "张三",
  "phone": "13800138000",
  "campus": "南湖校区",
  "usage_description": "机器人维修",
  "group_name": "机械组",
  "troop_type": "步兵",
  "project": "RoboMaster比赛",
  "remarks": "急用"
}
```

### 3. 签到系统模块 / Sign-in System Module

#### 3.1 sign_daytask 表 / sign_daytask Table

每日签到记录表。

Daily sign-in record table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| nickname | varchar(255) | 昵称 / Nickname |
| school | varchar(255) | 学校 / School |
| jlugroup | varchar(255) | 组别 / JLU Group |
| identity | varchar(255) | 身份 / Identity |
| signin | varchar(255) | 签到时间 / Sign-in Time |
| signout | varchar(255) | 签退时间 / Sign-out Time |
| lasttime | varchar(255) | 最后时间 / Last Time |
| totaltime | varchar(255) | 总时间（分钟） / Total Time (minutes) |
| status | int(255) | 状态 / Status |

**样例数据 / Sample Data:**
```
{
  "ID": 177,
  "nickname": "王瀚毅",
  "school": "南湖校区",
  "jlugroup": "电控组",
  "identity": "正式队员",
  "signin": "2022-10-13 08:06:51",
  "signout": "2022-10-13 21:44:15",
  "lasttime": "13小时37分",
  "totaltime": "817",
  "status": 1
}
```

#### 3.2 sign_person 表 / sign_person Table

个人签到汇总表。

Personal sign-in summary table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| nickname | varchar(255) | 昵称 / Nickname |
| school | varchar(255) | 学校 / School |
| jlugroup | varchar(255) | 组别 / JLU Group |
| identity | varchar(255) | 身份 / Identity |
| totaltime | varchar(255) | 总时间（分钟） / Total Time (minutes) |

**样例数据 / Sample Data:**
```
{
  "ID": 243,
  "nickname": "常家玮",
  "school": "南湖校区",
  "jlugroup": "机械组",
  "identity": "正式队员",
  "totaltime": "8811"
}
```

### 4. 内容管理模块 / Content Management Module

#### 4.1 Article 表 / Article Table

文章内容表。

Article content table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| title | longtext | 标题 / Title |
| time | text | 时间 / Time |
| classification | text | 分类 / Classification |
| nickname | text | 昵称 / Nickname |
| content | longtext | 内容 / Content |
| images | longtext | 图片 / Images |

**样例数据 / Sample Data:**
```
{
  "ID": 19,
  "title": "南岭杏花节",
  "time": "2023-04-16",
  "classification": "活动",
  "nickname": "何佳悦 邢浩泽 赵天培 周昊燃",
  "content": "本次活动主要内容为...",
  "images": "https://example.com/images/1.jpg,https://example.com/images/2.jpg"
}
```

#### 4.2 SignUpData 表 / SignUpData Table

报名数据表。

Sign-up data table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| nickname | varchar(255) | 昵称 / Nickname |
| photo | varchar(255) | 照片 / Photo |
| sex | varchar(255) | 性别 / Sex |
| address | varchar(255) | 地址 / Address |
| region | varchar(255) | 区域 / Region |
| classification | varchar(255) | 分类 / Classification |
| school | varchar(255) | 学校 / School |
| subject | varchar(255) | 专业 / Subject |
| uid | varchar(255) | UID / User ID |
| qq | varchar(255) | QQ号 / QQ Number |
| phone | varchar(255) | 电话 / Phone |
| email | varchar(255) | 电子邮件 / Email |
| type_one | varchar(255) | 类型一 / Type One |
| flag_one | int(11) | 标志一 / Flag One |
| type_two | varchar(255) | 类型二 / Type Two |
| flag_two | int(11) | 标志二 / Flag Two |
| text_one | longtext | 文本一 / Text One |
| text_two | longtext | 文本二 / Text Two |
| text_three | longtext | 文本三 / Text Three |
| text_four | longtext | 文本四 / Text Four |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "nickname": "李香怡",
  "photo": "https://tarsgo.xf233.com/tarsgo_cloud_service/upload/Registration/1726968347594_3674915940.jpg",
  "sex": "女",
  "address": "江苏省丰县",
  "region": "南湖校区",
  "classification": "2024",
  "school": "通信工程学院",
  "subject": "通信工程",
  "uid": "123456",
  "qq": "123456789",
  "phone": "13812345678",
  "email": "lixiangyi@example.com",
  "type_one": "技术组",
  "flag_one": 1,
  "type_two": "兵种组",
  "flag_two": 0,
  "text_one": "对技术的理解...",
  "text_two": "个人经历...",
  "text_three": "加入的原因...",
  "text_four": "其他补充信息..."
}
```

#### 4.3 options 表 / options Table

系统配置表。

System configuration table.

| 字段 / Field | 类型 / Type | 描述 / Description |
|------------|------------|-------------------|
| ID | int(11) | 主键 ID / Primary Key ID |
| name | varchar(50) | 名称 / Name |
| data | longtext | 数据 / Data |
| flag | varchar(50) | 标志 / Flag |
| switch | int(11) | 开关 / Switch |

**样例数据 / Sample Data:**
```
{
  "ID": 1,
  "name": "SignUpConfig",
  "data": "73bfa31706",
  "flag": "{\"start\":1724860800000,\"end\":1727452800000}",
  "switch": 1
}
```

## 数据库关系 / Database Relationships

数据库中存在多个外键关联，主要包括：

The database contains multiple foreign key relationships, including:

1. Material_Inbound、Material_Outbound、Material_Log、Material_Store 表都通过外键关联到：
   - Material_Category（物资类别）
   - Material_Usage（物资用途）
   - Material_site（物资位置）

2. tarsgo_user 表通过 group 字段关联到 tarsgo_auth 表的 ID 字段。

## 总结 / Summary

本数据库设计涵盖了组织管理所需的多个方面，包括用户管理、物资管理、签到系统和内容管理。通过合理的表结构设计和外键关联，实现了数据的有效组织和管理。数据库结构清晰，便于系统的扩展和维护。

This database design covers multiple aspects required for organization management, including user management, material management, sign-in systems, and content management. Through rational table structure design and foreign key relationships, it achieves effective organization and management of data. The database structure is clear, facilitating system extension and maintenance.