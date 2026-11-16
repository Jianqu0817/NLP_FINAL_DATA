#!/usr/bin/env python3
"""Deterministically generate the held-out NL-to-schema+data evaluation sets."""

from __future__ import annotations

import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
SEED = 20261105
MODEL = "GPT-6 Luna max"
SCHEMA_URI = "https://json-schema.org/draft/2020-12/schema"


def s(min_len: int | None = None, max_len: int | None = None,
      pattern: str | None = None, fmt: str | None = None,
      choices: list[str] | None = None, nullable: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"type": ["string", "null"] if nullable else "string"}
    if min_len is not None:
        out["minLength"] = min_len
    if max_len is not None:
        out["maxLength"] = max_len
    if pattern is not None:
        out["pattern"] = pattern
    if fmt is not None:
        out["format"] = fmt
    if choices is not None:
        out["enum"] = choices
    return out


def n(minimum: int | float | None = None, maximum: int | float | None = None,
      integer: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"type": "integer" if integer else "number"}
    if minimum is not None:
        out["minimum"] = minimum
    if maximum is not None:
        out["maximum"] = maximum
    return out


def arr(item: dict[str, Any], minimum: int | None = None,
        maximum: int | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"type": "array", "items": item}
    if minimum is not None:
        out["minItems"] = minimum
    if maximum is not None:
        out["maxItems"] = maximum
    return out


def obj(props: dict[str, Any], required: list[str] | None = None,
        **extra: Any) -> dict[str, Any]:
    out: dict[str, Any] = {
        "type": "object",
        "properties": props,
        "required": list(props) if required is None else required,
        "additionalProperties": False,
    }
    out.update(extra)
    return out


def root_schema(props: dict[str, Any], required: list[str], **extra: Any) -> dict[str, Any]:
    out = obj(props, required, **extra)
    out["$schema"] = SCHEMA_URI
    return out


OPENERS = [
    "请将这则{task}整理成结构化记录。",
    "麻烦根据下面的字段说明和具体信息，抽取一份{task}记录。",
    "要录入一条{task}信息，请按给出的字段与规则完成整理。",
    "请从以下材料整理{task}，字段名称以括号中的英文键为准。",
    "按下列字段要求，把这段{task}内容转成结构化记录。",
]
CONNECTORS = ["字段与约束：{rules} 具体记录：{facts}",
              "需要的字段和规则如下：{rules}；材料内容：{facts}",
              "字段说明：{rules} 这条记录写的是：{facts}",
              "请遵守这些字段要求：{rules} 给出的事实是：{facts}"]
ENDINGS = [
    "未标为可选的字段均为必填，不得增加其他字段。输出只含一个 JSON 对象，键为 schema 和 data。",
    "没有注明可选的字段都要填写，也不要补造字段；结果对象只包含 schema 与 data。",
    "按记录中明确给出的信息填写，不能添加额外字段。请返回含 schema、data 两个键的 JSON 对象。",
]


def prompt(task: str, rules: str, facts: str, i: int) -> str:
    seeded = random.Random(f"{SEED}:{task}:{i}")
    return " ".join((seeded.choice(OPENERS).format(task=task),
                     seeded.choice(CONNECTORS).format(rules=rules, facts=facts),
                     seeded.choice(ENDINGS)))


def dt(i: int, start: date = date(2026, 3, 2), step: int = 1) -> str:
    return (start + timedelta(days=(i * step) % 250)).isoformat()


def family(name: str, split: str, tags: list[str], task: str,
           builder: Callable[[int, random.Random], tuple[str, dict[str, Any], dict[str, Any]]]) -> dict[str, Any]:
    return {"name": name, "split": split, "tags": tags, "task": task, "builder": builder}


def val_campus_identity(i: int, r: random.Random):
    majors = ["计算机科学", "金融学", "新闻传播", "生物工程", "汉语言文学"]
    names = ["林知夏", "周予安", "陈嘉树", "许清禾", "沈一诺", "唐可心", "顾明远", "宋雨桐"]
    student = f"S26{i:04d}"
    name, major, year = names[i % len(names)], majors[(i * 3) % len(majors)], 1 + i % 4
    rules = ("学生编号（student_id）为 S 后接 6 位数字；姓名（name）是字符串；"
             "专业（major）只能取计算机科学、金融学、新闻传播、生物工程、汉语言文学之一；"
             "年级（year）为 1 到 4 的整数。")
    facts = f"编号 {student}，姓名{name}，专业{major}，目前读{year}年级。"
    schema = root_schema({"student_id": s(pattern=r"^S[0-9]{6}$"), "name": s(),
                          "major": s(choices=majors), "year": n(1, 4, True)},
                         ["student_id", "name", "major", "year"])
    return prompt("校园学生身份", rules, facts, i), schema, {"student_id": student, "name": name, "major": major, "year": year}


