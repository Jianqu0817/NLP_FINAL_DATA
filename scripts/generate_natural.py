#!/usr/bin/env python3
"""Generate supplemental colloquial Chinese meeting extraction examples."""

from __future__ import annotations

import json
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
SEED = 20261105
MODEL = "GPT-6 Luna max"
REASONING_EFFORT = "max"
SCHEMA_URI = "https://json-schema.org/draft/2020-12/schema"
TIMEZONE = "Asia/Shanghai"

ROWS_PER_FAMILY = {"train": 20, "validation": 10, "test": 10}

# Each split has its own sentence-template families. The same fixed meeting
# schema convention is intentionally used in all three splits.
PATTERNS: dict[str, list[tuple[str, str]]] = {
    "train": [
        ("place_then_schedule", "地点先定在{location}。开会时间是{day}{time}，参会的有{attendees}，总共{count_cn}个人。帮我整理出字段结构和对应JSON。{anchor}"),
        ("schedule_then_place", "我想在{day}约个小会，{time}开始，地方在{location}。来的人一共{count_cn}位：{attendees}。请整理成字段定义和JSON。{anchor}"),
        ("memo_style", "帮我记个日程：{day}{time}在{location}开会。参会名单（共{count_cn}人）：{attendees}。整理好给我一份对应的JSON和字段规范。{anchor}"),
        ("meetup_first", "到时候我们在{location}碰头，日期是{day}，{time}。会有{count_cn}个人，分别是{attendees}。麻烦转成结构化信息。{anchor} 请附上对应的字段说明。"),
        ("casual_arrangement", "这次开会安排在{location}，{day}{time}。参与者就是{attendees}，算上大家一共{count_cn}位。能把它整理成一份字段规范和JSON吗？{anchor}"),
        ("spoken_note", "时间先记作{day}{time}，地点{location}。名单和电话在这儿：{attendees}；一共{count_cn}个人参加。把这件事整理成结构数据给我。{anchor}"),
        ("attendees_first", "我给你口述下会议安排：{count_cn}位到场，{attendees}；{day}{time}，在{location}。请给一份对应的字段结构和JSON。{anchor}"),
        ("short_booking", "会议就放到{day}吧，{time}在{location}见。确定会来的人有{attendees}，总数是{count_cn}人。帮忙整理下会议信息和JSON。{anchor}"),
        ("request_booking", "麻烦安排一场{day}{time}的会，场地用{location}。参会者共{count_cn}位，名字和电话分别是：{attendees}。请给结构和数据。{anchor}"),
        ("diary_entry", "我这条备忘录写的是：{location}开会，{day}{time}。到场的{count_cn}个人是{attendees}。帮我把信息收拾成字段规范和JSON内容。{anchor}"),
        ("agreed_time", "我们约的是{day}，具体{time}，地点定在{location}。参加的刚好{count_cn}个人：{attendees}。请按这些话整理一份结构化结果。{anchor}"),
        ("quick_record", "把会议记一下：在{location}，时间{day}{time}；人员有{attendees}，一共{count_cn}名。请给出对应的字段定义和JSON。{anchor}"),
        ("future_meeting", "之后我要到{location}开会，安排在{day}{time}。名单如下（总计{count_cn}位）：{attendees}。麻烦整成可用的JSON和字段结构。{anchor}"),
        ("meeting_reminder", "有个会想录进去：{day}{time}举行，地点是{location}。这{count_cn}位会到：{attendees}。请整理一下内容。{anchor} 给我相应的字段定义和JSON就行。"),
        ("people_first", "会面信息补全一下——{attendees}会参加；人头数是{count_cn}。地点{location}，时间{day}{time}。请依据这些信息输出字段结构和JSON。{anchor}"),
    ],
    "validation": [
        ("v_chat_invite", "我们要碰个头，安排在{day}{time}，地点是{location}。来的人是{attendees}，正好{count_cn}位。能帮我把这个安排整理成字段定义和数据JSON吗？{anchor}"),
        ("v_record_request", "记一下这场会：{day}{time}，地点{location}；名单是{attendees}，一共{count_cn}人。请把信息变成字段定义和JSON。{anchor}"),
        ("v_voice_message", "口头说下安排，{day}的{time}大家去{location}开会，参加的有{attendees}，总计{count_cn}名。给我对应的结构和JSON即可。{anchor}"),
        ("v_calendar_entry", "日历里加一场会议吧：{location}，{day}{time}，共{count_cn}位——{attendees}。请整理出字段结构和数据。{anchor}"),
    ],
    "test": [
        ("t_brief", "帮我留个会议信息：{day}{time}在{location}，{attendees}都来，总共{count_cn}个人。转成字段定义和JSON发我。{anchor}"),
        ("t_team_plan", "团队准备在{location}开会，约在{day}{time}。到场名单（{count_cn}位）：{attendees}。麻烦整理成结构化记录和对应JSON。{anchor}"),
        ("t_agenda_chat", "咱们把碰面的事定下来：时间{day}{time}，地点{location}；{attendees}会参加，人数是{count_cn}。请给出字段定义和JSON数据。{anchor}"),
        ("t_contact_list", "这几个人要一起开会：{attendees}，一共{count_cn}位。定在{day}{time}，地点放{location}。能按这些内容生成字段说明和数据JSON吗？{anchor}"),
        ("t_schedule_edit", "我有个会议要录入，时间{day}{time}、地方{location}，参会者是{attendees}（总共{count_cn}人）。帮我整理成对应的字段和JSON。{anchor}"),
        ("t_arrangement_message", "会议安排发你：{location}见，{day}{time}开始。会来的有{attendees}，合计{count_cn}名。请写成字段规范加JSON。{anchor}"),
        ("t_simple_booking", "想约{count_cn}个人开会，分别是{attendees}。哪天呢？{day}{time}；在哪儿？{location}。麻烦帮我整理成结构和JSON。{anchor}"),
        ("t_record_cleanup", "把这段安排收拾一下：{day}{time}，{location}，参加者{attendees}，人数一共{count_cn}。需要一份字段定义和对应数据。{anchor}"),
    ],
}

