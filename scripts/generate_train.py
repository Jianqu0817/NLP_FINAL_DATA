#!/usr/bin/env python3
"""Deterministically generate synthetic schema-plus-data training examples."""

from __future__ import annotations

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


SEED = 20261105
ROWS_PER_FAMILY = 25
SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "data" / "train_raw.jsonl"
NOTES_PATH = ROOT / "data" / "train_generation_notes.md"


DOMAINS: list[tuple[str, str, str, list[tuple[str, str]]]] = [
    (
        "meeting", "会议", "MT",
        [
            ("周例会预约", "weekly_sync_booking"),
            ("跨部门评审会邀请", "cross_team_review_invitation"),
            ("会议室设备借用", "meeting_room_equipment_loan"),
            ("讨论议程整理", "discussion_agenda_record"),
            ("会后行动项跟进", "post_meeting_action_followup"),
            ("混合会议接入安排", "hybrid_meeting_access"),
            ("参会签到汇总", "attendee_checkin_summary"),
            ("会议纪要归档", "meeting_minutes_archive"),
            ("临时改期通知", "meeting_reschedule_notice"),
            ("会议取消登记", "meeting_cancellation_record"),
        ],
    ),
    (
        "reminder", "提醒事项", "RM",
        [
            ("缴费截止提醒", "payment_due_reminder"),
            ("项目节点提醒", "project_milestone_reminder"),
            ("日程预约提醒", "appointment_reminder"),
            ("周期检查提醒", "periodic_check_reminder"),
            ("物品取回提醒", "item_pickup_reminder"),
            ("证件到期提醒", "document_expiry_reminder"),
            ("值班交接提醒", "shift_handover_reminder"),
            ("读书计划提醒", "reading_plan_reminder"),
            ("设备维护提醒", "equipment_maintenance_reminder"),
            ("报名截止提醒", "registration_deadline_reminder"),
        ],
    ),
    (
        "course", "课程", "CR",
        [
            ("课程开课信息", "course_start_notice"),
            ("作业发布记录", "assignment_publication"),
            ("测验安排", "quiz_schedule"),
            ("成绩登记", "grade_record"),
            ("课程考勤", "course_attendance"),
            ("教学资料发布", "teaching_material_release"),
            ("答疑时段预约", "office_hour_booking"),
            ("学习目标追踪", "learning_goal_tracking"),
            ("课程调课通知", "course_reschedule_notice"),
            ("结课证明申请", "course_completion_certificate"),
        ],
    ),
    (
        "registration", "报名登记", "RG",
        [
            ("学生活动报名", "student_activity_signup"),
            ("访客入校登记", "campus_visitor_registration"),
            ("社团成员登记", "club_member_registration"),
            ("技能工作坊报名", "skills_workshop_signup"),
            ("考试席位登记", "exam_seat_registration"),
            ("实验室培训登记", "lab_training_registration"),
            ("讲座预约", "lecture_reservation"),
            ("志愿者登记", "volunteer_registration"),
            ("竞赛队伍报名", "competition_team_signup"),
            ("场地使用申请", "venue_use_application"),
        ],
    ),
    (
        "inventory", "库存与物资", "IV",
        [
            ("库存盘点", "stocktaking_record"),
            ("批次追踪", "batch_tracking_record"),
            ("补货申请", "restock_request"),
            ("仓库调拨", "warehouse_transfer"),
            ("设备借用", "equipment_loan"),
            ("耗材领用", "consumables_issue"),
            ("货架位置登记", "shelf_location_record"),
            ("破损品报告", "damaged_goods_report"),
            ("供应商收货", "supplier_receipt"),
            ("有效期检查", "expiry_inspection"),
        ],
    ),
    (
        "order", "订单与售后", "OR",
        [
            ("采购订单", "purchase_order"),
            ("商品销售订单", "sales_order"),
            ("配送安排", "delivery_arrangement"),
            ("退款申请", "refund_request"),
            ("发票开具申请", "invoice_request"),
            ("包裹内容登记", "parcel_contents_record"),
            ("餐品订购", "meal_order"),
            ("订阅续费", "subscription_renewal"),
            ("售后维修单", "after_sales_repair"),
            ("支付记录", "payment_record"),
        ],
    ),
    (
        "book", "图书", "BK",
        [
            ("馆藏目录登记", "library_catalog_record"),
            ("图书借阅", "book_checkout"),
            ("图书归还", "book_return"),
            ("阅读清单", "reading_list"),
            ("读者书评", "reader_review"),
            ("图书采购申请", "book_purchase_request"),
            ("作者信息归档", "author_information_archive"),
            ("丛书关系登记", "book_series_record"),
            ("图书捐赠", "book_donation"),
            ("参考文献记录", "bibliography_record"),
        ],
    ),
    (
        "lab_task", "实验室任务", "LB",
        [
            ("实验计划", "experiment_plan"),
            ("样本采集", "sample_collection"),
            ("设备使用预约", "equipment_use_booking"),
            ("实验室安全检查", "lab_safety_inspection"),
            ("实验步骤记录", "experiment_step_record"),
            ("观测结果登记", "observation_result_record"),
            ("设备维护工单", "equipment_maintenance_ticket"),
            ("试剂配制记录", "reagent_preparation_record"),
            ("数据复核任务", "data_review_task"),
            ("实验异常报告", "experiment_incident_report"),
        ],
    ),
]

