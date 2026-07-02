import httpx
import pytest

from airflow.adapters.base import AdapterUnavailable
from airflow.adapters.lm_studio import LMStudioAdapter
from airflow.adapters.rule_based import RuleBasedClassifier
from airflow.models import Category


def test_rule_based_detects_engineering_and_urgency():
    clf = RuleBasedClassifier()
    result = clf.classify("本番サーバーのバグを今すぐ修正してデプロイする")
    assert result.category == Category.ENGINEERING
    assert result.priority == 1
    assert result.involves_irreversible_action is True
    assert result.worker == "rule_based"


def test_rule_based_detects_business_and_decision():
    clf = RuleBasedClassifier()
    result = clf.classify("A社との提携レート再交渉の方針を決めたい")
    assert result.category == Category.BUSINESS
    assert result.decision_required is True


def test_rule_based_defaults_when_ambiguous():
    clf = RuleBasedClassifier()
    result = clf.classify("よくわからない何か")
    assert result.category == Category.BUSINESS
    assert result.priority == 2
    assert result.decision_required is False


def test_lm_studio_unreachable_raises_adapter_unavailable(monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    with pytest.raises(AdapterUnavailable):
        adapter.classify("何かのテキスト")


def test_lm_studio_parses_valid_response(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"category": "Engineering", "priority": 1, '
                                '"decision_required": true, "involves_external_send": false, '
                                '"involves_irreversible_action": false}'
                            )
                        }
                    }
                ]
            },
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    result = adapter.classify("サーバーの実装を至急直す")
    assert result.category == Category.ENGINEERING
    assert result.priority == 1
    assert result.decision_required is True
    assert result.worker == "lmstudio"


def test_lm_studio_unparseable_response_raises(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "not json"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    with pytest.raises(AdapterUnavailable):
        adapter.classify("何か")


def test_lm_studio_summarize(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "要約されたテキスト。"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    assert adapter.summarize("長い文章...") == "要約されたテキスト。"


def test_lm_studio_verify_pass(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"pass": true, "reason": "基準を満たす"}'}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    passed, reason = adapter.verify("成果物のテキスト", "基準: 日本語で書かれていること")
    assert passed is True
    assert reason == "基準を満たす"


def test_lm_studio_verify_fail(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": '{"pass": false, "reason": "基準未達"}'}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    passed, reason = adapter.verify("成果物", "基準")
    assert passed is False
    assert reason == "基準未達"


def test_lm_studio_list_models(monkeypatch):
    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={"data": [{"id": "qwen2.5-7b-instruct"}, {"id": "llama-3.1-8b"}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx, "get", fake_get)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    assert adapter.list_models() == ["qwen2.5-7b-instruct", "llama-3.1-8b"]


def test_lm_studio_run_ok(monkeypatch):
    def fake_post(url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "応答テキスト"}}]},
            request=httpx.Request("POST", url),
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    result = adapter.run("何か聞きたいこと")
    assert result.ok is True
    assert result.text == "応答テキスト"
    assert result.worker == "lmstudio"


def test_lm_studio_run_reports_failure_without_raising(monkeypatch):
    def fake_post(url, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx, "post", fake_post)
    adapter = LMStudioAdapter(base_url="http://localhost:1234/v1")
    result = adapter.run("何か")
    assert result.ok is False
    assert result.error is not None
