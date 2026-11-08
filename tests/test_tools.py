"""ツールのテスト（LLMもAPIキーも使わない）。"""

import json

from app import tools


def test_glossary_ids_are_unique_and_related_links_exist():
    terms = tools.load_glossary()
    ids = [t["id"] for t in terms]
    assert len(ids) == len(set(ids))
    for t in terms:
        for r in t["related"]:
            assert r in ids, f"{t['id']} の related に存在しない id: {r}"


def test_search_finds_term_by_name_and_alias():
    for query in ["LoRA", "lora", "Low-Rank Adaptation"]:
        hits = json.loads(tools.search_glossary(query))
        assert hits[0]["term"] == "LoRA", query


def test_search_finds_course_specific_term():
    hits = json.loads(tools.search_glossary("lecNN-start"))
    assert hits[0]["term"] == "lecNN-start タグ"


def test_search_limits_number_of_results():
    hits = json.loads(tools.search_glossary("エージェント"))
    assert 1 <= len(hits) <= tools.MAX_RESULTS


def test_search_reports_not_found():
    assert "見つかりませんでした" in tools.search_glossary("存在しない用語xyz")


def test_lecture_summary_appends_to_learning_log(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")

    assert "エージェント" in tools.get_lecture_summary(3)
    assert "まだありません" in tools.get_lecture_summary(99)

    logs = [json.loads(line) for line in tools.LOG_PATH.read_text(encoding="utf-8").splitlines()]
    assert [entry["topic"] for entry in logs] == [
        "第3回の講義要点",
        "第99回の講義要点",
    ]


def test_make_quiz_uses_a_term_from_the_requested_lecture(tmp_path, monkeypatch):
    def choose_first(terms):
        assert terms
        assert all(term["lecture"] == 2 for term in terms)
        return terms[0]

    monkeypatch.setattr(tools.random, "choice", choose_first)
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")

    quiz = json.loads(tools.make_quiz(2))
    selected_term = next(term for term in tools.load_glossary() if term["lecture"] == 2)

    assert quiz["question"].endswith("に当てはまる用語は何ですか？")
    assert selected_term["definition"] in quiz["question"]
    assert quiz["answer"] == selected_term["term"]
    logged = json.loads(tools.LOG_PATH.read_text(encoding="utf-8"))
    assert logged["topic"] == "第2回の確認問題"
    assert logged["note"] == json.dumps(quiz, ensure_ascii=False)


def test_make_quiz_reports_when_lecture_has_no_terms(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")

    result = json.loads(tools.make_quiz(99))

    assert "第99回" in result["error"]
    logged = json.loads(tools.LOG_PATH.read_text(encoding="utf-8"))
    assert logged["topic"] == "第99回の確認問題"


def test_save_learning_log_appends_jsonl_records(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "LOG_DIR", tmp_path)
    monkeypatch.setattr(tools, "LOG_PATH", tmp_path / "learning_log.jsonl")

    tools.save_learning_log("用語検索", "用語集を調べた")
    result = tools.save_learning_log("第2回の確認問題", "問題と答え")

    records = [json.loads(line) for line in tools.LOG_PATH.read_text(encoding="utf-8").splitlines()]
    assert records == [
        {
            "topic": "用語検索",
            "note": "用語集を調べた",
        },
        {
            "topic": "第2回の確認問題",
            "note": "問題と答え",
        },
    ]
    assert "learning_log.jsonl" in result


def test_default_question_of_lecture1_is_answerable_from_glossary():
    """第1回の既定の質問（app.ask）は、第3回のエージェントが用語集で正しく答えられること。"""
    from app.ask import DEFAULT_QUESTION

    assert "3レベル" in DEFAULT_QUESTION
    hits = json.loads(tools.search_glossary("3レベル"))
    assert hits[0]["term"] == "宿題の3レベル"