PEOPLE = [
    "林晓雨", "陈嘉宁", "王子涵", "李思远", "赵一诺", "周明轩", "吴雨桐",
    "徐景行", "孙可欣", "朱文博", "马清越", "胡安然", "郭晨曦", "何知夏",
    "高亦凡", "罗嘉树", "郑语桐", "梁星宇", "谢清和", "宋以宁", "唐若溪",
    "韩书瑶", "冯景明", "于乐言", "董思齐", "萧予安", "沈知行", "叶舒然",
    "秦望舒", "蒋闻笙", "许星晚", "潘一帆", "姚知微", "邓云舟", "卢嘉禾",
]
ITEMS = [
    "项目甲", "项目乙", "项目丙", "项目丁", "项目戊", "项目己", "项目庚",
    "项目辛", "项目壬", "项目癸", "项目子", "项目丑", "项目寅", "项目卯",
]
STATUSES = ["待处理", "处理中", "已完成"]


def string_schema(**kwargs: Any) -> dict[str, Any]:
    return {"type": "string", **kwargs}


def object_schema(
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    root: bool = False,
) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "required": list(properties) if required is None else required,
        "additionalProperties": False,
    }
    if root:
        schema["$schema"] = SCHEMA_DIALECT
    return schema


def code_for(prefix: str, family_number: int, variant: int) -> str:
    return f"{prefix}{family_number:02d}{variant + 1:04d}"


def phone_for(family_number: int, variant: int) -> str:
    return f"138{family_number:03d}{variant + 1:05d}"


def date_for(family_number: int, variant: int) -> str:
    month = variant % 12 + 1
    day = (family_number * 7 + variant * 3) % 27 + 1
    return f"2026-{month:02d}-{day:02d}"


def email_for(family_number: int, variant: int) -> str:
    return f"user{family_number:03d}.{variant + 1:02d}@example.org"


def draw_people(rng: random.Random, count: int) -> list[str]:
    return rng.sample(PEOPLE, count)


def draw_items(rng: random.Random, count: int) -> list[str]:
    return rng.sample(ITEMS, count)


def field_map(label: str, key: str, type_name: str, children: list[str] | None = None) -> str:
    text = f"{label}（{key}，{type_name}）"
    if children:
        text += "，包含" + "、".join(children)
    return text