REFERENCE_DATES = [
    date(2026, 11, 5),
    date(2026, 11, 12),
    date(2026, 11, 28),
    date(2026, 11, 30),
    date(2026, 12, 1),
    date(2026, 12, 24),
    date(2027, 1, 29),
]
LOCATIONS = [
    "科创楼305会议室", "公司三楼的小会议室", "图书馆旁边的研讨间",
    "浦东办公室的靠窗会议室", "清风咖啡馆二楼", "线上视频会议室",
    "园区A座1208室", "学校行政楼206", "江湾路共享办公区的讨论室",
    "西湖边的云栖茶馆", "新街口门店后面的会议间", "总部一号楼大会议室",
    "滨江园区的蓝色会议室", "社区中心二楼活动室", "实验楼北侧小会客室",
    "人民广场附近的会客厅", "远程会议室", "创业园C区402室",
    "南门旁的拾光书店", "研发中心的项目讨论间",
]
SURNAMES = list("赵钱孙李周吴郑王冯陈褚卫蒋沈韩杨朱秦尤许何吕施张孔曹严华金魏陶姜")
GIVEN_FIRST = list("安清知若予景书文承星晓子可明思宇立")
GIVEN_SECOND = list("宁远川禾恺心言初之航涵墨沐然松照亭月")
CN_NUMBERS = {1: "一", 2: "两", 3: "三", 4: "四", 5: "五", 6: "六"}
CN_CLOCK = {0: "零", 1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 6: "六", 7: "七", 8: "八", 9: "九", 10: "十", 11: "十一", 12: "十二", 13: "十三", 14: "十四", 15: "十五", 16: "十六", 17: "十七", 18: "十八", 19: "十九", 20: "二十", 30: "三十", 40: "四十", 45: "四十五", 50: "五十", 55: "五十五"}
MINUTES = [0, 5, 10, 15, 20, 30, 40, 45, 50, 55]


def meeting_schema(participant_count: int) -> dict[str, Any]:
    participant = {
        "type": "object",
        "properties": {"name": {"type": "string"}, "phone": {"type": "string"}},
        "required": ["name", "phone"],
        "additionalProperties": False,
    }
    return {
        "$schema": SCHEMA_URI,
        "type": "object",
        "properties": {
            "start_time": {"type": "string", "format": "date-time"},
            "location": {"type": "string"},
            "participants": {
                "type": "array",
                "items": participant,
                "minItems": participant_count,
                "maxItems": participant_count,
            },
        },
        "required": ["start_time", "location", "participants"],
        "additionalProperties": False,
    }


