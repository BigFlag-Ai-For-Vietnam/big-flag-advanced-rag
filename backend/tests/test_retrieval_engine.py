"""Test outer graph (agentic planning): normalize -> rewrite -> plan -> gather -> assess -> loop.

Không gọi FPT thật: mock llm_client.chat (plan/assess) + engine._search / engine._catalog_outline.
"""
from app.config import settings
from app.retrieval import engine, nodes


def _chunk(cid, doc, idx, score, content, title="Doc"):
    return {"chunk_id": cid, "document_id": doc, "title": title, "chunk_index": idx, "score": score, "final_content": content}


def _mock_common(monkeypatch):
    monkeypatch.setattr(settings, "retrieval_enable_normalize", True)
    monkeypatch.setattr(settings, "retrieval_enable_rewrite", False)  # passthrough, khỏi mock rewrite
    monkeypatch.setattr(settings, "retrieval_enable_planning", True)
    monkeypatch.setattr(settings, "retrieval_max_hops", 3)
    monkeypatch.setattr(engine, "_catalog_outline", lambda q, k: "")


def test_planning_decomposes_and_covers_each_subgoal(monkeypatch):
    _mock_common(monkeypatch)

    def fake_chat(messages, **kw):
        tag = kw.get("tag")
        if tag == "retrieval_plan":
            return '{"subgoals":[{"description":"quyền lợi A","query":"quyền lợi bảo hiểm A"},{"description":"quyền lợi B","query":"quyền lợi bảo hiểm B"}]}'
        if tag == "retrieval_assess":
            return '{"results":[{"id":"g1","satisfied":true},{"id":"g2","satisfied":true}]}'
        return ""

    monkeypatch.setattr(nodes.llm_client, "chat", fake_chat)
    # mỗi sub-goal query khác nhau -> trả chunk khác nhau (giữ coverage cả 2)
    def fake_search(query, k):
        if "A" in query:
            return [_chunk("cA", "dA", 0, 0.8, "Quyền lợi A: ...", "Bảo hiểm A")]
        return [_chunk("cB", "dB", 0, 0.7, "Quyền lợi B: ...", "Bảo hiểm B")]

    monkeypatch.setattr(engine, "_search", fake_search)

    out = engine.build_graph().invoke(
        {"question": "So sánh quyền lợi bảo hiểm A và B", "top_k": 5, "subgoals": [], "hops": 0, "tool_calls": [], "citations": []},
        config={"recursion_limit": 20},
    )
    docs = {c.document_id for c in out["citations"]}
    assert docs == {"dA", "dB"}                     # coverage: cả 2 sản phẩm đều có citation
    assert len(out["subgoals"]) == 2
    assert all(sg["satisfied"] for sg in _cov(out))


def test_loop_broadens_until_satisfied_then_stops(monkeypatch):
    _mock_common(monkeypatch)
    rounds = {"assess": 0}

    def fake_chat(messages, **kw):
        tag = kw.get("tag")
        if tag == "retrieval_plan":
            return '{"subgoals":[{"description":"phí thẻ","query":"phí thẻ Sung Túc"}]}'
        if tag == "retrieval_assess":
            rounds["assess"] += 1
            satisfied = rounds["assess"] >= 2      # vòng 1 thiếu -> loop; vòng 2 đủ -> dừng
            return '{"results":[{"id":"g1","satisfied":%s}]}' % ("true" if satisfied else "false")
        return ""

    monkeypatch.setattr(nodes.llm_client, "chat", fake_chat)
    monkeypatch.setattr(engine, "_search", lambda q, k: [_chunk("c1", "d1", 0, 0.6, "phí ...")])

    out = engine.build_graph().invoke(
        {"question": "phí thẻ", "top_k": 5, "subgoals": [], "hops": 0, "tool_calls": [], "citations": []},
        config={"recursion_limit": 20},
    )
    assert rounds["assess"] == 2                    # đã loop đúng 1 lần rồi dừng
    assert out["hops"] == 2
    assert len(out["citations"]) == 1


def test_budget_caps_hops_when_never_satisfied(monkeypatch):
    _mock_common(monkeypatch)
    monkeypatch.setattr(settings, "retrieval_max_hops", 2)

    def fake_chat(messages, **kw):
        if kw.get("tag") == "retrieval_plan":
            return '{"subgoals":[{"description":"x","query":"x"}]}'
        if kw.get("tag") == "retrieval_assess":
            return '{"results":[{"id":"g1","satisfied":false,"note":"thiếu"}]}'
        return ""

    monkeypatch.setattr(nodes.llm_client, "chat", fake_chat)
    monkeypatch.setattr(engine, "_search", lambda q, k: [_chunk("c1", "d1", 0, 0.2, "yếu")])

    out = engine.build_graph().invoke(
        {"question": "x", "top_k": 5, "subgoals": [], "hops": 0, "tool_calls": [], "citations": []},
        config={"recursion_limit": 20},
    )
    assert out["hops"] == 2                          # dừng đúng budget dù chưa satisfied
    assert _cov(out)[0]["satisfied"] is False
    assert _cov(out)[0]["note"]                      # nêu được phần còn thiếu


def test_planning_disabled_single_subgoal(monkeypatch):
    _mock_common(monkeypatch)
    monkeypatch.setattr(settings, "retrieval_enable_planning", False)

    def fake_chat(messages, **kw):
        if kw.get("tag") == "retrieval_assess":
            return '{"results":[{"id":"g1","satisfied":true}]}'
        return ""

    monkeypatch.setattr(nodes.llm_client, "chat", fake_chat)
    monkeypatch.setattr(engine, "_search", lambda q, k: [_chunk("c1", "d1", 0, 0.9, "data")])

    out = engine.build_graph().invoke(
        {"question": "phí thường niên?", "top_k": 5, "subgoals": [], "hops": 0, "tool_calls": [], "citations": []},
        config={"recursion_limit": 20},
    )
    assert len(_cov(out)) == 1                        # planning tắt -> 1 sub-goal = cả câu hỏi


def _cov(out):
    """engine.retrieve() bọc coverage; ở đây invoke() trả state thô -> tự build coverage."""
    return engine._subgoal_coverage(out["subgoals"])