def build_blueprint(
    kind: int,
    task: str,
    prefix: str,
    family_number: int,
    variant: int,
    rng: random.Random,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str], list[str]]:
    """Return schema, data, field mappings, facts, explicit rules, and rule tags."""
    record_id = code_for(prefix, family_number, variant)
    title = f"{task}第{variant + 1}次"
    maps: list[str]
    facts: list[str]
    rules: list[str]
    tags: list[str]

    if kind == 0:
        status = STATUSES[(family_number + variant) % len(STATUSES)]
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "title": string_schema(maxLength=24),
                "status": {"type": "string", "enum": STATUSES},
            }, root=True,
        )
        data = {"record_id": record_id, "title": title, "status": status}
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("处理状态", "status", "枚举字符串"),
        ]
        facts = [f"record_id 的值是“{record_id}”", f"title 的值是“{title}”", f"status 的值是“{status}”"]
        rules = [
            "record_id 必须由 2 个大写英文字母和 6 位数字组成",
            "title 最多 24 个字符",
            f"status 只能是“{'、'.join(STATUSES)}”中的一个",
            "record_id、title、status 都必填，不能添加未列出的字段",
        ]
        tags = ["pattern", "enum", "maxLength"]

    elif kind == 1:
        name = rng.choice(PEOPLE)
        phone = phone_for(family_number, variant)
        date = date_for(family_number, variant)
        contact = object_schema(
            {
                "name": string_schema(),
                "phone": string_schema(pattern="^1[3-9][0-9]{9}$"),
            }
        )
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "contact": contact,
                "date": string_schema(format="date"),
            }, root=True,
        )
        data = {"record_id": record_id, "contact": {"name": name, "phone": phone}, "date": date}
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("联系人", "contact", "对象", [
                field_map("姓名", "name", "字符串"),
                field_map("联系电话", "phone", "字符串"),
            ]),
            field_map("日期", "date", "日期字符串"),
        ]
        facts = [
            f"record_id 是“{record_id}”",
            f"contact 里的 name 是“{name}”，phone 是“{phone}”",
            f"date 是“{date}”",
        ]
        rules = [
            "contact 必须是对象，name 和 phone 都必填，不能增加对象字段",
            "phone 必须是 1 开头的 11 位中国手机号字符串，保留前导数字",
            "date 必须是有效日期",
            "record_id、contact、date 都必填，不能添加未列出的字段",
        ]
        tags = ["nested_object", "pattern", "format_date"]

    elif kind == 2:
        count = 2 + variant % 3
        people = draw_people(rng, count)
        date = date_for(family_number, variant)
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "date": string_schema(format="date"),
                "participants": {
                    "type": "array", "items": string_schema(),
                    "minItems": count, "maxItems": count,
                },
            }, root=True,
        )
        data = {"record_id": record_id, "date": date, "participants": people}
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("日期", "date", "日期字符串"),
            field_map("参与者姓名列表", "participants", "字符串数组"),
        ]
        facts = [
            f"record_id 是“{record_id}”",
            f"date 是“{date}”",
            f"participants 按此顺序为：{ '、'.join(f'“{p}”' for p in people) }",
        ]
        rules = [
            f"participants 恰好有 {count} 个姓名，按给出的顺序保留",
            "participants 的每一项都是字符串",
            "record_id、date、participants 都必填，不能添加未列出的字段",
        ]
        tags = ["array", "exact_array_length", "format_date"]

    elif kind == 3:
        count = 2 + variant % 3
        item_names = draw_items(rng, count)
        entries = [
            {"item_name": name, "quantity": (variant + i * 3) % 20 + 1}
            for i, name in enumerate(item_names)
        ]
        item_schema = object_schema(
            {
                "item_name": string_schema(),
                "quantity": {"type": "integer", "minimum": 1, "maximum": 20},
            }
        )
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "entries": {
                    "type": "array", "items": item_schema,
                    "minItems": count, "maxItems": count,
                },
            }, root=True,
        )
        data = {"record_id": record_id, "entries": entries}
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("明细列表", "entries", "对象数组", [
                field_map("明细名称", "item_name", "字符串"),
                field_map("数量", "quantity", "整数"),
            ]),
        ]
        entry_text = "；".join(
            f"第{i + 1}项 item_name 为“{entry['item_name']}”，quantity 为 {entry['quantity']}"
            for i, entry in enumerate(entries)
        )
        facts = [f"record_id 是“{record_id}”", f"entries 的顺序内容为：{entry_text}"]
        rules = [
            f"entries 恰好有 {count} 项，保留输入顺序",
            "每项必须是对象，item_name 是字符串，quantity 是 1 到 20 的整数",
            "每项只能包含 item_name 和 quantity",
            "record_id 和 entries 都必填，不能添加未列出的字段",
        ]
        tags = ["array", "nested_object", "exact_array_length", "numeric_bounds"]

    elif kind == 4:
        quantity = variant % 20 + 1
        duration = (variant * 17) % 476 + 5
        status = STATUSES[(variant + family_number) % len(STATUSES)]
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "title": string_schema(maxLength=24),
                "quantity": {"type": "integer"},
                "duration_minutes": {"type": "integer"},
                "status": {"type": "string", "enum": STATUSES},
            }, root=True,
        )
        schema["allOf"] = [
            {"properties": {"quantity": {"minimum": 1}}},
            {"properties": {"quantity": {"maximum": 20}}},
            {"properties": {"duration_minutes": {"minimum": 5}}},
            {"properties": {"duration_minutes": {"maximum": 480}}},
        ]
        data = {
            "record_id": record_id, "title": title, "quantity": quantity,
            "duration_minutes": duration, "status": status,
        }
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("数量", "quantity", "整数"),
            field_map("时长", "duration_minutes", "整数，单位为分钟"),
            field_map("处理状态", "status", "枚举字符串"),
        ]
        facts = [
            f"record_id 是“{record_id}”", f"title 是“{title}”",
            f"quantity 是 {quantity}", f"duration_minutes 是 {duration}",
            f"status 是“{status}”",
        ]
        rules = [
            "quantity 是 1 到 20 的整数",
            "duration_minutes 是 5 到 480 的整数",
            "status 只能是“待处理、处理中、已完成”之一",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "record_id、title、quantity、duration_minutes、status 都必填，不能添加未列出的字段",
        ]
        tags = ["allOf", "numeric_bounds", "enum", "pattern", "maxLength"]

    elif kind == 5:
        schema = object_schema(
            {
                "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
                "title": string_schema(maxLength=24),
                "description": {"type": ["string", "null"], "maxLength": 80},
                "source_ref": string_schema(maxLength=30),
            },
            required=["record_id", "title", "description"], root=True,
        )
        data = {"record_id": record_id, "title": title, "description": None}
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("补充说明", "description", "可空字符串"),
            field_map("来源编号", "source_ref", "可选字符串"),
        ]
        facts = [
            f"record_id 是“{record_id}”", f"title 是“{title}”",
            "description 的信息缺失，请明确写为 null",
            "本条没有 source_ref；source_ref 是可选字段，省略",
        ]
        rules = [
            "description 必须出现，值可以是字符串或 null，最多 80 个字符",
            "source_ref 是可选字符串，最多 30 个字符",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "不能添加未列出的字段",
        ]
        tags = ["nullable", "optional_property", "maxLength", "pattern"]

    elif kind == 6:
        channel = "短信" if variant % 2 == 0 else "邮件"
        properties = {
            "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
            "title": string_schema(maxLength=24),
            "notify_by": {"type": "string", "enum": ["短信", "邮件"]},
            "phone": string_schema(pattern="^1[3-9][0-9]{9}$"),
            "email": string_schema(format="email"),
        }
        schema = object_schema(
            properties,
            required=["record_id", "title", "notify_by"], root=True,
        )
        schema["if"] = {
            "properties": {"notify_by": {"const": "短信"}},
            "required": ["notify_by"],
        }
        schema["then"] = {"required": ["phone"]}
        schema["else"] = {"required": ["email"]}
        data = {"record_id": record_id, "title": title, "notify_by": channel}
        if channel == "短信":
            phone = phone_for(family_number, variant)
            data["phone"] = phone
            chosen_fact = f"phone 是“{phone}”"
        else:
            email = email_for(family_number, variant)
            data["email"] = email
            chosen_fact = f"email 是“{email}”"
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("通知渠道", "notify_by", "枚举字符串"),
            field_map("手机号", "phone", "字符串"),
            field_map("邮箱", "email", "字符串"),
        ]
        facts = [
            f"record_id 是“{record_id}”", f"title 是“{title}”",
            f"notify_by 是“{channel}”", chosen_fact,
            "未选择的联系方式字段不填写",
        ]
        rules = [
            "notify_by 只能是“短信”或“邮件”，且必须提供",
            "notify_by 为“短信”时 phone 必填且符合 11 位手机号格式；notify_by 为“邮件”时 email 必填且符合 email 格式",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "除分支要求的联系方式外，不能添加未列出的字段",
        ]
        tags = ["conditional", "if_then_else", "const", "enum", "format_email", "pattern"]

    elif kind == 7:
        has_backup = variant % 2 == 0
        properties = {
            "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
            "title": string_schema(maxLength=24),
            "backup_contact": string_schema(),
            "backup_phone": string_schema(pattern="^1[3-9][0-9]{9}$"),
        }
        schema = object_schema(
            properties, required=["record_id", "title"], root=True,
        )
        schema["dependentRequired"] = {"backup_contact": ["backup_phone"]}
        data = {"record_id": record_id, "title": title}
        facts = [f"record_id 是“{record_id}”", f"title 是“{title}”"]
        if has_backup:
            backup_name = rng.choice(PEOPLE)
            backup_phone = phone_for(family_number, variant)
            data["backup_contact"] = backup_name
            data["backup_phone"] = backup_phone
            facts.append(f"backup_contact 是“{backup_name}”，backup_phone 是“{backup_phone}”")
            facts.append("本条提供备用联系人和备用电话")
        else:
            facts.append("本条没有备用联系人或备用电话，两个可选字段都省略")
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("备用联系人", "backup_contact", "可选字符串"),
            field_map("备用电话", "backup_phone", "可选字符串"),
        ]
        rules = [
            "backup_contact 和 backup_phone 都是可选字段",
            "一旦提供 backup_contact，就必须同时提供 backup_phone；backup_phone 是符合 11 位手机号格式的字符串",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "record_id 和 title 必填，不能添加未列出的字段",
        ]
        tags = ["dependentRequired", "optional_property", "pattern", "maxLength"]

    elif kind == 8:
        channel = "短信" if variant % 2 == 0 else "邮箱"
        properties = {
            "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
            "title": string_schema(maxLength=24),
            "contact_method": {"type": "string", "enum": ["短信", "邮箱"]},
            "phone": string_schema(pattern="^1[3-9][0-9]{9}$"),
            "email": string_schema(format="email"),
        }
        schema = object_schema(
            properties, required=["record_id", "title"], root=True,
        )
        schema["oneOf"] = [
            {
                "properties": {"contact_method": {"const": "短信"}},
                "required": ["contact_method", "phone"],
            },
            {
                "properties": {"contact_method": {"const": "邮箱"}},
                "required": ["contact_method", "email"],
            },
        ]
        data = {"record_id": record_id, "title": title, "contact_method": channel}
        if channel == "短信":
            phone = phone_for(family_number, variant)
            data["phone"] = phone
            chosen_fact = f"phone 是“{phone}”"
        else:
            email = email_for(family_number, variant)
            data["email"] = email
            chosen_fact = f"email 是“{email}”"
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("联系方式类型", "contact_method", "枚举字符串"),
            field_map("手机号", "phone", "字符串"),
            field_map("邮箱", "email", "字符串"),
        ]
        facts = [
            f"record_id 是“{record_id}”", f"title 是“{title}”",
            f"contact_method 是“{channel}”", chosen_fact,
            "只保留 contact_method 指定的那一种联系方式",
        ]
        rules = [
            "contact_method 为“短信”时必须提供 phone；为“邮箱”时必须提供 email",
            "必须且只能满足一个联系方式分支，未选分支的字段省略",
            "phone 是符合 11 位手机号格式的字符串；email 符合 email 格式",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "不能添加未列出的字段",
        ]
        tags = ["oneOf", "const", "enum", "format_email", "pattern"]

    elif kind == 9:
        contact_case = variant % 3
        properties = {
            "record_id": string_schema(pattern="^[A-Z]{2}[0-9]{6}$"),
            "title": string_schema(maxLength=24),
            "email": string_schema(format="email"),
            "phone": string_schema(pattern="^1[3-9][0-9]{9}$"),
        }
        schema = object_schema(
            properties, required=["record_id", "title"], root=True,
        )
        schema["anyOf"] = [{"required": ["email"]}, {"required": ["phone"]}]
        data = {"record_id": record_id, "title": title}
        facts = [f"record_id 是“{record_id}”", f"title 是“{title}”"]
        if contact_case in (0, 2):
            email = email_for(family_number, variant)
            data["email"] = email
            facts.append(f"email 是“{email}”")
        if contact_case in (1, 2):
            phone = phone_for(family_number, variant)
            data["phone"] = phone
            facts.append(f"phone 是“{phone}”")
        maps = [
            field_map("记录编号", "record_id", "字符串"),
            field_map("事项名称", "title", "字符串"),
            field_map("邮箱", "email", "可选字符串"),
            field_map("手机号", "phone", "可选字符串"),
        ]
        facts.append("email 和 phone 至少填写一个；未提供的可选联系方式字段省略")
        rules = [
            "email 和 phone 至少提供一个，也可以两个都提供",
            "email 必须符合 email 格式；phone 必须是符合 11 位手机号格式的字符串",
            "title 最多 24 个字符；record_id 是 2 个大写字母后接 6 位数字",
            "record_id 和 title 必填，不能添加未列出的字段",
        ]
        tags = ["anyOf", "format_email", "pattern", "optional_property"]

    else:
        raise ValueError(f"Unknown blueprint kind: {kind}")

    return schema, data, maps, facts, rules, tags


