from fastapi.testclient import TestClient

from api.server import app
from skills.evaluation import compare_reports


client = TestClient(app)


def test_report_payload_is_layered_and_report_first(real_llm_required):
    response = client.post("/analyze", json={"company_code": "002555", "query": "请生成企业体检报告", "top_k": 2})
    assert response.status_code == 200

    body = response.json()["data"]
    payload = body["report_payload"]

    assert payload["report_layer"]["executive_summary"]
    assert payload["report_layer"]["key_judgments"]
    assert payload["report_layer"]["deep_sections"]
    assert payload["report_layer"]["risk_opportunities"]["risks"]
    assert payload["report_layer"]["action_items"]
    assert payload["evidence_layer"]["key_evidence"]
    assert payload["machine_layer"]["skill_runs"]
    assert all(section["title"] != "执行摘要" for section in payload["sections"])
    assert payload["sections"][0]["title"] == "综合判断"
    assert len(payload["sections"]) <= 4
    assert "skill" not in body["summary"].lower()
    assert "多阶段" not in body["summary"]
    assert "看到的事实" not in body["summary"]


def test_evaluation_rewards_user_facing_reports():
    baseline = {
        "summary": "本次共基于 8 条证据完成多阶段分析，已命中 5 个 skill。",
        "findings": ["已命中 3 个信号。"],
        "recommendations": [],
        "report_payload": {
            "report_layer": {
                "executive_summary": "",
                "key_judgments": [],
                "risk_opportunities": {"risks": [], "opportunities": []},
                "deep_sections": [],
                "next_steps": [],
            },
            "evidence_layer": {"key_evidence": [], "verification_focus": []},
        },
    }
    candidate = {
        "summary": "公司当前处于修复中状态，最关键的支撑来自新品储备和效率改善，但盈利质量仍是压制结论强度的核心约束。",
        "findings": ["公司当前处于修复中状态。"],
        "recommendations": ["第一，公司的核心状态不是泛泛有波动，而是修复中。"],
        "report_payload": {
            "report_layer": {
                "executive_summary": "公司当前处于修复中状态，最关键的支撑来自新品储备和效率改善，但盈利质量仍是压制结论强度的核心约束。",
                "key_judgments": [
                    {
                        "title": "总体判断",
                        "verdict": "公司当前处于修复中状态。",
                        "explanation": "当前压力主要来自盈利质量，积极变量来自新品储备与效率改善。",
                        "confidence": "中置信",
                        "tone": "warn",
                        "evidence_anchors": ["年报 P12"],
                    }
                ],
                "risk_opportunities": {
                    "risks": [
                        {
                            "title": "盈利质量与现金流匹配承压风险",
                            "summary": "盈利质量尚未完全站稳。",
                            "basis": "风险等级：中。当前证据：财务披露仍显示利润与现金流需要互相印证。",
                            "impact": "风险形成逻辑：利润修复尚未完全转化为现金流质量。若触发，最可能冲击利润弹性与经营韧性。",
                            "follow_up": "",
                            "tone": "risk",
                            "evidence": [],
                        }
                    ],
                    "opportunities": [
                        {
                            "title": "新品上线带来的增长再加速机会",
                            "summary": "新品储备仍可能提供新增弹性。",
                            "basis": "当前兑现基础：中。支撑证据：产品储备已有披露。",
                            "impact": "兑现条件：新品节奏继续向收入兑现转化。若兑现，将改善收入承接与增长持续性。",
                            "follow_up": "",
                            "tone": "good",
                            "evidence": [],
                        }
                    ],
                },
                "deep_sections": [
                    {
                        "key": "financial_health",
                        "title": "财务与经营健康度",
                        "summary": "盈利质量仍是当前结论强弱的关键约束。",
                        "body": ["材料信息：年报 P12。重点解读：收入质量与费用投放需要结合现金流一起看。对判断的意义：它解释了为什么盈利修复不能被直接等同于经营质量改善。", "诊断解释：这不是普通波动，而是会直接影响利润质量判断的压力链条。"],
                        "evidence": [],
                        "pending_checks": [],
                    }
                ],
                "next_steps": ["第一，公司的核心状态不是泛泛有波动，而是修复中。"],
            },
            "evidence_layer": {
                "key_evidence": [
                    {
                        "title": "年报关键披露",
                        "summary": "年报披露了新品储备与费用变化。",
                        "supports": "支持总体判断。",
                        "citation": "年报 P12",
                        "evidence": [],
                    }
                ],
                "verification_focus": [{"severity": "warn", "title": "证据覆盖", "detail": "现金流与利润口径仍需继续互相印证。"}],
            },
        },
    }

    comparison = compare_reports(candidate=candidate, baseline=baseline)

    assert comparison["delta"]["user_value_focus"] > 0
    assert comparison["delta"]["decision_support"] > 0
    assert comparison["delta"]["process_suppression"] > 0
