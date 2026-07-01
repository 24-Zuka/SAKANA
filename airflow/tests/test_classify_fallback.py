from airflow.adapters.base import AdapterUnavailable, ClassificationResult
from airflow.models import Category
from airflow.orchestrator.classify import classify_text


class AlwaysFailsAdapter:
    def classify(self, text: str) -> ClassificationResult:
        raise AdapterUnavailable("simulated: LM Studio not running")


class StubAdapter:
    def __init__(self, result: ClassificationResult):
        self._result = result

    def classify(self, text: str) -> ClassificationResult:
        return self._result


def test_falls_back_to_rule_based_when_primary_unavailable():
    result = classify_text(
        "本番サーバーのバグを今すぐ修正してデプロイする", primary=AlwaysFailsAdapter()
    )
    assert result.worker == "rule_based"
    assert result.category == Category.ENGINEERING


def test_uses_primary_when_available():
    stub_result = ClassificationResult(
        category=Category.CONTENT,
        priority=2,
        decision_required=False,
        involves_external_send=False,
        involves_irreversible_action=False,
        worker="lmstudio",
    )
    result = classify_text("何か", primary=StubAdapter(stub_result))
    assert result.worker == "lmstudio"
    assert result.category == Category.CONTENT


def test_never_raises_even_when_primary_fails():
    try:
        classify_text("何かのタスク", primary=AlwaysFailsAdapter())
    except AdapterUnavailable:
        raise AssertionError("classify_text must not propagate AdapterUnavailable")