def build_domain_fields(
    domain_slug: str,
    domain_index: int,
    task_index: int,
    variant: int,
    family_number: int,
    rng: random.Random,
) -> tuple[dict[str, Any], dict[str, Any], list[str], list[str], list[str], list[str]]:
    """Add a domain-specific structure and family-specific constraints."""
    if domain_slug == "meeting":
        room_max = 8 + task_index
        room = f"创新楼{chr(ord('A') + variant % 4)}{301 + variant % 90}"
        mode = ["线下", "线上", "混合"][variant % 3]
        props = {
            "meeting_schedule": object_schema(
                {
                    "meeting_date": string_schema(format="date"),
                    "room": string_schema(maxLength=room_max),
                    "mode": {"type": "string", "enum": ["线下", "线上", "混合"]},
                }
            )
        }
        values = {"meeting_schedule": {"meeting_date": date_for(family_number, variant), "room": room, "mode": mode}}
        maps = [field_map("会议安排", "meeting_schedule", "对象", [
            field_map("会议日期", "meeting_date", "日期字符串"),
            field_map("会议室", "room", "字符串"),
            field_map("会议形式", "mode", "枚举字符串"),
        ])]
        rules = [
            f"meeting_schedule.meeting_date 是有效日期",
            f"meeting_schedule.room 最多 {room_max} 个字符",
            "meeting_schedule.mode 只能是“线下、线上、混合”之一",
            "meeting_schedule 的三个子字段都必填，不能添加其他子字段",
        ]
        facts = [f"meeting_schedule.meeting_date 是“{values['meeting_schedule']['meeting_date']}”", f"meeting_schedule.room 是“{room}”", f"meeting_schedule.mode 是“{mode}”"]
        tags = ["nested_object", "format_date", "enum", "maxLength"]

    elif domain_slug == "reminder":
        repeat_max = 7 + task_index * 3
        channel_count = 1 + variant % 2
        channels = rng.sample(["站内信", "短信", "邮件"], channel_count)
        props = {
            "reminder_schedule": object_schema(
                {
                    "due_date": string_schema(format="date"),
                    "repeat_every_days": {"type": "integer", "minimum": 1, "maximum": repeat_max},
                    "channels": {"type": "array", "items": {"type": "string", "enum": ["站内信", "短信", "邮件"]}, "minItems": 1, "maxItems": 2},
                }
            )
        }
        repeat_days = variant % repeat_max + 1
        values = {"reminder_schedule": {"due_date": date_for(family_number, variant), "repeat_every_days": repeat_days, "channels": channels}}
        maps = [field_map("提醒计划", "reminder_schedule", "对象", [
            field_map("到期日期", "due_date", "日期字符串"),
            field_map("重复间隔天数", "repeat_every_days", "整数"),
            field_map("发送渠道列表", "channels", "枚举字符串数组"),
        ])]
        rules = [
            "reminder_schedule.due_date 是有效日期",
            f"reminder_schedule.repeat_every_days 是 1 到 {repeat_max} 的整数",
            "reminder_schedule.channels 有 1 到 2 个值，只能从“站内信、短信、邮件”中选择，并按输入顺序保留",
            "reminder_schedule 的三个子字段都必填，不能添加其他子字段",
        ]
        facts = [f"reminder_schedule.due_date 是“{values['reminder_schedule']['due_date']}”", f"reminder_schedule.repeat_every_days 是 {repeat_days}", f"reminder_schedule.channels 按顺序为：{'、'.join(f'“{channel}”' for channel in channels)}"]
        tags = ["nested_object", "format_date", "numeric_bounds", "array", "enum"]

    elif domain_slug == "course":
        score_max = 80 + task_index * 2
        score = variant % (score_max + 1)
        weight = [0.25, 0.4, 0.55, 0.7][variant % 4]
        assessment_type = ["作业", "测验", "实验"][variant % 3]
        props = {
            "assessment_detail": object_schema(
                {
                    "score": {"type": "integer", "minimum": 0, "maximum": score_max},
                    "weight": {"type": "number", "minimum": 0.1, "maximum": 1.0},
                    "assessment_type": {"type": "string", "enum": ["作业", "测验", "实验"]},
                }
            )
        }
        values = {"assessment_detail": {"score": score, "weight": weight, "assessment_type": assessment_type}}
        maps = [field_map("课程考核明细", "assessment_detail", "对象", [
            field_map("得分", "score", "整数"),
            field_map("成绩权重", "weight", "数值"),
            field_map("考核形式", "assessment_type", "枚举字符串"),
        ])]
        rules = [
            f"assessment_detail.score 是 0 到 {score_max} 的整数",
            "assessment_detail.weight 是 0.1 到 1.0 的数值",
            "assessment_detail.assessment_type 只能是“作业、测验、实验”之一",
            "assessment_detail 的三个子字段都必填，不能添加其他子字段",
        ]
        facts = [f"assessment_detail.score 是 {score}", f"assessment_detail.weight 是 {weight}", f"assessment_detail.assessment_type 是“{assessment_type}”"]
        tags = ["nested_object", "numeric_bounds", "enum"]

    elif domain_slug == "registration":
        seat_max = 20 + task_index * 5
        seat_count = variant % seat_max + 1
        count = 2 + variant % 3
        participant_ids = [f"RG{task_index + 1:02d}{(variant * 3 + i + 1) % 10_000:04d}" for i in range(count)]
        props = {
            "registration_category": {"type": "string", "enum": ["个人", "团队", "候补"]},
            "seat_count": {"type": "integer", "minimum": 1, "maximum": seat_max},
            "participant_ids": {"type": "array", "items": string_schema(pattern="^RG[0-9]{6}$"), "minItems": count, "maxItems": count},
        }
        category = ["个人", "团队", "候补"][variant % 3]
        values = {"registration_category": category, "seat_count": seat_count, "participant_ids": participant_ids}
        maps = [
            field_map("报名类别", "registration_category", "枚举字符串"),
            field_map("申请席位数", "seat_count", "整数"),
            field_map("参与者编号列表", "participant_ids", "字符串数组"),
        ]
        rules = [
            "registration_category 只能是“个人、团队、候补”之一",
            f"seat_count 是 1 到 {seat_max} 的整数",
            f"participant_ids 恰好有 {count} 个编号，按输入顺序保留；每个编号由 RG 和 6 位数字组成",
            "registration_category、seat_count、participant_ids 都必填，不能添加未列出的字段",
        ]
        facts = [f"registration_category 是“{category}”", f"seat_count 是 {seat_count}", f"participant_ids 按顺序为：{'、'.join(f'“{participant_id}”' for participant_id in participant_ids)}"]
        tags = ["enum", "numeric_bounds", "array", "exact_array_length", "pattern"]

    elif domain_slug == "inventory":
        stock_max = 100 + task_index * 50
        stock_level = variant % 101
        warehouse = f"WH-{chr(ord('A') + variant % 6)}"
        shelf = f"{chr(ord('A') + variant % 8)}{variant % 90 + 1:02d}"
        props = {
            "storage_location": object_schema(
                {
                    "warehouse_code": string_schema(pattern="^WH-[A-Z]$"),
                    "shelf_code": string_schema(pattern="^[A-Z][0-9]{2}$"),
                }
            ),
            "stock_level": {"type": "integer", "minimum": 0, "maximum": stock_max},
        }
        values = {"storage_location": {"warehouse_code": warehouse, "shelf_code": shelf}, "stock_level": stock_level}
        maps = [
            field_map("存放位置", "storage_location", "对象", [
                field_map("仓库代码", "warehouse_code", "字符串"),
                field_map("货架代码", "shelf_code", "字符串"),
            ]),
            field_map("现有库存量", "stock_level", "整数"),
        ]
        rules = [
            "storage_location.warehouse_code 必须是 WH- 加一个大写英文字母",
            "storage_location.shelf_code 必须是一个大写英文字母后接两位数字",
            f"stock_level 是 0 到 {stock_max} 的整数",
            "storage_location 和 stock_level 都是顶层必填字段；storage_location 内的 warehouse_code 和 shelf_code 也都必填",
        ]
        facts = [f"storage_location.warehouse_code 是“{warehouse}”", f"storage_location.shelf_code 是“{shelf}”", f"stock_level 是 {stock_level}"]
        tags = ["nested_object", "pattern", "numeric_bounds"]

    elif domain_slug == "order":
        quantity_max = 5 + task_index * 3
        price_max = 500 + task_index * 100
        count = 1 + variant % 3
        line_items = []
        for i in range(count):
            sku_number = (task_index * 1000 + variant * 3 + i + 1) % 100_000
            line_items.append({
                "sku": f"SKU-{sku_number:05d}",
                "quantity": (variant + i) % quantity_max + 1,
                "unit_price": round(12.5 + variant % 20 + i * 7.25, 2),
            })
        props = {
            "line_items": {
                "type": "array",
                "items": object_schema({
                    "sku": string_schema(pattern="^SKU-[0-9]{5}$"),
                    "quantity": {"type": "integer", "minimum": 1, "maximum": quantity_max},
                    "unit_price": {"type": "number", "minimum": 0.01, "maximum": price_max},
                }),
                "minItems": count, "maxItems": count,
            }
        }
        values = {"line_items": line_items}
        maps = [field_map("订单商品明细", "line_items", "对象数组", [
            field_map("商品代码", "sku", "字符串"),
            field_map("购买数量", "quantity", "整数"),
            field_map("单价", "unit_price", "数值"),
        ])]
        rules = [
            f"line_items 恰好有 {count} 项，按输入顺序保留",
            f"每项 sku 必须是 SKU- 加 5 位数字；quantity 是 1 到 {quantity_max} 的整数；unit_price 是 0.01 到 {price_max} 的数值",
            "每个明细对象只能有 sku、quantity 和 unit_price，三个字段都必填",
        ]
        facts = ["line_items 的顺序明细为：" + "；".join(f"第{i + 1}项 sku 是“{item['sku']}”、quantity 是 {item['quantity']}、unit_price 是 {item['unit_price']}" for i, item in enumerate(line_items))]
        tags = ["array", "nested_object", "exact_array_length", "pattern", "numeric_bounds"]

    elif domain_slug == "book":
        page_max = 800 + task_index * 50
        page_count = 120 + (variant * 7) % 600
        isbn = f"978{task_index + 1:02d}{variant + 1:04d}{domain_index + 1:04d}"
        props = {
            "book_catalog": object_schema(
                {
                    "isbn": string_schema(pattern="^978[0-9]{10}$"),
                    "page_count": {"type": "integer", "minimum": 1, "maximum": page_max},
                    "publication_date": string_schema(format="date"),
                }
            )
        }
        values = {"book_catalog": {"isbn": isbn, "page_count": page_count, "publication_date": date_for(family_number, variant)}}
        maps = [field_map("图书编目信息", "book_catalog", "对象", [
            field_map("ISBN", "isbn", "字符串"),
            field_map("页数", "page_count", "整数"),
            field_map("出版日期", "publication_date", "日期字符串"),
        ])]
        rules = [
            "book_catalog.isbn 必须是 978 开头的 13 位数字字符串",
            f"book_catalog.page_count 是 1 到 {page_max} 的整数",
            "book_catalog.publication_date 是有效日期",
            "book_catalog 的三个子字段都必填，不能添加其他子字段",
        ]
        facts = [f"book_catalog.isbn 是“{isbn}”", f"book_catalog.page_count 是 {page_count}", f"book_catalog.publication_date 是“{values['book_catalog']['publication_date']}”"]
        tags = ["nested_object", "pattern", "numeric_bounds", "format_date"]

    elif domain_slug == "lab_task":
        measurement_max = 100 + task_index * 20
        count = 2 + variant % 3
        measurements = []
        for i in range(count):
            sample_number = (task_index * 100 + variant * 3 + i + 1) % 10_000
            measurements.append({
                "sample_code": f"LAB-AB{sample_number:04d}",
                "value": round(-10 + ((variant * 9 + i * 7) % 100) / 2, 1),
                "unit": ["°C", "mg", "mL"][i % 3],
            })
        props = {
            "measurements": {
                "type": "array",
                "items": object_schema({
                    "sample_code": string_schema(pattern="^LAB-[A-Z]{2}[0-9]{4}$"),
                    "value": {"type": "number", "minimum": -50, "maximum": measurement_max},
                    "unit": {"type": "string", "enum": ["°C", "mg", "mL"]},
                }),
                "minItems": count, "maxItems": count,
            }
        }
        values = {"measurements": measurements}
        maps = [field_map("样本测量结果", "measurements", "对象数组", [
            field_map("样本代码", "sample_code", "字符串"),
            field_map("测量数值", "value", "数值"),
            field_map("测量单位", "unit", "枚举字符串"),
        ])]
        rules = [
            f"measurements 恰好有 {count} 项，按输入顺序保留",
            f"每项 sample_code 符合 LAB- 加 2 个大写英文字母和 4 位数字；value 是 -50 到 {measurement_max} 的数值；unit 只能是“°C、mg、mL”之一",
            "每个测量对象只能有 sample_code、value 和 unit，三个字段都必填",
        ]
        facts = ["measurements 的顺序数据为：" + "；".join(f"第{i + 1}项 sample_code 是“{item['sample_code']}”、value 是 {item['value']}、unit 是“{item['unit']}”" for i, item in enumerate(measurements))]
        tags = ["array", "nested_object", "exact_array_length", "pattern", "numeric_bounds", "enum"]

    else:
        raise ValueError(f"Unknown domain: {domain_slug}")

    return props, values, maps, rules, facts, tags