def chinese_date(value: date) -> str:
    return f"{value.year}年{value.month}月{value.day}日"


def anchor_text(reference_date: date, style: int) -> str:
    if style % 4 == 0:
        return f"咱们按上海时间（{TIMEZONE}）算，今天是{chinese_date(reference_date)}。"
    if style % 4 == 1:
        return f"这里用{TIMEZONE}时区，今天日期为{reference_date.isoformat()}。"
    if style % 4 == 2:
        return f"按上海时间来，今天是{reference_date.isoformat()}（{TIMEZONE}）。"
    return f"时区按{TIMEZONE}处理，参照日期是{chinese_date(reference_date)}。"


def date_phrase(reference_date: date, kind: int, sample_index: int) -> tuple[str, date, str]:
    if kind == 0:
        target = reference_date + timedelta(days=1)
        return "明天", target, "relative_tomorrow"
    if kind == 1:
        target = reference_date + timedelta(days=2)
        return "后天", target, "relative_day_after_tomorrow"
    target = reference_date + timedelta(days=7 + sample_index % 19)
    return chinese_date(target), target, "absolute_date"


def time_value(sample_index: int, family_index: int) -> tuple[str, str]:
    hour = 8 + ((sample_index * 7 + family_index * 3) % 12)
    minute = MINUTES[(sample_index * 3 + family_index) % len(MINUTES)]
    if hour < 12:
        period = "上午"
        display_hour = hour
    elif hour == 12:
        period = "中午"
        display_hour = 12
    elif hour < 18:
        period = "下午"
        display_hour = hour - 12
    else:
        period = "晚上"
        display_hour = hour - 12
    if minute == 0:
        minute_text = "整"
    elif minute == 30:
        minute_text = "半"
    else:
        minute_text = f"{CN_CLOCK[minute]}分"
    natural = f"{period}{CN_CLOCK[display_hour]}点{minute_text}"
    exact = f"{hour:02d}:{minute:02d}:00+08:00"
    return natural, exact


def participant_name(serial: int) -> str:
    surname = SURNAMES[serial % len(SURNAMES)]
    first = GIVEN_FIRST[(serial * 7 + 3) % len(GIVEN_FIRST)]
    second = GIVEN_SECOND[(serial * 11 + 5) % len(GIVEN_SECOND)]
    return surname + first + second


def attendee_phrase(participants: list[dict[str, str]], style: int) -> str:
    entries: list[str] = []
    for person in participants:
        name, phone = person["name"], person["phone"]
        form = style % 5
        if form == 0:
            entries.append(f"{name}（电话：{phone}）")
        elif form == 1:
            entries.append(f"{name}，联系电话{phone}")
        elif form == 2:
            entries.append(f"{name}的手机号是{phone}")
        elif form == 3:
            entries.append(f"{name}：{phone}")
        else:
            entries.append(f"{name}电话{phone}")
    return "、".join(entries)


