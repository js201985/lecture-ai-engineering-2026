"""エージェントの配線テスト。

TestModel は実際のLLMを呼ばない偽モデルで、登録されたツールを全部呼んでから
ダミーの回答を返す。APIキーも利用枠も使わずに、
「ツールが登録され、呼ばれ、結果がモデルに戻るか」を確かめられる。
"""

import json

from pydantic_ai import DeferredToolRequests
from pydantic_ai.messages import ToolCallPart, ToolReturnPart
from pydantic_ai.models.test import TestModel

from app.agent import agent, run_with_approval

BASE_TOOLS = {"search_glossary", "get_lecture_summary"}


def _parts(result, kind):
    return [p for m in result.all_messages() for p in m.parts if isinstance(p, kind)]


def test_base_tools_are_registered_and_called():
    model = TestModel()
    with agent.override(model=model):
        result = agent.run_sync("LoRAとは？")

    offered = {t.name for t in model.last_model_request_parameters.function_tools}
    assert BASE_TOOLS <= offered  # 演習でツールを足しても壊れないよう「含む」で判定

    called = {p.tool_name for p in _parts(result, ToolCallPart)}
    assert BASE_TOOLS <= called
    # 承認が必要なツール（requires_approval=True）は、実行されずに承認待ちになるので戻り値が無い
    waiting = len(result.output.approvals) if isinstance(result.output, DeferredToolRequests) else 0
    assert len(_parts(result, ToolReturnPart)) + waiting == len(_parts(result, ToolCallPart))
    assert result.output


def test_glossary_result_reaches_the_model():
    model = TestModel(call_tools=["search_glossary"])
    with agent.override(model=model):
        result = agent.run_sync("RAGとは？")
    returns = _parts(result, ToolReturnPart)
    assert returns and returns[0].tool_name == "search_glossary"


def test_learning_log_tool_waits_for_approval():
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = agent.run_sync("学習記録を保存して")

    assert isinstance(result.output, DeferredToolRequests)
    assert len(result.output.approvals) == 1
    assert _parts(result, ToolReturnPart) == []


def test_summary_and_quiz_wait_for_approval_before_logging(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")
    model = TestModel(call_tools=["get_lecture_summary", "make_quiz"])
    with agent.override(model=model):
        result = agent.run_sync("第2回の要点と確認問題を出して")

    assert isinstance(result.output, DeferredToolRequests)
    assert {call.tool_name for call in result.output.approvals} == {
        "get_lecture_summary",
        "make_quiz",
    }
    assert not tools.LOG_PATH.exists()


def test_approved_summary_execution_appends_learning_log(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")
    monkeypatch.setattr("builtins.input", lambda _: "y")
    model = TestModel(call_tools=["get_lecture_summary"])
    with agent.override(model=model):
        result = run_with_approval(agent, "第3回の要点を教えて", model)

    assert not isinstance(result.output, DeferredToolRequests)
    log_entry = json.loads(tools.LOG_PATH.read_text(encoding="utf-8"))
    assert log_entry["topic"] == "第0回の講義要点"
    assert log_entry["note"].startswith("第0回の要点はまだありません。")


def test_learning_log_cli_approval_resumes_and_saves(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")
    monkeypatch.setattr("builtins.input", lambda _: "y")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = run_with_approval(agent, "学習記録を保存して", model)

    assert not isinstance(result.output, DeferredToolRequests)
    records = [json.loads(line) for line in tools.LOG_PATH.read_text(encoding="utf-8").splitlines()]
    assert len(records) == 1
    assert records[0]["topic"] == "a"


def test_learning_log_cli_rejection_resumes_without_saving(tmp_path, monkeypatch):
    from app import tools

    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")
    monkeypatch.setattr("builtins.input", lambda _: "n")
    model = TestModel(call_tools=["save_learning_log"])
    with agent.override(model=model):
        result = run_with_approval(agent, "学習記録を保存して", model)

    assert not isinstance(result.output, DeferredToolRequests)
    assert not tools.LOG_PATH.exists()