def specialize_record_id(
    schema: dict[str, Any],
    data: dict[str, Any],
    facts: list[str],
    rules: list[str],
    prefix: str,
    task_index: int,
    variant: int,
) -> tuple[list[str], list[str]]:
    """Give each semantic family its own stated record identifier pattern."""
    pattern_prefix = f"{prefix}{task_index + 1:02d}"
    old_value = data["record_id"]
    new_value = f"{pattern_prefix}{variant + 1:04d}"
    data["record_id"] = new_value
    schema["properties"]["record_id"]["pattern"] = f"^{pattern_prefix}[0-9]{{4}}$"
    facts = [fact.replace(old_value, new_value) for fact in facts]
    id_rule = f"record_id 必须由前缀“{pattern_prefix}”和 4 位数字组成"
    updated_rules = []
    for rule in rules:
        rule = rule.replace("record_id 必须由 2 个大写英文字母和 6 位数字组成", id_rule)
        rule = rule.replace("record_id 是 2 个大写字母后接 6 位数字", id_rule)
        updated_rules.append(rule)
    return facts, updated_rules


def make_prompt(task: str, maps: list[str], rules: list[str], facts: list[str]) -> str:
    return (
        f"请把“{task}”整理为一条结构化记录。字段映射："
        + "；".join(maps)
        + "。约束要求："
        + "；".join(rules)
        + "。本条的具体信息："
        + "；".join(facts)
        + "。未标为可选的字段均须填写；对象中不要添加未列出的字段；"
        + "有序列表按给出的顺序保留。请给出符合这些要求的 schema 和 data 两个对象。"
    )