def val_course_registration(i: int, r: random.Random):
    courses = [("CS", "数据结构", 4), ("EC", "微观经济学", 3), ("BI", "细胞生物学", 3),
               ("CN", "现代汉语专题", 2), ("MA", "概率论", 4)]
    code, title, credits = courses[i % len(courses)]
    sid = f"S26{i:04d}"
    types = ["必修", "选修", "旁听"]
    mode = types[(i // 2) % len(types)]
    rules = ("学生（student）对象含学号（student_id）和姓名（name）；课程（course）对象含课程号（course_code）、"
             "课程名（title）与学分（credits，1至6的整数）；选课类别（registration_type）只能是必修、选修或旁听。")
    facts = f"学号{sid}，学生姓名{['林知夏','周予安','陈嘉树','许清禾'][i%4]}；选择{title}课，课程号{code}{202600+i:06d}，{credits}学分；类别为{mode}。"
    schema = root_schema({"student": obj({"student_id": s(pattern=r"^S[0-9]{6}$"), "name": s()}),
                          "course": obj({"course_code": s(pattern=r"^[A-Z]{2}[0-9]{6}$"), "title": s(), "credits": n(1, 6, True)}),
                          "registration_type": s(choices=types)}, ["student", "course", "registration_type"])
    data = {"student": {"student_id": sid, "name": ["林知夏", "周予安", "陈嘉树", "许清禾"][i % 4]},
            "course": {"course_code": f"{code}{202600+i:06d}", "title": title, "credits": credits}, "registration_type": mode}
    return prompt("课程选课登记", rules, facts, i), schema, data


def val_exam_roster(i: int, r: random.Random):
    ids = [f"S26{(i * 3 + j):04d}" for j in range(3)]
    seats = [1 + (i * 3 + j) % 180 for j in range(3)]
    people = [{"student_id": ids[j], "seat_number": seats[j]} for j in range(3)]
    rules = ("考试编号（exam_code）是字符串；考试日期（exam_date）使用 YYYY-MM-DD；"
             "考生（candidates）是恰好 3 人的数组，每人含学号（student_id，S 后 6 位数字）与座位号（seat_number，1至180整数）。")
    facts = f"考试编号 EX{260+i:05d}，日期{dt(i)}；考生依次为" + "、".join(f"学号{p['student_id']}坐{p['seat_number']}号" for p in people) + "。"
    schema = root_schema({"exam_code": s(pattern=r"^EX[0-9]{5}$"), "exam_date": s(fmt="date"),
                          "candidates": arr(obj({"student_id": s(pattern=r"^S[0-9]{6}$"), "seat_number": n(1, 180, True)}), 3, 3)},
                         ["exam_code", "exam_date", "candidates"])
    return prompt("期末考试考场名单", rules, facts, i), schema, {"exam_code": f"EX{260+i:05d}", "exam_date": dt(i), "candidates": people}


def val_club_event(i: int, r: random.Random):
    kinds = ["讲座", "社团招新", "志愿服务", "作品展览"]
    names = ["青禾读书会", "机器人社", "青年志愿队", "摄影协会", "戏剧社"]
    attendees = [["林知夏", "周予安", "陈嘉树"][((i+j) % 3)] for j in range(3)]
    budget = 120 + (i * 37) % 880
    rules = ("活动名称（event_name）、场地（venue）为字符串；活动日期（event_date）用 YYYY-MM-DD；"
             "活动类型（event_type）限讲座、社团招新、志愿服务、作品展览；报名成员（attendees）必须正好 3 人；"
             "物资预算（supply_budget）为 0 至 1000 的数值。")
    facts = f"{names[i%5]}办{['新生交流夜','校园公益日','春季分享会','社团开放日'][i%4]}，类型{ kinds[i%4] }，{dt(i, date(2026,4,1),2)}在{['学生活动中心','图书馆报告厅','南区草坪'][i%3]}举行；成员为{'、'.join(attendees)}，物资预算{budget}元。"
    schema = root_schema({"event_name": s(), "venue": s(), "event_date": s(fmt="date"), "event_type": s(choices=kinds),
                          "attendees": arr(s(), 3, 3), "supply_budget": n(0, 1000)},
                         ["event_name", "venue", "event_date", "event_type", "attendees", "supply_budget"])
    data = {"event_name": ["新生交流夜", "校园公益日", "春季分享会", "社团开放日"][i % 4],
            "venue": ["学生活动中心", "图书馆报告厅", "南区草坪"][i % 3], "event_date": dt(i, date(2026,4,1),2),
            "event_type": kinds[i % 4], "attendees": attendees, "supply_budget": budget}
    return prompt("学生社团活动备案", rules, facts, i), schema, data


def val_scholarship_application(i: int, r: random.Random):
    docs = ["家庭收入证明", "成绩单", "志愿服务证明"]
    aid = ["是", "否"][i % 2]
    props = {"applicant": obj({"student_id": s(pattern=r"^S[0-9]{6}$"), "name": s(), "gpa": n(0, 4)}),
             "annual_household_income": n(0, 500000), "aid_requested": s(choices=["是", "否"]),
             "aid_documents": arr(s(choices=docs), 1, 2)}
    required = ["applicant", "annual_household_income", "aid_requested"]
    cond = {"if": {"properties": {"aid_requested": {"const": "是"}}, "required": ["aid_requested"]},
            "then": {"required": ["aid_documents"], "properties": {"aid_documents": arr(s(choices=docs), 1, 2)}}}
    rules = ("申请人（applicant）对象含学号（student_id，S 后 6 位数字）、姓名（name）和 GPA（gpa，0至4）；"
             "家庭年收入（annual_household_income）为 0 至 500000 元；是否申请助学金（aid_requested）只能为是或否。"
             "选是时必须提供材料（aid_documents），材料只能是家庭收入证明、成绩单、志愿服务证明中的 1 至 2 项；选否时不要求提供材料字段。")
    sid, name, gpa, income = f"S26{i:04d}", ["林知夏", "周予安", "陈嘉树", "许清禾"][i % 4], round(2.4 + (i % 16) / 10, 1), 18000 + i * 2150
    fact_docs = docs[i % 3:i % 3 + 1] if aid == "是" else []
    facts = f"{name}（{sid}）GPA {gpa}，家庭年收入 {income} 元，助学金申请意向为{aid}" + (f"，已提交{'、'.join(fact_docs)}。" if fact_docs else "。")
    data = {"applicant": {"student_id": sid, "name": name, "gpa": gpa}, "annual_household_income": income, "aid_requested": aid}
    if fact_docs:
        data["aid_documents"] = fact_docs
    schema = root_schema(props, required, **cond)
    return prompt("校内助学金申请", rules, facts, i), schema, data


def val_dining_order(i: int, r: random.Random):
    dishes = ["番茄鸡蛋面", "香菇青菜饭", "咖喱鸡肉饭", "素炒米粉", "牛肉盖饭", "菌菇汤面"]
    first, second = dishes[i % len(dishes)], dishes[(i + 2) % len(dishes)]
    items = [{"dish_name": first, "quantity": 1 + i % 3}, {"dish_name": second, "quantity": 1 + (i + 1) % 3}]
    note = None if i % 3 == 0 else ["不加花生", "少辣", "对虾过敏"][i % 3 - 1]
    rules = ("取餐号（ticket_id）为 D 后接 5 位数字；菜品（menu_items）恰好 2 项，每项含菜名（dish_name）和份数（quantity，1至5整数）；"
             "取餐时间（pickup_time）用 HH:MM:SS；过敏或口味备注（allergy_note）为字符串；没有备注时填写 null，此字段允许 null。")
    facts = f"取餐号 D{i+1:05d}，{first} {items[0]['quantity']}份、{second} {items[1]['quantity']}份，{['11:30:00','12:15:00','17:45:00'][i%3]}取餐；" + (f"备注：{note}。" if note else "没有过敏或口味备注。")
    schema = root_schema({"ticket_id": s(pattern=r"^D[0-9]{5}$"),
                          "menu_items": arr(obj({"dish_name": s(), "quantity": n(1, 5, True)}), 2, 2),
                          "pickup_time": s(fmt="time"), "allergy_note": s(nullable=True)},
                         ["ticket_id", "menu_items", "pickup_time", "allergy_note"])
    return prompt("校园食堂预订取餐", rules, facts, i), schema, {"ticket_id": f"D{i+1:05d}", "menu_items": items,
            "pickup_time": ["11:30:00", "12:15:00", "17:45:00"][i % 3], "allergy_note": note}


def val_dorm_repair(i: int, r: random.Random):
    props = {"request_id": s(pattern=r"^R[0-9]{4}$"), "building": s(), "room": s(), "issue": s(),
             "priority": s(choices=["普通", "紧急"]), "resident_name": s(), "resident_phone": s(pattern=r"^1[0-9]{10}$")}
    name = ["林知夏", "周予安", "陈嘉树", "许清禾"][i % 4]
    include = i % 2 == 0
    priority = ["普通", "紧急"][i % 2]
    rules = ("报修编号（request_id）为 R 后 4 位数字；楼宇（building）、房间号（room）、问题描述（issue）为字符串；"
             "优先级（priority）只能为普通或紧急。住户姓名（resident_name）和联系电话（resident_phone）都可省略；"
             "若填写姓名就必须同时填写电话，电话为 11 位且以 1 开头。")
    facts = f"编号 R{i+1:04d}，{['东苑','西苑','梧桐公寓'][i%3]} {['3-201','5-408','2-116'][i%3]}，{['水龙头漏水','空调无法启动','门锁松动','照明灯闪烁'][i%4]}，{priority}处理。"
    data = {"request_id": f"R{i+1:04d}", "building": ["东苑", "西苑", "梧桐公寓"][i % 3],
            "room": ["3-201", "5-408", "2-116"][i % 3], "issue": ["水龙头漏水", "空调无法启动", "门锁松动", "照明灯闪烁"][i % 4], "priority": priority}
    if include:
        phone = f"138{i:08d}"
        data.update({"resident_name": name, "resident_phone": phone})
        facts += f"报修人{name}，联系电话{phone}。"
    else:
        facts += "由宿管代为登记，没有提供住户姓名和电话。"
    schema = root_schema(props, ["request_id", "building", "room", "issue", "priority"],
                         dependentRequired={"resident_name": ["resident_phone"]})
    return prompt("宿舍设施报修", rules, facts, i), schema, data


def val_experiment_log(i: int, r: random.Random):
    samples = [{"sample_code": f"P{i+1:03d}-{j+1}", "temperature_c": round(18 + ((i * 7 + j * 11) % 80) / 2, 1),
                "ph": round(4 + ((i * 3 + j * 5) % 100) / 10, 1)} for j in range(2)]
    rules = ("实验编号（experiment_id）和实验室（laboratory）为字符串；实验日期（experiment_date）用 YYYY-MM-DD；"
             "记录人（recorded_by）为字符串。样本测量（samples）恰好 2 项，每项含样本码（sample_code）、"
             "温度（temperature_c，-20至60数值）和酸碱度（ph，0至14数值）。")
    facts = f"编号 LAB-{i+1:04d}，在{['材料实验室','环境实验室','食品实验室'][i%3]}于{dt(i,date(2026,5,1))}由{['赵老师','刘助教','王研究员'][i%3]}记录；" + "；".join(f"{x['sample_code']}温度{x['temperature_c']}摄氏度、pH {x['ph']}" for x in samples) + "。"
    schema = root_schema({"experiment_id": s(pattern=r"^LAB-[0-9]{4}$"), "laboratory": s(), "experiment_date": s(fmt="date"),
                          "recorded_by": s(), "samples": arr(obj({"sample_code": s(pattern=r"^P[0-9]{3}-[12]$"),
                          "temperature_c": n(-20, 60), "ph": n(0, 14)}), 2, 2)},
                         ["experiment_id", "laboratory", "experiment_date", "recorded_by", "samples"])
    data = {"experiment_id": f"LAB-{i+1:04d}", "laboratory": ["材料实验室", "环境实验室", "食品实验室"][i%3],
            "experiment_date": dt(i,date(2026,5,1)), "recorded_by": ["赵老师", "刘助教", "王研究员"][i%3], "samples": samples}
    return prompt("本科实验测量日志", rules, facts, i), schema, data


def val_internship_offer(i: int, r: random.Random):
    modes = ["现场", "远程"]
    mode = modes[i % 2]
    props = {"candidate_name": s(), "company": s(), "work_mode": s(choices=modes), "office_address": s(), "work_timezone": s()}
    rules = ("候选人姓名（candidate_name）和公司（company）为字符串；工作方式（work_mode）只能为现场或远程。"
             "现场岗位必须提供办公地址（office_address）；远程岗位必须提供工作时区（work_timezone）。未触发的分支字段不要求提供。")
    name, company = ["林知夏", "周予安", "陈嘉树", "许清禾"][i%4], ["澄海数据", "青岚科技", "远帆咨询"][i%3]
    facts = f"{name}收到{company}的实习录用，工作方式是{mode}；" + (f"办公地点为{['科创园A座','大学科技园2号楼','滨江中心'][i%3]}。" if mode == "现场" else f"团队按{'Asia/Shanghai','Asia/Tokyo','Asia/Singapore'}之一的时区协作。")
    data = {"candidate_name": name, "company": company, "work_mode": mode}
    if mode == "现场":
        data["office_address"] = ["科创园A座", "大学科技园2号楼", "滨江中心"][i%3]
    else:
        data["work_timezone"] = ["Asia/Shanghai", "Asia/Tokyo", "Asia/Singapore"][i%3]
    cond = {"if": {"properties": {"work_mode": {"const": "现场"}}, "required": ["work_mode"]},
            "then": {"required": ["office_address"]}, "else": {"required": ["work_timezone"]}}
    schema = root_schema(props, ["candidate_name", "company", "work_mode"], **cond)
    return prompt("大学生实习录用通知", rules, facts, i), schema, data


def val_library_return(i: int, r: random.Random):
    books = [{"barcode": f"B{i*2+j+1:07d}", "title": ["百年孤独", "算法导论", "乡土中国", "人类简史", "统计学习方法"][((i+j)%5)]} for j in range(2)]
    overdue = i % 31
    rules = ("借阅人编号（borrower_id）为字符串；归还日期（return_date）用 YYYY-MM-DD；"
             "归还图书（returned_books）恰好 2 本，每本含条码（barcode，B 后 7 位数字）和书名（title）；"
             "逾期天数（overdue_days）为 0 至 30 的整数。")
    facts = f"读者 U{i+1:06d} 于{dt(i,date(2026,6,1))}归还" + "、".join(f"《{b['title']}》（{b['barcode']}）" for b in books) + f"，逾期{overdue}天。"
    schema = root_schema({"borrower_id": s(pattern=r"^U[0-9]{6}$"), "return_date": s(fmt="date"),
                          "returned_books": arr(obj({"barcode": s(pattern=r"^B[0-9]{7}$"), "title": s()}), 2, 2),
                          "overdue_days": n(0, 30, True)}, ["borrower_id", "return_date", "returned_books", "overdue_days"])
    data = {"borrower_id": f"U{i+1:06d}", "return_date": dt(i,date(2026,6,1)), "returned_books": books, "overdue_days": overdue}
    return prompt("图书馆集中归还登记", rules, facts, i), schema, data


def val_student_trip(i: int, r: random.Random):
    contact = None if i % 4 == 0 else f"{['138','139','136'][i%3]}{i:08d}"
    routes = [("杭州", "南京"), ("成都", "重庆"), ("苏州", "上海"), ("武汉", "长沙"), ("厦门", "福州")]
    origin, destination = routes[i % len(routes)]
    cost = 260 + i * 48
    rules = ("行程编号（trip_id）、出发地（origin）、目的地（destination）和出行目的（purpose）为字符串；"
             "出发日期（departure_date）用 YYYY-MM-DD；预计费用（estimated_cost）为 0 至 20000 元数值；"
             "紧急联系人电话（emergency_phone）必须填写，若无联系人则填 null，且该字段允许 null。")
    facts = f"行程 T{i+1:05d}：{origin}前往{destination}，{dt(i,date(2026,7,1))}出发，目的是{['参加学术会议','暑期实践','校际交流','志愿服务'][i%4]}，预算{cost}元；" + (f"紧急联系人电话{contact}。" if contact else "没有紧急联系人电话。")
    schema = root_schema({"trip_id": s(pattern=r"^T[0-9]{5}$"), "origin": s(), "destination": s(), "departure_date": s(fmt="date"),
                          "purpose": s(), "estimated_cost": n(0, 20000), "emergency_phone": s(pattern=r"^1[0-9]{10}$", nullable=True)},
                         ["trip_id", "origin", "destination", "departure_date", "purpose", "estimated_cost", "emergency_phone"])
    data = {"trip_id": f"T{i+1:05d}", "origin": origin, "destination": destination, "departure_date": dt(i,date(2026,7,1)),
            "purpose": ["参加学术会议", "暑期实践", "校际交流", "志愿服务"][i%4], "estimated_cost": cost, "emergency_phone": contact}
    return prompt("高校学生外出实践行程", rules, facts, i), schema, data


def val_peer_tutoring(i: int, r: random.Random):
    online = i % 2 == 1
    subjects = ["高等数学", "英语写作", "程序设计", "经济学原理"]
    props = {"tutor_id": s(pattern=r"^TUT[0-9]{4}$"), "subject": s(choices=subjects), "weekly_hours": n(0.5, 12),
             "sessions": arr(obj({"session_date": s(fmt="date"), "start_time": s(fmt="time")}), 2, 2),
             "online_platform": s(choices=["腾讯会议", "Zoom", "校内课堂"]), "meeting_url": s()}
    required = ["tutor_id", "subject", "weekly_hours", "sessions"]
    rules = ("导师编号（tutor_id）为 TUT 后 4 位数字；辅导科目（subject）只能是高等数学、英语写作、程序设计、经济学原理；"
             "每周课时（weekly_hours）为 0.5 至 12；辅导时段（sessions）恰好 2 项，每项含日期（session_date，YYYY-MM-DD）和开始时间（start_time，HH:MM:SS）。"
             "线上辅导可填写平台（online_platform），但一旦填写平台就必须提供会议链接（meeting_url）；线下辅导可不提供这两个字段。")
    sessions = [{"session_date": dt(i*2+j,date(2026,8,1)), "start_time": ["16:00:00", "18:30:00"][j]} for j in range(2)]
    hours = round(1 + (i % 20) / 2, 1)
    facts = f"导师 TUT{i+1:04d} 辅导{subjects[i%4]}，每周{hours}小时，安排在" + "和".join(f"{x['session_date']} {x['start_time']}" for x in sessions) + "。"
    data = {"tutor_id": f"TUT{i+1:04d}", "subject": subjects[i%4], "weekly_hours": hours, "sessions": sessions}
    if online:
        platform = ["腾讯会议", "Zoom", "校内课堂"][i%3]
        url = f"https://meet.example.edu/tutoring/{i+1:04d}"
        data.update({"online_platform": platform, "meeting_url": url})
        facts += f"本次为线上辅导，使用{platform}，会议链接为{url}。"
    else:
        facts += "本次在线下教室进行。"
    schema = root_schema(props, required, dependentRequired={"online_platform": ["meeting_url"]})
    return prompt("同伴辅导排课记录", rules, facts, i), schema, data


VAL_FAMILIES = [
    family("val_campus_identity", "validation", ["ordinary", "college", "enum", "pattern", "range"], "校园学生身份", val_campus_identity),
    family("val_course_registration", "validation", ["ordinary", "college", "nested", "enum", "range"], "课程选课登记", val_course_registration),
    family("val_exam_roster", "validation", ["ordinary", "college", "array_count", "format", "pattern", "range"], "期末考试考场名单", val_exam_roster),
    family("val_club_event", "validation", ["ordinary", "college", "array_count", "enum", "range", "format"], "学生社团活动备案", val_club_event),
    family("val_scholarship_application", "validation", ["combination", "college", "nested", "conditional", "enum", "range", "array"], "校内助学金申请", val_scholarship_application),
    family("val_dining_order", "validation", ["combination", "college", "nested", "array_count", "range", "format", "nullable"], "校园食堂预订取餐", val_dining_order),
    family("val_dorm_repair", "validation", ["combination", "college", "dependent_required", "enum", "pattern", "optional"], "宿舍设施报修", val_dorm_repair),
    family("val_experiment_log", "validation", ["combination", "college", "nested", "array_count", "format", "range", "pattern"], "本科实验测量日志", val_experiment_log),
    family("val_internship_offer", "validation", ["combination", "college", "conditional", "enum", "optional"], "大学生实习录用通知", val_internship_offer),
    family("val_library_return", "validation", ["ordinary", "college", "nested", "array_count", "format", "range", "pattern"], "图书馆集中归还登记", val_library_return),
    family("val_student_trip", "validation", ["combination", "college", "format", "range", "pattern", "nullable"], "高校学生外出实践行程", val_student_trip),
    family("val_peer_tutoring", "validation", ["combination", "college", "nested", "array_count", "format", "range", "dependent_required", "enum"], "同伴辅导排课记录", val_peer_tutoring),
]


# Business-focused evaluation families continue below.


def test_customer_quote(i: int, r: random.Random):
    services = ["数据迁移", "品牌设计", "门店培训", "云资源托管", "供应链咨询"]
    items = [{"service": services[i % 5], "quantity": 1 + i % 4, "unit_price": 800 + i * 37},
             {"service": services[(i + 2) % 5], "quantity": 1 + (i + 1) % 3, "unit_price": 1200 + i * 29}]
    status = ["草稿", "已发送", "已接受"][i % 3]
    rules = ("报价编号（quote_id）为 Q 后 6 位数字；客户（customer）对象含客户编号（customer_id）和公司名（company_name）。"
             "服务项目（line_items）恰好 2 项，每项含服务名称（service）、数量（quantity，1至12整数）和单价（unit_price，100至20000元数值）；"
             "报价状态（quote_status）只能是草稿、已发送、已接受；有效期（valid_until）用 YYYY-MM-DD。")
    facts = f"报价 Q{i+1:06d} 给客户 C{i+1:05d}（{['海棠零售','远帆制造','青岚医疗','澄海物流'][i%4]}），提供" + "及".join(f"{x['service']} {x['quantity']}份、单价{x['unit_price']}元" for x in items) + f"；状态{status}，有效至{dt(i,date(2026,9,1))}。"
    schema = root_schema({"quote_id": s(pattern=r"^Q[0-9]{6}$"),
                          "customer": obj({"customer_id": s(pattern=r"^C[0-9]{5}$"), "company_name": s()}),
                          "line_items": arr(obj({"service": s(), "quantity": n(1, 12, True), "unit_price": n(100, 20000)}), 2, 2),
                          "quote_status": s(choices=["草稿", "已发送", "已接受"]), "valid_until": s(fmt="date")},
                         ["quote_id", "customer", "line_items", "quote_status", "valid_until"])
    data = {"quote_id": f"Q{i+1:06d}", "customer": {"customer_id": f"C{i+1:05d}", "company_name": ["海棠零售", "远帆制造", "青岚医疗", "澄海物流"][i%4]},
            "line_items": items, "quote_status": status, "valid_until": dt(i,date(2026,9,1))}
    return prompt("企业服务报价单", rules, facts, i), schema, data


def test_sales_contract_order(i: int, r: random.Random):
    skus = [f"SKU-{(i*2+j+1):06d}" for j in range(2)]
    lines = [{"sku": skus[j], "quantity": 2 + (i+j) % 12, "unit_price": 18.5 + i * (j+1) * 7.25} for j in range(2)]
    terms = ["月结30天", "预付50%", "发货前全款"][i%3]
    rules = ("合同订单号（order_id）为 ORD 后 6 位数字；买方（buyer）对象含公司名（company_name）与税号（tax_id，15位字母数字）。"
             "订单行（items）必须恰好 2 行，每行含 SKU（sku，SKU-后 6 位数字）、数量（quantity，1至20整数）和单价（unit_price，10至50000元数值）；"
             "交付日期（delivery_date）为 YYYY-MM-DD；付款条款（payment_terms）限月结30天、预付50%、发货前全款。")
    facts = f"订单 ORD{i+1:06d}，买方{['海棠零售','远帆制造','青岚医疗'][i%3]}，税号 A1B2C3D4E5F6G7H；采购" + "、".join(f"{x['sku']} {x['quantity']}件，每件{x['unit_price']}元" for x in lines) + f"；交付日{dt(i,date(2026,10,1))}，条款{terms}。"
    schema = root_schema({"order_id": s(pattern=r"^ORD[0-9]{6}$"),
                          "buyer": obj({"company_name": s(), "tax_id": s(pattern=r"^[A-Z0-9]{15}$")}),
                          "items": arr(obj({"sku": s(pattern=r"^SKU-[0-9]{6}$"), "quantity": n(1,20,True), "unit_price": n(10,50000)}),2,2),
                          "delivery_date": s(fmt="date"), "payment_terms": s(choices=["月结30天","预付50%","发货前全款"])},
                         ["order_id","buyer","items","delivery_date","payment_terms"])
    data = {"order_id": f"ORD{i+1:06d}", "buyer": {"company_name": ["海棠零售","远帆制造","青岚医疗"][i%3], "tax_id":"A1B2C3D4E5F6G7H"},
            "items": lines, "delivery_date": dt(i,date(2026,10,1)), "payment_terms": terms}
    return prompt("销售合同订单", rules, facts, i), schema, data


def test_vendor_invoice_payment(i: int, r: random.Random):
    methods = ["银行转账", "信用卡"]
    method = methods[i % 2]
    amount = round(250.50 + i * 318.75, 2)
    props = {"invoice_id": s(pattern=r"^INV[0-9]{6}$"), "vendor_name": s(), "amount": n(0.01, 500000),
             "payment_method": s(choices=methods), "bank_reference": s(pattern=r"^BR[0-9]{8}$"), "card_last4": s(pattern=r"^[0-9]{4}$")}
    rules = ("发票编号（invoice_id）为 INV 后 6 位数字；供应商（vendor_name）为字符串；金额（amount）为 0.01 至 500000 元数值；"
             "付款方式（payment_method）只能为银行转账或信用卡。银行转账时必须给银行流水号（bank_reference，BR 后 8 位数字），信用卡时必须给卡号末四位（card_last4）；另一种付款凭据字段不要求提供。")
    facts = f"发票 INV{i+1:06d} 来自{['远帆制造','澄海物流','青岚医疗'][i%3]}，金额{amount:.2f}元，采用{method}。"
    data = {"invoice_id": f"INV{i+1:06d}", "vendor_name": ["远帆制造","澄海物流","青岚医疗"][i%3], "amount": amount, "payment_method": method}
    if method == "银行转账":
        data["bank_reference"] = f"BR{i+1:08d}"
        facts += f"银行流水号为 BR{i+1:08d}。"
    else:
        data["card_last4"] = f"{(i*37+1234)%10000:04d}"
        facts += f"信用卡末四位为 {data['card_last4']}。"
    conditional = {"if": {"properties":{"payment_method":{"const":"银行转账"}},"required":["payment_method"]},
                   "then":{"required":["bank_reference"]},"else":{"required":["card_last4"]}}
    schema = root_schema(props,["invoice_id","vendor_name","amount","payment_method"],**conditional)
    return prompt("供应商发票付款登记", rules, facts, i), schema, data


def test_warehouse_pick_pack(i: int, r: random.Random):
    packages = []
    for j in range(3):
        packages.append({"tracking_code": f"TRK{i*3+j+1:08d}", "sku": f"SKU-{(i*3+j+1):06d}", "units": 1+(i+j)%25})
    rules = ("出库单号（shipment_id）为 SH 后 6 位数字；仓库（warehouse）为字符串。"
             "包裹（packages）必须恰好 3 件，每件包含物流单号（tracking_code，TRK 后 8 位数字）、SKU（sku，SKU-后 6 位数字）和件数（units，1至25整数）；"
             "出库日期（ship_date）用 YYYY-MM-DD。")
    facts = f"出库单 SH{i+1:06d} 从{['华东一号仓','华南冷链仓','成都中心仓'][i%3]}于{dt(i,date(2026,10,15))}发出；" + "；".join(f"物流单号{x['tracking_code']}承运{x['sku']} {x['units']}件" for x in packages) + "。"
    schema = root_schema({"shipment_id":s(pattern=r"^SH[0-9]{6}$"),"warehouse":s(),"ship_date":s(fmt="date"),
                          "packages":arr(obj({"tracking_code":s(pattern=r"^TRK[0-9]{8}$"),"sku":s(pattern=r"^SKU-[0-9]{6}$"),"units":n(1,25,True)}),3,3)},
                         ["shipment_id","warehouse","ship_date","packages"])
    data = {"shipment_id":f"SH{i+1:06d}","warehouse":["华东一号仓","华南冷链仓","成都中心仓"][i%3],"ship_date":dt(i,date(2026,10,15)),"packages":packages}
    return prompt("仓库拣货出库单",rules,facts,i),schema,data


def test_employee_onboarding(i: int, r: random.Random):
    dept=["财务部","产品部","客户成功部","供应链部"]
    email=None if i%4==0 else f"manager{i%17+1}@example.com"
    rules=("员工编号（employee_id）为 E 后 6 位数字；员工姓名（name）和部门（department）为字符串；"
           "入职日期（start_date）用 YYYY-MM-DD；合同类型（contract_type）限正式、实习、外包；"
           "直属经理邮箱（manager_email）必须填写，未分配经理时写 null；字段允许 null，非空时须为 email 格式。")
    facts=f"员工 E{i+1:06d}，姓名{['林知夏','周予安','陈嘉树','许清禾'][i%4]}，加入{dept[i%4]}，{dt(i,date(2026,11,1))}入职，签{['正式','实习','外包'][i%3]}合同；"+(f"经理邮箱{email}。" if email else "暂未分配直属经理。")
    schema=root_schema({"employee_id":s(pattern=r"^E[0-9]{6}$"),"name":s(),"department":s(),"start_date":s(fmt="date"),
                        "contract_type":s(choices=["正式","实习","外包"]),"manager_email":s(fmt="email",nullable=True)},
                       ["employee_id","name","department","start_date","contract_type","manager_email"])
    data={"employee_id":f"E{i+1:06d}","name":["林知夏","周予安","陈嘉树","许清禾"][i%4],"department":dept[i%4],"start_date":dt(i,date(2026,11,1)),
          "contract_type":["正式","实习","外包"][i%3],"manager_email":email}
    return prompt("企业员工入职建档",rules,facts,i),schema,data


def test_recruiting_candidate(i: int, r: random.Random):
    contact_is_email=i%2==0
    props={"candidate_id":s(pattern=r"^CAN[0-9]{5}$"),"name":s(),"position":s(),"contact_email":s(fmt="email"),"contact_phone":s(pattern=r"^1[0-9]{10}$")}
    rules=("候选人编号（candidate_id）为 CAN 后 5 位数字；姓名（name）和应聘岗位（position）为字符串。"
           "联系方式（contact_email 邮箱、contact_phone 手机号）必须且只能填写一个；邮箱须符合 email 格式，手机号为 11 位且以 1 开头。")
    name=["沈一诺","唐可心","顾明远","宋雨桐"][i%4]
    data={"candidate_id":f"CAN{i+1:05d}","name":name,"position":["数据分析师","区域销售","测试工程师","采购专员"][i%4]}
    facts=f"候选人 CAN{i+1:05d}，{name}，申请{data['position']}；"
    if contact_is_email:
        email=f"candidate{i+1:03d}@example.com";data["contact_email"]=email;facts+=f"联系邮箱为{email}。"
    else:
        phone=f"139{i+1:08d}";data["contact_phone"]=phone;facts+=f"联系电话为{phone}。"
    exactly_one={"oneOf":[{"required":["contact_email"]},{"required":["contact_phone"]}]}
    schema=root_schema(props,["candidate_id","name","position"],**exactly_one)
    return prompt("企业招聘候选人登记",rules,facts,i),schema,data


def test_product_catalog(i: int, r: random.Random):
    categories=["办公设备","工业传感器","家用电器","网络配件"]
    price=round(25.5+i*82.75,2)
    dimensions={"width_cm":round(4.0+i%19,1),"height_cm":round(3.0+(i*2)%32,1),"depth_cm":round(2.0+(i*3)%28,1)}
    props={"product_id":s(pattern=r"^PDT[0-9]{6}$"),"name":s(),"category":s(choices=categories),"unit_price":n(),
           "dimensions":obj({"width_cm":n(1,100),"height_cm":n(1,100),"depth_cm":n(1,100)})}
    all_of=[{"properties":{"unit_price":{"minimum":5}}},{"properties":{"unit_price":{"maximum":5000}}}]
    rules=("商品编号（product_id）为 PDT 后 6 位数字；商品名（name）为字符串；品类（category）限办公设备、工业传感器、家用电器、网络配件；"
           "单价（unit_price）为 5 至 5000 元数值。尺寸（dimensions）对象含宽（width_cm）、高（height_cm）、深（depth_cm），三项都是 1 至 100 厘米的数值。")
    facts=f"商品 PDT{i+1:06d}「{['便携显示器','温湿度探头','静音净化器','千兆交换机'][i%4]}」，品类{categories[i%4]}，售价{price}元，尺寸宽{dimensions['width_cm']}厘米、高{dimensions['height_cm']}厘米、深{dimensions['depth_cm']}厘米。"
    schema=root_schema(props,["product_id","name","category","unit_price","dimensions"],allOf=all_of)
    data={"product_id":f"PDT{i+1:06d}","name":["便携显示器","温湿度探头","静音净化器","千兆交换机"][i%4],"category":categories[i%4],"unit_price":price,"dimensions":dimensions}
    return prompt("商品目录上架信息",rules,facts,i),schema,data


def test_monthly_forecast(i: int, r: random.Random):
    metrics=["签约收入","新客数","续费金额"]
    projections=[{"metric":metrics[j],"forecast_value":round(10000+(i*1937)+(j*5250),2)} for j in range(3)]
    month=date(2026,1,1)+timedelta(days=28*(i%12)); period=month.replace(day=1).isoformat()
    props={"forecast_id":s(pattern=r"^FC[0-9]{6}$"),"period":s(fmt="date"),"department":s(),
           "projections":arr(obj({"metric":s(choices=metrics),"forecast_value":n(0,10000000)}),3,3),
           "confidence":s(choices=["低","中","高"])}
    rules=("预测编号（forecast_id）为 FC 后 6 位数字；预测月份（period）用该月第一天的 YYYY-MM-DD 表示；部门（department）为字符串。"
           "预测项目（projections）恰好 3 项，每项含指标（metric，签约收入、新客数、续费金额之一）和预测值（forecast_value，0至10000000数值）；"
           "把握度（confidence）限低、中、高。")
    facts=f"预测 FC{i+1:06d}，月份{period[:7]}，部门{['销售部','客户成功部','电商部'][i%3]}；"+"；".join(f"{x['metric']}预测{x['forecast_value']}" for x in projections)+f"；把握度{['低','中','高'][i%3]}。"
    schema=root_schema(props,["forecast_id","period","department","projections","confidence"])
    data={"forecast_id":f"FC{i+1:06d}","period":period,"department":["销售部","客户成功部","电商部"][i%3],"projections":projections,"confidence":["低","中","高"][i%3]}
    return prompt("部门月度经营预测",rules,facts,i),schema,data


def test_support_case(i: int, r: random.Random):
    priorities=["普通","紧急"]
    priority=priorities[i%2]
    props={"case_id":s(pattern=r"^CASE[0-9]{6}$"),"customer_id":s(pattern=r"^C[0-9]{5}$"),
           "issue_type":s(choices=["登录故障","账单疑问","数据导出","权限申请"]),"priority":s(choices=priorities),
           "description":s(),"callback_time":s(fmt="time")}
    rules=("工单号（case_id）为 CASE 后 6 位数字；客户编号（customer_id）为 C 后 5 位数字；"
           "问题类型（issue_type）限登录故障、账单疑问、数据导出、权限申请；优先级（priority）限普通或紧急；描述（description）为字符串。"
           "紧急工单必须提供回电时间（callback_time，HH:MM:SS）；普通工单不要求填写该字段。")
    issue=["登录后页面持续报错","账单中的税额需要说明","导出按钮没有反应","新同事需要只读权限"][i%4]
    facts=f"工单 CASE{i+1:06d} 属于客户 C{i+1:05d}，问题类型{["登录故障","账单疑问","数据导出","权限申请"][i%4]}，优先级{priority}，描述：{issue}。"
    data={"case_id":f"CASE{i+1:06d}","customer_id":f"C{i+1:05d}","issue_type":["登录故障","账单疑问","数据导出","权限申请"][i%4],"priority":priority,"description":issue}
    if priority=="紧急":
        data["callback_time"]=["09:30:00","13:15:00","16:45:00"][i%3];facts+=f"请在{data['callback_time']}回电。"
    condition={"if":{"properties":{"priority":{"const":"紧急"}},"required":["priority"]},"then":{"required":["callback_time"]}}
    schema=root_schema(props,["case_id","customer_id","issue_type","priority","description"],**condition)
    return prompt("SaaS 客服问题工单",rules,facts,i),schema,data


def test_refund_claim(i: int, r: random.Random):
    methods=["门店退货","快递寄回"]
    method=methods[i%2]
    props={"claim_id":s(pattern=r"^RF[0-9]{6}$"),"order_id":s(pattern=r"^ORD[0-9]{6}$"),
           "reason":s(choices=["尺寸不合","重复购买","到货破损"]),"refund_amount":n(0.01,10000),
           "return_method":s(choices=methods),"return_tracking":s(pattern=r"^RET[0-9]{8}$"),"requested_at":s(fmt="date-time")}
    amount=round(99.9+i*23.4,2)
    rules=("退款申请号（claim_id）为 RF 后 6 位数字；订单号（order_id）为 ORD 后 6 位数字；"
           "原因（reason）限尺寸不合、重复购买、到货破损；退款金额（refund_amount）为 0.01 至 10000 元数值；"
           "申请时间（requested_at）用带时区的 YYYY-MM-DDTHH:MM:SS+08:00；退货方式（return_method）限门店退货或快递寄回。"
           "快递寄回时必须提供退货物流号（return_tracking，RET 后 8 位数字）；门店退货时不要求填写物流号。")
    instant=f"{dt(i,date(2026,2,1))}T{['09:10:00','11:25:00','15:40:00'][i%3]}+08:00"
    facts=f"申请 RF{i+1:06d} 对订单 ORD{i+1:06d} 退款，原因{['尺寸不合','重复购买','到货破损'][i%3]}，金额{amount}元，{instant}提交，选择{method}。"
    data={"claim_id":f"RF{i+1:06d}","order_id":f"ORD{i+1:06d}","reason":["尺寸不合","重复购买","到货破损"][i%3],"refund_amount":amount,"return_method":method,"requested_at":instant}
    if method=="快递寄回":data["return_tracking"]=f"RET{i+1:08d}";facts+=f"退货物流号为 RET{i+1:08d}。"
    condition={"if":{"properties":{"return_method":{"const":"快递寄回"}},"required":["return_method"]},"then":{"required":["return_tracking"]}}
    schema=root_schema(props,["claim_id","order_id","reason","refund_amount","return_method","requested_at"],**condition)
    return prompt("电商售后退款申请",rules,facts,i),schema,data


def test_campaign_brief(i: int, r: random.Random):
    channels=["公众号","短视频","搜索广告","线下展会"]
    chosen=[channels[i%4],channels[(i+1)%4]]
    budget=5000+i*4250
    lo=18+i%20;hi=45+(i%36)
    rules=("活动编号（campaign_id）为 CMP 后 6 位数字；活动名称（campaign_name）为字符串；"
           "投放渠道（channels）须为 2 至 3 个，且每项只能是公众号、短视频、搜索广告、线下展会；"
           "总预算（budget）为 1000 至 200000 元数值；目标年龄下限（min_age）为 18 至 80 的整数，上限（max_age）为 18 至 90 的整数。")
    facts=f"活动 CMP{i+1:06d}「{['春季上新','会员回馈','新品体验','年中促销'][i%4]}」，渠道为{'和'.join(chosen)}，预算{budget}元，目标人群{lo}至{hi}岁。"
    schema=root_schema({"campaign_id":s(pattern=r"^CMP[0-9]{6}$"),"campaign_name":s(),"channels":arr(s(choices=channels),2,3),
                        "budget":n(1000,200000),"min_age":n(18,80,True),"max_age":n(18,90,True)},
                       ["campaign_id","campaign_name","channels","budget","min_age","max_age"])
    data={"campaign_id":f"CMP{i+1:06d}","campaign_name":["春季上新","会员回馈","新品体验","年中促销"][i%4],"channels":chosen,"budget":budget,"min_age":lo,"max_age":hi}
    return prompt("市场营销活动简报",rules,facts,i),schema,data


def test_supplier_qualification(i: int, r: random.Random):
    has_tax=i%2==0
    props={"supplier_id":s(pattern=r"^SUP[0-9]{5}$"),"company_name":s(),"service_category":s(choices=["物流","包装","云服务","办公用品"]),
           "contact_email":s(fmt="email"),"contact_phone":s(pattern=r"^1[0-9]{10}$"),
           "tax_id":s(pattern=r"^[A-Z0-9]{15}$"),"tax_region":s()}
    rules=("供应商编号（supplier_id）为 SUP 后 5 位数字；公司名（company_name）为字符串；"
           "服务类别（service_category）限物流、包装、云服务、办公用品。联系邮箱（contact_email）和电话（contact_phone）至少提供一项，"
           "可同时提供；邮箱为 email 格式，电话为 11 位且以 1 开头。税号（tax_id）和税务登记地区（tax_region）均可省略；"
           "一旦提供税号就必须同时提供登记地区，税号为 15 位字母数字。")
    company=["远帆制造","澄海物流","青岚科技","北辰包装"][i%4]
    facts=f"供应商 SUP{i+1:05d}「{company}」提供{['物流','包装','云服务','办公用品'][i%4]}。"
    data={"supplier_id":f"SUP{i+1:05d}","company_name":company,"service_category":["物流","包装","云服务","办公用品"][i%4]}
    if i%2==0:
        email=f"supplier{i+1:03d}@example.com";data["contact_email"]=email;facts+=f"联系邮箱为{email}。"
    else:
        phone=f"136{i+1:08d}";data["contact_phone"]=phone;facts+=f"联系电话为{phone}。"
    if has_tax:
        tax="A1B2C3D4E5F6G7H";region=["浙江省杭州市","江苏省苏州市","广东省深圳市"][i%3]
        data.update({"tax_id":tax,"tax_region":region});facts+=f"税号{tax}，税务登记地{region}。"
    else:facts+="暂未提供税号及税务登记地区。"
    schema=root_schema(props,["supplier_id","company_name","service_category"],
                       anyOf=[{"required":["contact_email"]},{"required":["contact_phone"]}],
                       dependentRequired={"tax_id":["tax_region"]})
    return prompt("企业供应商资质登记",rules,facts,i),schema,data


def test_meeting_minutes(i: int, r: random.Random):
    attendees=[f"{['林知夏','周予安','陈嘉树','许清禾','沈一诺'][(i+j)%5]}（{['销售','产品','财务','运营','技术'][(i+j)%5]}）" for j in range(3)]
    actions=[{"owner":["周予安","陈嘉树"][i%2],"task":["整理客户问题清单","核对预算明细","提交新版排期"][i%3],"due_date":dt(i,date(2026,9,10))},
             {"owner":["许清禾","沈一诺"][i%2],"task":["准备演示环境","补充风险说明","更新合同附件"][i%3],"due_date":dt(i+3,date(2026,9,10))}]
    instant=f"{dt(i,date(2026,8,1))}T{['09:00:00','14:00:00','16:30:00'][i%3]}+08:00"
    rules=("会议编号（meeting_id）为 MTG 后 6 位数字；主题（topic）为字符串；开始时间（starts_at）用带 +08:00 时区的 YYYY-MM-DDTHH:MM:SS+08:00。"
           "参会人（attendees）恰好 3 人，按原顺序保存；行动项（action_items）恰好 2 条，每条含负责人（owner）、任务（task）和截止日期（due_date，YYYY-MM-DD）。")
    facts=f"会议 MTG{i+1:06d} 讨论{['华东客户续约','季度产品发布','渠道成本调整'][i%3]}，开始于{instant}；参会者依次为{'、'.join(attendees)}；"+"；".join(f"{x['owner']}负责{x['task']}，截止{x['due_date']}" for x in actions)+"。"
    schema=root_schema({"meeting_id":s(pattern=r"^MTG[0-9]{6}$"),"topic":s(),"starts_at":s(fmt="date-time"),"attendees":arr(s(),3,3),
                        "action_items":arr(obj({"owner":s(),"task":s(),"due_date":s(fmt="date")}),2,2)},
                       ["meeting_id","topic","starts_at","attendees","action_items"])
    data={"meeting_id":f"MTG{i+1:06d}","topic":["华东客户续约","季度产品发布","渠道成本调整"][i%3],"starts_at":instant,"attendees":attendees,"action_items":actions}
    return prompt("跨部门项目会议纪要",rules,facts,i),schema,data


def test_business_travel_claim(i: int, r: random.Random):
    expenses=[{"category":"交通","amount":round(88.5+i*15.7,2)},{"category":"住宿","amount":round(320+i*24.3,2)}]
    total=round(sum(x["amount"] for x in expenses),2)
    routes=[("上海","北京"),("深圳","武汉"),("杭州","成都"),("南京","西安")]
    origin,dest=routes[i%4]
    rules=("报销编号（claim_id）为 TRC 后 6 位数字；员工（employee）对象含编号（employee_id，E 后 6 位数字）和姓名（name）；"
           "出差起止日期（start_date、end_date）均用 YYYY-MM-DD；城市（origin、destination）为字符串。"
           "费用明细（expenses）恰好 2 项，每项类别（category）限交通或住宿，金额（amount）为 0 至 20000 元数值；"
           "报销总额（total_amount）为 0 至 50000 元数值。")
    name=["林知夏","周予安","陈嘉树","许清禾"][i%4]
    facts=f"报销 TRC{i+1:06d} 属于员工 E{i+1:06d} {name}，从{origin}到{dest}出差，{dt(i,date(2026,10,2))}至{dt(i+2,date(2026,10,2))}；交通{expenses[0]['amount']}元、住宿{expenses[1]['amount']}元，总额{total}元。"
    schema=root_schema({"claim_id":s(pattern=r"^TRC[0-9]{6}$"),"employee":obj({"employee_id":s(pattern=r"^E[0-9]{6}$"),"name":s()}),
                        "origin":s(),"destination":s(),"start_date":s(fmt="date"),"end_date":s(fmt="date"),
                        "expenses":arr(obj({"category":s(choices=["交通","住宿"]),"amount":n(0,20000)}),2,2),"total_amount":n(0,50000)},
                       ["claim_id","employee","origin","destination","start_date","end_date","expenses","total_amount"])
    data={"claim_id":f"TRC{i+1:06d}","employee":{"employee_id":f"E{i+1:06d}","name":name},"origin":origin,"destination":dest,
          "start_date":dt(i,date(2026,10,2)),"end_date":dt(i+2,date(2026,10,2)),"expenses":expenses,"total_amount":total}
    return prompt("企业差旅费用报销",rules,facts,i),schema,data


def test_hotel_group_booking(i: int, r: random.Random):
    room_types=["大床房","双床房","家庭房"]
    blocks=[{"room_type":room_types[i%3],"room_count":1+i%8,"guests_per_room":1+i%2},
            {"room_type":room_types[(i+1)%3],"room_count":1+(i+2)%6,"guests_per_room":2}]
    start=dt(i,date(2026,11,5));end=dt(i+2,date(2026,11,5))
    rules=("团体预订号（booking_id）为 HB 后 6 位数字；酒店名（hotel_name）为字符串；"
           "入住日（check_in）与退房日（check_out）用 YYYY-MM-DD；房型分配（room_blocks）恰好 2 项，"
           "每项含房型（room_type，限大床房、双床房、家庭房）、房间数（room_count，1至12整数）和每间入住人数（guests_per_room，1至4整数）。")
    facts=f"预订 HB{i+1:06d}，{['云栖酒店','海悦会议中心','北站商务酒店'][i%3]}，{start}入住、{end}退房；"+"；".join(f"{b['room_type']}{b['room_count']}间，每间{b['guests_per_room']}人" for b in blocks)+"。"
    schema=root_schema({"booking_id":s(pattern=r"^HB[0-9]{6}$"),"hotel_name":s(),"check_in":s(fmt="date"),"check_out":s(fmt="date"),
                        "room_blocks":arr(obj({"room_type":s(choices=room_types),"room_count":n(1,12,True),"guests_per_room":n(1,4,True)}),2,2)},
                       ["booking_id","hotel_name","check_in","check_out","room_blocks"])
    data={"booking_id":f"HB{i+1:06d}","hotel_name":["云栖酒店","海悦会议中心","北站商务酒店"][i%3],"check_in":start,"check_out":end,"room_blocks":blocks}
    return prompt("企业差旅团队酒店预订",rules,facts,i),schema,data


def test_subscription_change(i: int, r: random.Random):
    kinds=["更换套餐","暂停服务","取消订阅"]
    kind=kinds[i%3]
    props={"request_id":s(pattern=r"^SUB[0-9]{6}$"),"subscriber_id":s(pattern=r"^AC[0-9]{6}$"),"change_type":s(choices=kinds),
           "new_plan":s(choices=["基础版","专业版","企业版"]),"pause_until":s(fmt="date"),"cancel_reason":s()}
    rules=("变更单号（request_id）为 SUB 后 6 位数字；订阅账户（subscriber_id）为 AC 后 6 位数字；"
           "变更类型（change_type）只能是更换套餐、暂停服务、取消订阅。更换套餐时必须填写新套餐（new_plan，基础版/专业版/企业版）；"
           "暂停服务时必须填写恢复日期（pause_until，YYYY-MM-DD）；取消订阅时必须填写取消原因（cancel_reason）。未触发的类型字段不要求提供。")
    data={"request_id":f"SUB{i+1:06d}","subscriber_id":f"AC{i+1:06d}","change_type":kind}
    facts=f"变更单 SUB{i+1:06d}，账户 AC{i+1:06d}，请求{kind}。"
    if kind=="更换套餐":data["new_plan"]=["基础版","专业版","企业版"][i%3];facts+=f"新套餐设为{data['new_plan']}。"
    elif kind=="暂停服务":data["pause_until"]=dt(i,date(2026,12,1));facts+=f"恢复日期为{data['pause_until']}。"
    else:data["cancel_reason"]=["业务调整","改用其他平台","项目结束"][i%3];facts+=f"原因是{data['cancel_reason']}。"
    branches=[{"properties":{"change_type":{"const":"更换套餐"}},"required":["change_type","new_plan"]},
              {"properties":{"change_type":{"const":"暂停服务"}},"required":["change_type","pause_until"]},
              {"properties":{"change_type":{"const":"取消订阅"}},"required":["change_type","cancel_reason"]}]
    schema=root_schema(props,["request_id","subscriber_id","change_type"],oneOf=branches)
    return prompt("企业软件订阅变更申请",rules,facts,i),schema,data


def test_equipment_maintenance(i: int, r: random.Random):
    parts=[{"part_code":f"PT-{i*2+j+1:05d}","quantity":1+(i+j)%3} for j in range(2)]
    rules=("设备编号（asset_id）为 AST 后 6 位数字；设备名称（asset_name）和维护人（technician）为字符串；"
           "维护状态（status）限已完成、待复检、需停机；维护日期（maintenance_date）及下次巡检日（next_inspection）用 YYYY-MM-DD；"
           "更换零件（parts）恰好 2 项，每项含零件编号（part_code，PT-后 5 位数字）和数量（quantity，1至3整数）。")
    status=["已完成","待复检","需停机"][i%3]
    facts=f"设备 AST{i+1:06d}「{['冷却泵','包装机械臂','空压机','制冷机组'][i%4]}」由{['赵工','刘工','王工'][i%3]}于{dt(i,date(2026,9,20))}维护，状态{status}，下次巡检{dt(i+10,date(2026,9,20))}；"+"、".join(f"零件{p['part_code']}更换{p['quantity']}件" for p in parts)+"。"
    schema=root_schema({"asset_id":s(pattern=r"^AST[0-9]{6}$"),"asset_name":s(),"technician":s(),"status":s(choices=["已完成","待复检","需停机"]),
                        "maintenance_date":s(fmt="date"),"next_inspection":s(fmt="date"),"parts":arr(obj({"part_code":s(pattern=r"^PT-[0-9]{5}$"),"quantity":n(1,3,True)}),2,2)},
                       ["asset_id","asset_name","technician","status","maintenance_date","next_inspection","parts"])
    data={"asset_id":f"AST{i+1:06d}","asset_name":["冷却泵","包装机械臂","空压机","制冷机组"][i%4],"technician":["赵工","刘工","王工"][i%3],"status":status,
          "maintenance_date":dt(i,date(2026,9,20)),"next_inspection":dt(i+10,date(2026,9,20)),"parts":parts}
    return prompt("生产设备维护工单",rules,facts,i),schema,data


def test_training_signin(i: int, r: random.Random):
    participants=[{"employee_id":f"E{i*3+j+1:06d}","name":["林知夏","周予安","陈嘉树","许清禾","沈一诺"][(i+j)%5],"attendance":["到场","迟到","请假"][(i+j)%3]} for j in range(3)]
    note=None if i%3==0 else ["完成实操考核","需补交练习","已领取讲义"][i%3-1]
    rules=("培训场次编号（session_id）为 TRN 后 6 位数字；课程名（course_name）为字符串；日期（training_date）用 YYYY-MM-DD。"
           "学员（participants）恰好 3 人，每人含员工编号（employee_id，E 后 6 位数字）、姓名（name）和出勤状态（attendance，限到场、迟到、请假）。"
           "备注（note）必须填写；没有备注时为 null，字段允许 null。")
    facts=f"培训 TRN{i+1:06d}「{['数据安全入门','客户沟通技巧','质量管理基础'][i%3]}」于{dt(i,date(2026,10,6))}举行；"+"；".join(f"{p['name']}（{p['employee_id']}）{p['attendance']}" for p in participants)+"。"+(f"备注：{note}。" if note else "没有补充备注。")
    schema=root_schema({"session_id":s(pattern=r"^TRN[0-9]{6}$"),"course_name":s(),"training_date":s(fmt="date"),
                        "participants":arr(obj({"employee_id":s(pattern=r"^E[0-9]{6}$"),"name":s(),"attendance":s(choices=["到场","迟到","请假"])}),3,3),
                        "note":s(nullable=True)},["session_id","course_name","training_date","participants","note"])
    data={"session_id":f"TRN{i+1:06d}","course_name":["数据安全入门","客户沟通技巧","质量管理基础"][i%3],"training_date":dt(i,date(2026,10,6)),"participants":participants,"note":note}
    return prompt("企业内训签到表",rules,facts,i),schema,data


def test_b2b_lead_intake(i: int, r: random.Random):
    orgs=["北辰零售","海棠食品","远帆制造","青岚医疗"]
    channel=["邮箱","电话"]
    people=[]
    for j in range(2):
        name=["陈经理","许主管","顾总监","宋主任"][(i+j)%4]
        ch=channel[(i+j)%2]
        value=f"contact{i*2+j+1:03d}@example.com" if ch=="邮箱" else f"137{i*2+j+1:08d}"
        people.append({"name":name,"channel":ch,"contact_value":value})
    source=["行业展会","官网咨询","合作转介","线上研讨会"][i%4]
    item_schemas=[
        obj({"name":s(),"channel":{"type":"string","const":"邮箱"},"contact_value":s(fmt="email")}),
        obj({"name":s(),"channel":{"type":"string","const":"电话"},"contact_value":s(pattern=r"^1[0-9]{10}$")}),
    ]
    rules=("线索编号（lead_id）为 LD 后 6 位数字；企业名（organization）为字符串；来源（source）限行业展会、官网咨询、合作转介、线上研讨会。"
           "联系人（contacts）恰好 2 人；每人含姓名（name）、渠道（channel，邮箱或电话）和联系方式（contact_value）；"
           "邮箱渠道的联系方式须为 email 格式，电话渠道须为 11 位且以 1 开头。")
    facts=f"线索 LD{i+1:06d} 来自{orgs[i%4]}，来源{source}；"+"；".join(f"联系人{x['name']}，{x['channel']} {x['contact_value']}" for x in people)+"。"
    schema=root_schema({"lead_id":s(pattern=r"^LD[0-9]{6}$"),"organization":s(),"source":s(choices=["行业展会","官网咨询","合作转介","线上研讨会"]),
                        "contacts":arr({"oneOf":item_schemas},2,2)},["lead_id","organization","source","contacts"])
    data={"lead_id":f"LD{i+1:06d}","organization":orgs[i%4],"source":source,"contacts":people}
    return prompt("B2B 销售线索录入",rules,facts,i),schema,data


def test_project_milestone(i: int, r: random.Random):
    names=["需求评审","试点部署","验收交付"]
    milestones=[{"name":names[j],"status":["未开始","进行中","已完成"][(i+j)%3],"completion_percent":[0,45,100][(i+j)%3],"due_date":dt(i+j*7,date(2026,12,5))} for j in range(3)]
    budget=25000+i*17500
    rules=("项目编号（project_id）为 PRJ 后 6 位数字；项目名（project_name）为字符串；负责人（owner）对象含姓名（name）和员工号（employee_id，E 后 6 位数字）；"
           "项目预算（budget）为 1000 至 500000 元数值。里程碑（milestones）恰好 3 项，每项含名称（name）、状态（status，限未开始、进行中、已完成）、"
           "完成百分比（completion_percent，0至100整数）和截止日（due_date，YYYY-MM-DD）。")
    facts=f"项目 PRJ{i+1:06d}「{['客户门户升级','华东仓改造','数据中台迁移','售后流程重建'][i%4]}」，负责人{['林知夏','周予安','陈嘉树','许清禾'][i%4]}（E{i+1:06d}），预算{budget}元；"+"；".join(f"{m['name']}状态{m['status']}、完成{m['completion_percent']}%、截止{m['due_date']}" for m in milestones)+"。"
    schema=root_schema({"project_id":s(pattern=r"^PRJ[0-9]{6}$"),"project_name":s(),"owner":obj({"name":s(),"employee_id":s(pattern=r"^E[0-9]{6}$")}),
                        "budget":n(1000,500000),"milestones":arr(obj({"name":s(),"status":s(choices=["未开始","进行中","已完成"]),"completion_percent":n(0,100,True),"due_date":s(fmt="date")}),3,3)},
                       ["project_id","project_name","owner","budget","milestones"])
    data={"project_id":f"PRJ{i+1:06d}","project_name":["客户门户升级","华东仓改造","数据中台迁移","售后流程重建"][i%4],"owner":{"name":["林知夏","周予安","陈嘉树","许清禾"][i%4],"employee_id":f"E{i+1:06d}"},"budget":budget,"milestones":milestones}
    return prompt("企业项目里程碑跟踪",rules,facts,i),schema,data


TEST_FAMILIES = [
    family("test_customer_quote", "test", ["ordinary", "business", "nested", "array_count", "enum", "range", "format", "pattern"], "企业服务报价单", test_customer_quote),
    family("test_sales_contract_order", "test", ["combination", "business", "nested", "array_count", "enum", "range", "format", "pattern"], "销售合同订单", test_sales_contract_order),
    family("test_vendor_invoice_payment", "test", ["combination", "business", "conditional", "enum", "range", "pattern"], "供应商发票付款登记", test_vendor_invoice_payment),
    family("test_warehouse_pick_pack", "test", ["combination", "business", "nested", "array_count", "pattern", "format", "range"], "仓库拣货出库单", test_warehouse_pick_pack),
    family("test_employee_onboarding", "test", ["combination", "business", "nullable", "format", "pattern", "enum"], "企业员工入职建档", test_employee_onboarding),
    family("test_recruiting_candidate", "test", ["combination", "business", "one_of", "format", "pattern"], "企业招聘候选人登记", test_recruiting_candidate),
    family("test_product_catalog", "test", ["combination", "business", "nested", "all_of", "enum", "range", "pattern"], "商品目录上架信息", test_product_catalog),
    family("test_monthly_forecast", "test", ["ordinary", "business", "nested", "array_count", "enum", "range", "format", "pattern"], "部门月度经营预测", test_monthly_forecast),
    family("test_support_case", "test", ["combination", "business", "conditional", "enum", "format", "pattern"], "SaaS 客服问题工单", test_support_case),
    family("test_refund_claim", "test", ["combination", "business", "conditional", "enum", "range", "format", "pattern"], "电商售后退款申请", test_refund_claim),
    family("test_campaign_brief", "test", ["combination", "business", "array_range", "enum", "range", "pattern"], "市场营销活动简报", test_campaign_brief),
    family("test_supplier_qualification", "test", ["combination", "business", "dependent_required", "any_of", "optional", "enum", "format", "pattern"], "企业供应商资质登记", test_supplier_qualification),
    family("test_meeting_minutes", "test", ["combination", "business", "nested", "array_count", "format", "pattern"], "跨部门项目会议纪要", test_meeting_minutes),
    family("test_business_travel_claim", "test", ["combination", "business", "nested", "array_count", "range", "format", "pattern"], "企业差旅费用报销", test_business_travel_claim),
    family("test_hotel_group_booking", "test", ["combination", "business", "nested", "array_count", "enum", "range", "format", "pattern"], "企业差旅团队酒店预订", test_hotel_group_booking),
    family("test_subscription_change", "test", ["combination", "business", "one_of", "enum", "format", "pattern"], "企业软件订阅变更申请", test_subscription_change),
    family("test_equipment_maintenance", "test", ["ordinary", "business", "nested", "array_count", "enum", "format", "pattern", "range"], "生产设备维护工单", test_equipment_maintenance),
    family("test_training_signin", "test", ["combination", "business", "nested", "array_count", "nullable", "enum", "format", "pattern"], "企业内训签到表", test_training_signin),
    family("test_b2b_lead_intake", "test", ["combination", "business", "nested", "array_count", "one_of", "enum", "format", "pattern"], "B2B 销售线索录入", test_b2b_lead_intake),
    family("test_project_milestone", "test", ["combination", "business", "nested", "array_count", "enum", "range", "format", "pattern"], "企业项目里程碑跟踪", test_project_milestone),
]


def emit_split(families: list[dict[str, Any]], count_per_family: int) -> tuple[list[dict[str, Any]], Counter[str]]:
    rows: list[dict[str, Any]] = []
    family_counts: Counter[str] = Counter()
    format_checker = FormatChecker()
    for fam in families:
        validator_cache: dict[str, Draft202012Validator] = {}
        for idx in range(count_per_family):
            rng = random.Random(f"{SEED}:{fam['name']}:{idx}")
            input_text, schema, data = fam["builder"](idx, rng)
            schema_key = json.dumps(schema, ensure_ascii=False, sort_keys=True)
            if schema_key not in validator_cache:
                Draft202012Validator.check_schema(schema)
                validator_cache[schema_key] = Draft202012Validator(schema, format_checker=format_checker)
            errors = list(validator_cache[schema_key].iter_errors(data))
            if errors:
                detail = "; ".join(f"{list(e.absolute_path)}: {e.message}" for e in errors)
                raise ValueError(f"{fam['name']} row {idx}: reference_data invalid: {detail}")
            row = {
                "id": f"{fam['name']}_{idx+1:03d}",
                "split": fam["split"],
                "family": fam["name"],
                "rule_tags": list(fam["tags"]),
                "input": input_text,
                "reference_schema": schema,
                "reference_data": data,
                "provenance": {
                    "synthetic": True,
                    "authoring_model": MODEL,
                    "method": "GPT-6 Luna max-authored Chinese task-family templates with fixed-seed deterministic slot values",
                    "seed": SEED,
                    "template_id": fam["name"],
                },
            }
            rows.append(row)
            family_counts[fam["name"]] += 1
    return rows, family_counts


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    val_rows, val_counts = emit_split(VAL_FAMILIES, 25)
    test_rows, test_counts = emit_split(TEST_FAMILIES, 25)
    for name, rows in (("validation_raw.jsonl", val_rows), ("test_raw.jsonl", test_rows)):
        path = OUT / name
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    write_notes(val_rows, val_counts, test_rows, test_counts)


def write_notes(val_rows: list[dict[str, Any]], val_counts: Counter[str],
                test_rows: list[dict[str, Any]], test_counts: Counter[str]) -> None:
    tag_counts = Counter(tag for row in val_rows + test_rows for tag in row["rule_tags"])
    ordinary = sum("ordinary" in row["rule_tags"] for row in test_rows)
    combination = sum("combination" in row["rule_tags"] for row in test_rows)
    lines = [
        "# Evaluation generation notes", "",
        "## Provenance and method", "",
        f"These records are synthetic and authored for this task by {MODEL}. The generator uses hand-written Chinese task-family templates with fixed-seed deterministic slot substitution; the rows are not individually sampled from a language-model API and are not human-validated.",
        f"The seed is `{SEED}`. Each row carries the same model/method disclosure, seed, and family template ID in `provenance`.", "",
        "## Split and family counts", "",
        f"Validation: {len(val_rows)} rows across {len(val_counts)} semantic task families ({len(VAL_FAMILIES)} rows per family). Test: {len(test_rows)} rows across {len(test_counts)} separate business task families ({len(TEST_FAMILIES)} rows per family).",
        "Validation covers college processes; test covers business operations. Family names identify distinct tasks and constraint patterns, not paraphrase IDs.", "",
        "### Validation families", "",
    ]
    lines.extend(f"- `{name}`: {count}" for name, count in sorted(val_counts.items()))
    lines.extend(["", "### Test families", ""])
    lines.extend(f"- `{name}`: {count}" for name, count in sorted(test_counts.items()))
    lines.extend(["", "## Rule coverage", "", "Tags are descriptive; rows may carry several tags. Test split is explicitly separated into ordinary and combination examples:",
                  f"- Test ordinary: {ordinary}", f"- Test combination: {combination}", "", "Combined tag counts across both splits:"])
    lines.extend(f"- `{tag}`: {count}" for tag, count in sorted(tag_counts.items()))
    lines.extend(["", "The set includes scalar and nested objects, exact array counts and bounded array lengths, integer and numeric ranges, enums, simple anchored patterns, date/time/date-time formats, `if`/`then`/`else`, `dependentRequired`, `oneOf`, `allOf`, optional fields, and explicit nullable values. Nullable fields always state the null policy in the input. Conditional and dependency examples state which branch fields are required or omitted.", "",
                  "## Validation", "", "The generator checks each schema with `Draft202012Validator.check_schema` and validates every `reference_data` object with `Draft202012Validator` plus `FormatChecker` before writing JSONL. The output is deterministic for the fixed seed.", "",
                  "## Limits", "", "The data are synthetic, template-based, and use bounded slot vocabularies; repeated phrasing and structural regularity may make them easier than naturally authored requests. They do not provide independent human validation, and the provenance reports model-assisted template authorship rather than per-row model generation.", ""])
    (OUT / "eval_generation_notes.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
