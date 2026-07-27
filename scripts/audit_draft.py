#!/usr/bin/env python3
"""Deterministic offline preflight checks for user-authored LINUX DO drafts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


SEVERITY_ORDER = {"INFO": 0, "MEDIUM": 1, "HIGH": 2, "BLOCKER": 3}
SHORTENER_DOMAINS = {
    "bit.ly",
    "cutt.ly",
    "dwz.cn",
    "is.gd",
    "rebrand.ly",
    "t.co",
    "tinyurl.com",
    "url.cn",
}
MANUAL_REVIEW_TERMS = {
    "CORE-002": ["国家领导人", "国家政策", "政治"],
    "CORE-003": ["色情", "成人视频", "裸聊"],
    "CORE-004": ["赌博", "博彩", "毒品", "涉黑", "血腥"],
    "CORE-005": ["挂人", "人肉", "带节奏", "傻逼", "垃圾人"],
    "CORE-006": ["诈骗", "欺诈", "黑产", "木马", "病毒"],
    "QUALITY-001": ["拉人头", "下线返利", "裂变"],
}
CATEGORY_BY_POST_TYPE = {
    "cloud_drive": "网盘资源",
    "trade": "跳蚤市场",
    "job": "非我莫属",
    "book_note": "读书成诗",
    "promotion": "扬帆起航",
    "giveaway": "福利羊毛",
    "collaborative_doc": "文档共建",
    "news": "前沿快讯",
}
REQUIRED_TAG_BY_POST_TYPE = {
    "promotion": "推广",
    "open_source_promotion": "开源推广",
    "public_welfare_promotion": "公益推广",
    "advanced_promotion": "高级推广",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def add_finding(
    findings: list[dict[str, Any]],
    code: str,
    severity: str,
    message: str,
    evidence: str | None = None,
) -> None:
    finding: dict[str, Any] = {
        "code": code,
        "severity": severity,
        "message": message,
    }
    if evidence:
        finding["evidence"] = evidence[:160]
    findings.append(finding)


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s<>()\[\]{}\"']+", text, flags=re.IGNORECASE)


def normalize_category(
    requested: str, category_rules: dict[str, Any]
) -> tuple[str, bool]:
    requested_folded = requested.strip().casefold()
    if not requested_folded:
        return "", False
    for name, config in category_rules["categories"].items():
        candidates = [name, *config.get("aliases", [])]
        if requested_folded in {candidate.casefold() for candidate in candidates}:
            return name, True
    return requested.strip(), False


def audit_payload(
    payload: dict[str, Any],
    category_rules: dict[str, Any],
    post_checklists: dict[str, Any],
) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    body = str(payload.get("body", "")).strip()
    post_type = str(payload.get("post_type", "general")).strip() or "general"
    tags = [str(tag).strip() for tag in payload.get("tags", []) if str(tag).strip()]
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    findings: list[dict[str, Any]] = []
    questions: list[dict[str, str]] = []

    category, category_known = normalize_category(
        str(payload.get("category", "")), category_rules
    )

    if not title:
        add_finding(findings, "INPUT-001", "HIGH", "缺少标题。")
    if not body:
        add_finding(findings, "INPUT-002", "HIGH", "缺少正文。")
    elif len(body) < 50:
        add_finding(
            findings,
            "QUALITY-005",
            "MEDIUM",
            "正文较短，需人工确认是否只有摘要、链接或缺少完整说明。",
        )

    combined_text = f"{title}\n{body}"
    hidden_chars = [
        char
        for char in combined_text
        if unicodedata.category(char) == "Cf" and char not in {"\n", "\r", "\t"}
    ]
    if hidden_chars:
        add_finding(
            findings,
            "CORE-007",
            "BLOCKER",
            "检测到零宽或其他隐藏格式字符。",
            "".join(hidden_chars),
        )

    if re.search(r"\bhxxps?://|\[\.\]|\(\.\)", combined_text, re.IGNORECASE):
        add_finding(
            findings,
            "LINK-001",
            "BLOCKER",
            "检测到疑似替换字符或变形链接。",
        )

    supplied_links = payload.get("links", [])
    links = extract_urls(combined_text)
    if isinstance(supplied_links, list):
        links.extend(str(link).strip() for link in supplied_links if str(link).strip())
    links = list(dict.fromkeys(links))
    for link in links:
        domain = urlparse(link).netloc.casefold().split("@")[-1].split(":")[0]
        if domain.startswith("www."):
            domain = domain[4:]
        if domain in SHORTENER_DOMAINS:
            add_finding(
                findings,
                "LINK-001",
                "BLOCKER",
                "检测到短链域名；请使用未混淆的原始链接并人工核对。",
                link,
            )

    for code, terms in MANUAL_REVIEW_TERMS.items():
        matched = [term for term in terms if term in combined_text]
        if matched:
            add_finding(
                findings,
                code,
                "MEDIUM",
                "发现需要结合语境人工审查的敏感词；关键词本身不证明违规。",
                "、".join(matched),
            )

    ai_assisted = metadata.get("ai_assisted")
    if ai_assisted is True:
        add_finding(
            findings,
            "CORE-001",
            "BLOCKER",
            "输入表明正文经过 AI 生成或润色；不要发布该文字。",
        )
    elif ai_assisted is None:
        add_finding(
            findings,
            "CORE-001",
            "INFO",
            "未确认正文是否完全由用户自行撰写；发布前请自行确认。",
        )

    if not category:
        add_finding(findings, "CATEGORY-001", "MEDIUM", "尚未选择目标分区。")
    elif not category_known:
        add_finding(
            findings,
            "CATEGORY-002",
            "MEDIUM",
            "目标分区不在当前离线规则表中，需对照当前分类和置顶帖。",
            category,
        )
    else:
        category_config = category_rules["categories"][category]
        if category_config.get("pinned_status") == "required":
            add_finding(
                findings,
                "PINNED-001",
                "INFO",
                "发布前必须人工核对该分区当前置顶规则。",
                category,
            )
        preferred = category_config.get("preferred_post_types", [])
        if preferred and post_type not in preferred:
            add_finding(
                findings,
                "CATEGORY-003",
                "MEDIUM",
                f"帖子类型“{post_type}”不是该分区离线记录中的常见类型。",
                category,
            )

    required_category = CATEGORY_BY_POST_TYPE.get(post_type)
    if required_category and category and category != required_category:
        add_finding(
            findings,
            "CATEGORY-004",
            "HIGH",
            f"该帖子类型通常要求发布到“{required_category}”。",
            category,
        )

    required_tag = REQUIRED_TAG_BY_POST_TYPE.get(post_type)
    if required_tag and required_tag not in tags:
        add_finding(
            findings,
            "TAG-001",
            "HIGH",
            f"该帖子类型缺少必需标签“{required_tag}”。",
        )

    checklist = post_checklists["post_types"].get(post_type)
    if checklist is None:
        add_finding(
            findings,
            "TYPE-001",
            "MEDIUM",
            "帖子类型不在当前离线检查表中，需人工审查。",
            post_type,
        )
    else:
        for field in checklist.get("required_metadata", []):
            if is_missing(metadata.get(field)):
                question = checklist.get("questions", {}).get(
                    field, f"请自行补充字段：{field}"
                )
                questions.append({"field": field, "question": question})
                add_finding(
                    findings,
                    f"MISSING-{field.upper().replace('_', '-')}",
                    "HIGH",
                    f"缺少“{field}”信息。",
                )

    if post_type == "cloud_drive":
        providers = metadata.get("drive_providers", [])
        if isinstance(providers, list):
            missing_provider_tags = [
                str(provider)
                for provider in providers
                if str(provider).strip() and str(provider).strip() not in tags
            ]
            if missing_provider_tags:
                add_finding(
                    findings,
                    "DRIVE-002",
                    "HIGH",
                    "缺少部分网盘提供商标签。",
                    "、".join(missing_provider_tags),
                )
        if metadata.get("browser_accessible") is False:
            add_finding(
                findings,
                "DRIVE-003",
                "HIGH",
                "网盘链接被标记为不能通过常用浏览器直接访问。",
            )

    if post_type in {
        "promotion",
        "open_source_promotion",
        "public_welfare_promotion",
        "advanced_promotion",
    }:
        if metadata.get("community_diversion") is True:
            add_finding(
                findings,
                "PROMO-008",
                "BLOCKER",
                "推广内容包含向其他社区或群组引流。",
            )
        if metadata.get("login_required") is True and metadata.get(
            "linuxdo_connect"
        ) is not True:
            add_finding(
                findings,
                "PROMO-007",
                "HIGH",
                "项目需要登录，但尚未确认符合当前 LINUX DO Connect 要求。",
            )

    highest = max(
        (SEVERITY_ORDER[finding["severity"]] for finding in findings), default=0
    )
    if highest >= SEVERITY_ORDER["BLOCKER"]:
        verdict = "DO_NOT_POST"
    elif highest >= SEVERITY_ORDER["HIGH"]:
        verdict = "NEEDS_CHANGES"
    elif highest >= SEVERITY_ORDER["MEDIUM"]:
        verdict = "MANUAL_REVIEW"
    else:
        verdict = "READY_FOR_MANUAL_REVIEW"

    counts = {
        severity: sum(
            1 for finding in findings if finding["severity"] == severity
        )
        for severity in ("BLOCKER", "HIGH", "MEDIUM", "INFO")
    }
    return {
        "verdict": verdict,
        "counts": counts,
        "category": {
            "requested": payload.get("category", ""),
            "normalized": category,
            "known": category_known,
        },
        "post_type": post_type,
        "tags": tags,
        "links": links,
        "findings": findings,
        "missing_information": questions,
        "limitations": [
            "这是离线预审，不保证通过论坛审核。",
            "必须人工核对当前官方指南和目标分区置顶帖。",
            "本工具不生成、改写或润色可发布正文。",
        ],
    }


def render_markdown(report: dict[str, Any]) -> str:
    labels = {
        "DO_NOT_POST": "不要发布",
        "NEEDS_CHANGES": "需要修改",
        "MANUAL_REVIEW": "需要人工审查",
        "READY_FOR_MANUAL_REVIEW": "可进入最终人工核对",
    }
    lines = [
        f"# 审核结论：{labels.get(report['verdict'], report['verdict'])}",
        "",
        "## 风险统计",
    ]
    for severity in ("BLOCKER", "HIGH", "MEDIUM", "INFO"):
        lines.append(f"- {severity}: {report['counts'][severity]}")

    sections = [
        ("阻断问题", "BLOCKER"),
        ("高风险问题", "HIGH"),
        ("需要人工判断", "MEDIUM"),
        ("提示", "INFO"),
    ]
    for heading, severity in sections:
        matches = [
            finding
            for finding in report["findings"]
            if finding["severity"] == severity
        ]
        lines.extend(["", f"## {heading}"])
        if not matches:
            lines.append("- 无")
        for finding in matches:
            evidence = (
                f"（证据：{finding['evidence']}）"
                if finding.get("evidence")
                else ""
            )
            lines.append(
                f"- [{finding['code']}] {finding['message']}{evidence}"
            )

    lines.extend(
        [
            "",
            "## 分区与标签",
            f"- 分区：{report['category']['normalized'] or '未选择'}",
            f"- 类型：{report['post_type']}",
            f"- 标签：{'、'.join(report['tags']) or '未提供'}",
            "",
            "## 缺失信息（用户自行填写）",
        ]
    )
    if not report["missing_information"]:
        lines.append("- 无")
    else:
        for item in report["missing_information"]:
            lines.append(f"- `{item['field']}`：{item['question']}")

    lines.extend(["", "## 限制说明"])
    for limitation in report["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="离线检查用户自行撰写的 LINUX DO 发帖草稿。",
        epilog=(
            "输入 JSON 示例："
            '{"title":"...","body":"...","category":"开发调优",'
            '"post_type":"help","tags":[],"links":[],'
            '"metadata":{"environment":"...","attempted":"...",'
            '"error_or_symptom":"...","expected":"...","ai_assisted":false}}'
        ),
    )
    parser.add_argument("--input", required=True, help="UTF-8 JSON 输入文件")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="输出格式，默认 markdown",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    references = script_dir.parent / "references"
    try:
        payload = load_json(Path(args.input))
        category_rules = load_json(references / "category-rules.json")
        post_checklists = load_json(references / "post-type-checklists.json")
        report = audit_payload(payload, category_rules, post_checklists)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