def generate_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    family_number = 0
    for domain_index, (domain_slug, domain_name, prefix, tasks) in enumerate(DOMAINS):
        for kind, (task, task_slug) in enumerate(tasks):
            family_number += 1
            family = f"{domain_slug}_{task_slug}"
            for variant in range(ROWS_PER_FAMILY):
                rng = random.Random(SEED + family_number * 10_000 + variant)
                schema, data, maps, facts, rules, tags = build_blueprint(
                    kind, task, prefix, family_number, variant, rng,
                )
                facts, rules = specialize_record_id(schema, data, facts, rules, prefix, kind, variant)
                extra_schema, extra_data, extra_maps, extra_rules, extra_facts, extra_tags = build_domain_fields(
                    domain_slug, domain_index, kind, variant, family_number, rng,
                )
                schema["properties"].update(extra_schema)
                schema["required"].extend(extra_schema)
                data.update(extra_data)
                maps.extend(extra_maps)
                rules.extend(extra_rules)
                facts.extend(extra_facts)
                tags = list(dict.fromkeys(tags + extra_tags))
                rows.append(
                    {
                        "id": f"luna_train_{len(rows) + 1:06d}",
                        "split": "train",
                        "family": family,
                        "rule_tags": tags,
                        "input": make_prompt(task, maps, rules, facts),
                        "reference_schema": schema,
                        "reference_data": data,
                        "provenance": {
                            "model": "gpt-6-luna max",
                            "method": "template-assisted synthetic generation",
                            "generator": "scripts/generate_train.py",
                            "seed": SEED,
                        },
                    }
                )
    return rows


