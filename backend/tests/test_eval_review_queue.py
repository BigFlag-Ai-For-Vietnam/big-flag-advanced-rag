"""Test review queue spec (FR-7) — offline, deps mlflow được fake tường minh."""
from types import SimpleNamespace

from eval.review_queue import ANSWER_Q, APPROVE_Q, CONTEXTS_Q, ReviewQueueDeps, create_dataset_review_queue


def test_review_queue_spec():
    created_schemas = []
    created_queue = {}
    added_items = {}
    search_calls = []

    def fake_create_label_schema(*, name, type, input, instruction, enable_comment):
        created_schemas.append({"name": name, "type": type, "input": input, "instruction": instruction})
        return SimpleNamespace(schema_id=f"schema-{name}")

    def fake_create_review_queue(*, name, queue_type, schema_ids):
        created_queue.update(name=name, queue_type=queue_type, schema_ids=schema_ids)
        return SimpleNamespace(queue_id="queue-1")

    def fake_add_items_to_review_queue(queue_id, *, item_ids):
        added_items["queue_id"] = queue_id
        added_items["item_ids"] = item_ids

    def fake_search_traces(*, filter_string, return_type):
        search_calls.append(filter_string)
        return [SimpleNamespace(trace_id="tr-1"), SimpleNamespace(trace_id="tr-2")]

    class FakePassFail:
        def __init__(self, positive_label, negative_label):
            self.positive_label = positive_label
            self.negative_label = negative_label

    class FakeText:
        def __init__(self):
            pass

    deps = ReviewQueueDeps(
        create_label_schema=fake_create_label_schema,
        create_review_queue=fake_create_review_queue,
        add_items_to_review_queue=fake_add_items_to_review_queue,
        search_traces=fake_search_traces,
        input_pass_fail=FakePassFail,
        input_text=FakeText,
    )

    queue_id = create_dataset_review_queue("d1", deps=deps)

    assert queue_id == "queue-1"
    assert search_calls == ["tags.dataset_name = 'd1'"]

    names = [s["name"] for s in created_schemas]
    assert names == [APPROVE_Q, ANSWER_Q, CONTEXTS_Q]
    approve_schema = created_schemas[0]
    assert isinstance(approve_schema["input"], FakePassFail)
    answer_schema = created_schemas[1]
    assert isinstance(answer_schema["input"], FakeText)
    contexts_schema = created_schemas[2]
    assert isinstance(contexts_schema["input"], FakeText)

    assert created_queue["schema_ids"] == ["schema-approve", "schema-expected_response", "schema-reference_contexts"]
    assert added_items["queue_id"] == "queue-1"
    assert added_items["item_ids"] == ["tr-1", "tr-2"]