def build_rows(split: str) -> list[dict[str, Any]]:
    patterns = PATTERNS[split]
    rows_per_family = ROWS_PER_FAMILY[split]
    rows: list[dict[str, Any]] = []
    serial = {"train": 0, "validation": 10000, "test": 20000}[split]
    phone_serial = {"train": 1, "validation": 10001, "test": 20001}[split]

    for family_index, (family_slug, template) in enumerate(patterns):
        family = f"natural_{split}_{family_index + 1:02d}_{family_slug}"
        for sample_index in range(rows_per_family):
            row_index = family_index * rows_per_family + sample_index
            participant_count = row_index % 6 + 1
            reference_date = REFERENCE_DATES[(row_index + family_index) % len(REFERENCE_DATES)]
            kind = (sample_index + family_index) % 3
            day, target_date, date_tag = date_phrase(reference_date, kind, sample_index)
            natural_time, exact_time = time_value(sample_index, family_index)
            location = LOCATIONS[(row_index * 7 + family_index) % len(LOCATIONS)]

            participants: list[dict[str, str]] = []
            for attendee_index in range(participant_count):
                name = participant_name(serial + attendee_index)
                phone = f"138{phone_serial + attendee_index:08d}"
                participants.append({"name": name, "phone": phone})
            serial += participant_count
            phone_serial += participant_count

            names_and_phones = attendee_phrase(participants, row_index)
            count_cn = CN_NUMBERS[participant_count]
            anchor = anchor_text(reference_date, row_index)
            user_input = template.format(
                location=location,
                day=day,
                time=natural_time,
                attendees=names_and_phones,
                count_cn=count_cn,
                count=participant_count,
                anchor=anchor,
            )
            start_time = f"{target_date.isoformat()}T{exact_time}"
            reference_data = {
                "start_time": start_time,
                "location": location,
                "participants": participants,
            }
            rule_tags = ["meeting_record", "exact_participant_count", "colloquial_chinese", date_tag]
            rows.append(
                {
                    "id": f"NAT-{split[:3].upper()}-{family_index + 1:02d}-{sample_index + 1:03d}",
                    "split": split,
                    "family": family,
                    "rule_tags": rule_tags,
                    "input": user_input,
                    "reference_schema": meeting_schema(participant_count),
                    "reference_data": reference_data,
                    "provenance": {
                        "kind": "synthetic_template_based",
                        "model": MODEL,
                        "authoring_model": MODEL,
                        "reasoning_effort": REASONING_EFFORT,
                        "method": "template-assisted synthetic generation",
                        "instantiation": "deterministic Python template and slot substitution",
                        "seed": SEED,
                        "reference_date": reference_date.isoformat(),
                        "timezone": TIMEZONE,
                        "fictional_names_and_phones": True,
                        "human_validated": False,
                        "scope_note": "system convention supplies fixed meeting field names and required/no-extra-field rules; this split tests expression generalization over a familiar schema",
                    },
                }
            )

    # Shuffle row order reproducibly without changing family membership.
    random.Random(SEED + len(split)).shuffle(rows)
    return rows


def validate_and_write(split: str, rows: list[dict[str, Any]]) -> None:
    out_path = OUT / f"natural_{split}_raw.jsonl"
    validator_by_schema: dict[str, Draft202012Validator] = {}
    for row in rows:
        schema = row["reference_schema"]
        Draft202012Validator.check_schema(schema)
        schema_key = json.dumps(schema, ensure_ascii=False, sort_keys=True)
        validator = validator_by_schema.setdefault(
            schema_key,
            Draft202012Validator(schema, format_checker=FormatChecker()),
        )
        errors = sorted(validator.iter_errors(row["reference_data"]), key=lambda err: list(err.path))
        if errors:
            raise ValueError(f"{row['id']} failed schema validation: {errors[0].message}")

        user_input = row["input"]
        for forbidden in ("start_time", "participants", "additionalProperties", "minItems", "maxItems", "date-time"):
            if forbidden.lower() in user_input.lower():
                raise ValueError(f"{row['id']} leaks schema vocabulary into the input: {forbidden}")
        if TIMEZONE not in user_input and "上海时间" not in user_input:
            raise ValueError(f"{row['id']} is missing an explicit Asia/Shanghai time reference")

    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    print(f"{split}: {len(rows)} rows -> {out_path.relative_to(ROOT)}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_families: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for split in ("train", "validation", "test"):
        if len(PATTERNS[split]) != {"train": 15, "validation": 4, "test": 8}[split]:
            raise ValueError(f"unexpected pattern count for {split}")
        rows = build_rows(split)
        if len(rows) != {"train": 300, "validation": 40, "test": 80}[split]:
            raise ValueError(f"unexpected row count for {split}")
        family_counts = Counter(row["family"] for row in rows)
        if len(family_counts) != len(PATTERNS[split]) or set(family_counts.values()) != {ROWS_PER_FAMILY[split]}:
            raise ValueError(f"unexpected family distribution for {split}: {family_counts}")
        all_families[split] = set(family_counts)
        if all_ids.intersection(row["id"] for row in rows):
            raise ValueError(f"duplicate ids in {split}")
        all_ids.update(row["id"] for row in rows)
        validate_and_write(split, rows)

    if (all_families["train"] & all_families["validation"]
            or all_families["train"] & all_families["test"]
            or all_families["validation"] & all_families["test"]):
        raise ValueError("template families overlap across splits")


if __name__ == "__main__":
    main()