def validate_rows(rows: list[dict[str, Any]]) -> Counter[str]:
    format_checker = FormatChecker()
    family_counts: Counter[str] = Counter()
    ids: set[str] = set()
    for row in rows:
        if row["id"] in ids:
            raise ValueError(f"Duplicate row id: {row['id']}")
        ids.add(row["id"])
        family_counts[row["family"]] += 1
        schema = row["reference_schema"]
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema, format_checker=format_checker)
        errors = sorted(validator.iter_errors(row["reference_data"]), key=lambda e: list(e.path))
        if errors:
            error = errors[0]
            location = ".".join(str(part) for part in error.path) or "<root>"
            raise ValueError(f"{row['id']} invalid at {location}: {error.message}")
        if row["split"] != "train":
            raise ValueError(f"Unexpected split for {row['id']}: {row['split']}")
        if row["provenance"].get("model") != "gpt-6-luna max":
            raise ValueError(f"Missing requested model provenance for {row['id']}")
        if row["provenance"].get("method") != "template-assisted synthetic generation":
            raise ValueError(f"Missing synthetic-generation provenance for {row['id']}")
    return family_counts


def write_notes(rows: list[dict[str, Any]], family_counts: Counter[str]) -> tuple[int, int, int]:
    tag_counts = Counter(tag for row in rows for tag in row["rule_tags"])
    representative_rows: dict[str, dict[str, Any]] = {}
    for row in rows:
        representative_rows.setdefault(row["family"], row)

    def schema_signature(schema: dict[str, Any], normalize_record_id: bool = False) -> str:
        def clean(value: Any, path: tuple[str, ...] = ()) -> Any:
            if isinstance(value, dict):
                result = {}
                for key, child in value.items():
                    if key in {"title", "description"} and (not path or path[-1] != "properties"):
                        continue
                    if normalize_record_id and path == ("properties", "record_id") and key == "pattern":
                        result[key] = "<family record-id pattern>"
                    else:
                        result[key] = clean(child, path + (key,))
                return result
            if isinstance(value, list):
                return [clean(child, path) for child in value]
            return value
        return json.dumps(clean(schema), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    exact_family_schemas = {
        schema_signature(row["reference_schema"])
        for row in representative_rows.values()
    }
    structural_family_schemas = {
        schema_signature(row["reference_schema"], normalize_record_id=True)
        for row in representative_rows.values()
    }
    exact_row_schemas = {schema_signature(row["reference_schema"]) for row in rows}
    by_domain: Counter[str] = Counter()
    for domain_slug, _domain_name, _prefix, _tasks in DOMAINS:
        by_domain[domain_slug] = sum(
            count for family, count in family_counts.items()
            if family.startswith(domain_slug + "_")
        )
    lines = [
        "# Training data generation notes",
        "",
        "- Rows: 2,000 synthetic examples, all assigned to the `train` split.",
        f"- Named scenarios: {len(family_counts)} semantic task families; {ROWS_PER_FAMILY} deterministic slot substitutions per family.",
        f"- Representative schema variants: {len(exact_family_schemas)} distinct schemas across the {len(family_counts)} scenario families.",
        f"- Structural/constraint combinations: {len(structural_family_schemas)} distinct representative schemas after normalizing away family-specific record-ID patterns and schema title/description annotations.",
        f"- Exact row-level schema signatures: {len(exact_row_schemas)} after excluding schema title/description annotations.",
        f"- Seed: `{SEED}`. Running `python scripts/generate_train.py` rewrites the same JSONL deterministically.",
        "- Provenance on every row: `gpt-6-luna max`; `template-assisted synthetic generation`.",
        "- No external APIs were called. No independent human validation is claimed.",
        "",
        "## Family counts by domain",
        "",
    ]
    for domain_slug, domain_name, _prefix, _tasks in DOMAINS:
        lines.append(f"- {domain_name} (`{domain_slug}`): {by_domain[domain_slug]} rows, 10 families.")
    lines.extend(["", "## Rule coverage", ""])
    for tag, count in sorted(tag_counts.items()):
        lines.append(f"- `{tag}`: {count} rows")
    lines.extend(
        [
            "",
            "The scenarios cover meetings, reminders, courses, registration, inventory, orders, books, and lab tasks. Each family has a domain-specific structure (such as meeting schedules, reminder recurrence, course assessments, registration seats, stock locations, order line items, book catalog data, or lab measurements) alongside one of ten shared extraction patterns. Prompts provide English field keys with Chinese explanations, all rules, every concrete reference value, and array order. Optional and conditional/dependency branches are spelled out per example.",
            "",
            "The schemas use Draft 2020-12 and the contract's supported keywords: scalar types, nested objects, arrays with exact lengths, enums, numeric bounds, string patterns and lengths, date/email formats, nullable values, `if`/`then`/`else`, `dependentRequired`, `oneOf`, `anyOf`, and `allOf`. Every schema and data instance was checked locally using `jsonschema` Draft202012Validator with `FormatChecker`.",
        ]
    )
    NOTES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(exact_family_schemas), len(structural_family_schemas), len(exact_row_schemas)


def main() -> None:
    rows = generate_rows()
    if len(rows) != 2000:
        raise ValueError(f"Expected 2000 rows, generated {len(rows)}")
    family_counts = validate_rows(rows)
    if len(family_counts) != 80 or any(count != ROWS_PER_FAMILY for count in family_counts.values()):
        raise ValueError(f"Unexpected family distribution: {len(family_counts)} families")
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="\n") as out:
        for row in rows:
            out.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    family_schema_count, structural_count, row_schema_count = write_notes(rows, family_counts)
    tag_counts = Counter(tag for row in rows for tag in row["rule_tags"])
    print(f"Wrote {len(rows)} rows across {len(family_counts)} families to {OUTPUT_PATH}")
    print(f"Validated all schemas and instances with Draft202012Validator + FormatChecker")
    print(f"Schema signatures: {family_schema_count} family representatives, {structural_count} structural/constraint combinations, {row_schema_count} row-level")
    print("Rule tags: " + ", ".join(f"{key}={value}" for key, value in sorted(tag_counts.items())))


if __name__ == "__main__":
    main()
