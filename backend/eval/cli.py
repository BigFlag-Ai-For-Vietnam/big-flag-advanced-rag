"""CLI đánh giá RAG: python -m eval <lệnh>.

Rev 2 (spec.md): 2 lệnh cấp cao nhất, mirror đúng 2 process tách biệt —
  python -m eval dataset {generate,review-queue,promote}   # Build/Generate TestDataset
  python -m eval judge --dataset <name>                     # Eval/Judge
Lệnh phẳng cũ (generate/review-queue/promote/run ở top-level) KHÔNG còn tồn tại —
argparse tự từ chối là lệnh không hợp lệ (unknown command)."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

TOP_LEVEL_COMMANDS: tuple[str, ...] = ("dataset", "judge")
DATASET_SUBCOMMANDS: tuple[str, ...] = ("generate", "review-queue", "promote")


def cmd_generate(args: argparse.Namespace) -> int:
    """Sinh testset (silver) từ tài liệu đã index: KG -> query_distribution -> per-persona
    generate -> silver JSONL -> upload MLflow dataset. Yêu cầu: có personas.json (FR-4),
    tài liệu ở trạng thái indexed (FR-1)."""
    from eval.dataset_source import collect_chunks, build_and_log_kg
    from eval.dataset_upload import upload as upload_dataset
    from eval.distribution import (
        DistributionWeights,
        apply_backfill,
        build_query_distribution,
        multi_hop_availability,
    )
    from eval.judge import build_judge
    from eval.personas import (
        PersonaError,
        load_personas,
        log_personas_artifact,
        plan_persona_batches,
        stamp_persona_name,
    )

    import mlflow
    from app.config import settings
    from app.db import SessionLocal
    from ragas.testset import TestsetGenerator

    try:
        personas = load_personas(args.personas)
    except PersonaError as exc:
        print(f"Lỗi persona: {exc}", file=sys.stderr)
        return 1

    document_ids = None if args.all else (args.documents or [])
    if not args.all and not document_ids:
        print("Cần chỉ định --documents id[,id...] hoặc --all", file=sys.stderr)
        return 1

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)

    session = SessionLocal()
    try:
        chunks = collect_chunks(session, document_ids)
    finally:
        session.close()

    if not chunks:
        print("Không có chunk nào để sinh testset (kiểm tra trạng thái indexed).", file=sys.stderr)
        return 1

    bundle = build_judge()
    mlflow.openai.autolog()  # trace tự động mọi lời gọi LLM/embedding (KG transforms + generate)

    with mlflow.start_run(run_name="eval-generate"):
        log_personas_artifact(args.personas)  # NFR-4: personas.json là input, phải log lại
        kg_path = Path(args.out_dir) / "kg.json"
        if args.kg_file:
            # KG ngoài (FR-2): chunk node thô (không transforms) + entities/relations từ contract.
            from eval.kg_contract import contract_to_kg, load_contract

            kg = build_and_log_kg(chunks, kg_path, transforms=[])
            kg = contract_to_kg(load_contract(args.kg_file), kg)
            kg.save(str(kg_path))
            mlflow.log_artifact(str(kg_path))
        else:
            kg = build_and_log_kg(chunks, kg_path, llm=bundle.llm, embedding_model=bundle.embeddings)

        weights = DistributionWeights(
            single_hop_specific=args.w_single,
            multi_hop_abstract=args.w_multi_abstract,
            multi_hop_specific=args.w_multi_specific,
        )
        distribution = build_query_distribution(bundle.llm, weights=weights)
        # Synthesizer trọng số 0 vẫn PHẢI bị loại khỏi distribution trước khi generate():
        # ragas._generate_scenarios của multi-hop tính cluster bất kể n, raise ValueError
        # nếu KG không có cluster nào — kể cả khi n=0. Trọng số 0 không tự động an toàn.
        distribution = [(synth, w) for synth, w in distribution if w > 0]

        # FR-3 (r2): KG không tạo được cluster cho 1 multi-hop synthesizer -> dồn trọng số
        # về trivial (single-hop) thay vì để generate() raise ValueError giữa chừng.
        availability = multi_hop_availability(kg, distribution)
        distribution, backfill_report = apply_backfill(distribution, availability)
        if backfill_report:
            backfill_path = Path(args.out_dir) / "multihop_backfill_report.json"
            backfill_path.parent.mkdir(parents=True, exist_ok=True)
            backfill_path.write_text(
                json.dumps(backfill_report, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            mlflow.log_artifact(str(backfill_path))
            for row in backfill_report:
                print(
                    f"Cảnh báo: synthesizer '{row['synthesizer_name']}' không có cluster nào "
                    f"trên KG ({row['num_clusters']} cluster) — dồn trọng số "
                    f"{row['reallocated_weight']:.2f} về trivial (single-hop).",
                    file=sys.stderr,
                )

        batches = plan_persona_batches(personas, args.size)

        all_samples: list[dict] = []
        for batch in batches:
            generator = TestsetGenerator(
                llm=bundle.llm,
                embedding_model=bundle.embeddings,
                knowledge_graph=kg,
                persona_list=[batch.persona.to_ragas()],
            )
            testset = generator.generate(testset_size=batch.size, query_distribution=distribution)
            eval_samples = [s.eval_sample for s in testset.samples]
            stamp_persona_name(eval_samples, batch.persona.name)
            for s, sample in zip(testset.samples, eval_samples):
                d = sample.model_dump(exclude_none=True)
                d["synthesizer_name"] = s.synthesizer_name
                all_samples.append(d)

        silver_path = Path(args.out_dir) / "silver.jsonl"
        silver_path.parent.mkdir(parents=True, exist_ok=True)
        with silver_path.open("w", encoding="utf-8") as f:
            for sample in all_samples:
                f.write(json.dumps(sample, ensure_ascii=False) + "\n")
        mlflow.log_artifact(str(silver_path))

        # FR-16 (r3): đường chính — upload thẳng mẫu sinh ra lên MLflow Evaluation Dataset
        # đặt tên; merge_records upsert (T06) nên chạy lại `generate` không nhân đôi record.
        upload_result = upload_dataset(args.dataset, all_samples)
        dataset_upload_path = Path(args.out_dir) / "dataset_upload.jsonl"
        dataset_upload_path.write_text(upload_result.jsonl, encoding="utf-8")
        mlflow.log_artifact(str(dataset_upload_path))
        print(
            f"Đã upload {len(upload_result.records)} mẫu lên MLflow Evaluation Dataset "
            f"'{upload_result.dataset_name}'."
        )

        print(f"Sinh {len(all_samples)} mẫu silver tại {silver_path}")
        return 0


def cmd_review_queue(args: argparse.Namespace) -> int:
    """Tạo MLflow Review Queue cho SME duyệt silver traces của --dataset."""
    from eval.review_queue import create_dataset_review_queue

    queue_id = create_dataset_review_queue(args.dataset)
    print(f"Đã tạo review queue: {queue_id}")
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    """Gom trace silver đã SME duyệt -> golden Evaluation Dataset (FR-8)."""
    import mlflow
    from mlflow.exceptions import MlflowException
    from mlflow.genai.datasets import create_dataset, get_dataset

    from app.config import settings
    from eval.promote import promote

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    experiment = mlflow.set_experiment(settings.mlflow_experiment)

    def _search_traces(*, filter_string):
        combined = f"tags.dataset_name = '{args.dataset}' AND {filter_string}"
        return mlflow.search_traces(
            locations=[experiment.experiment_id],
            filter_string=combined,
            return_type="list",
        )

    def _get_or_create_dataset(name):
        try:
            return get_dataset(name=name)
        except MlflowException:
            return create_dataset(name=name, experiment_id=[experiment.experiment_id])

    result = promote(
        args.dataset,
        search_traces=_search_traces,
        get_or_create_dataset=_get_or_create_dataset,
        log_text=mlflow.log_text,
    )
    print(f"Đã promote {len(result.records)} mẫu vào dataset {result.dataset_name}")
    return 0


def cmd_judge(args: argparse.Namespace) -> int:
    """Chạy eval: nạp dataset -> RAG thật (có trace) qua qa_service -> chấm bằng tích hợp
    native mlflow.genai.evaluate() + mlflow.genai.scorers.ragas (KHÔNG dùng ragas.evaluate()
    thủ công — MLflow tự tạo Evaluations view, log assessment lên từng trace).

    Judge FPT được truyền cho scorer dưới dạng model URI ("openai:/<model>") — cơ chế của
    mlflow.genai.scorers.ragas chỉ nhận URI, tự dựng client bên trong qua litellm/openai SDK,
    nên KHÔNG thể tiêm qua llm_client.make_openai_client() như các nơi khác trong eval/.
    Đây là giới hạn của chính tích hợp native, không phải lựa chọn thiết kế ở đây — vẫn cấu
    hình endpoint FPT qua biến môi trường chuẩn OpenAI (OPENAI_API_KEY/OPENAI_API_BASE)."""
    import os

    import mlflow

    from app.config import settings
    from app.services.llm_client import make_openai_client
    from eval.runner import run as run_eval
    from eval.techniques import resolve as resolve_technique

    try:
        technique = resolve_technique(args.technique)
    except ValueError as exc:
        print(f"Lỗi: {exc}", file=sys.stderr)
        return 1

    os.environ["OPENAI_API_KEY"] = settings.fpt_api_key
    os.environ["OPENAI_API_BASE"] = settings.fpt_base_url
    os.environ["OPENAI_BASE_URL"] = settings.fpt_base_url

    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    mlflow.set_experiment(settings.mlflow_experiment)
    mlflow.openai.autolog()

    traces = run_eval(args.dataset, top_k=args.top_k, technique=technique)
    if not traces:
        print("Dataset rỗng, không có gì để eval.", file=sys.stderr)
        return 1

    from ragas.embeddings import OpenAIEmbeddings
    from mlflow.genai.scorers.ragas import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        FactualCorrectness,
        Faithfulness,
    )

    judge_uri = f"openai:/{settings.eval_judge_model or settings.fpt_chat_model}"
    embeddings = OpenAIEmbeddings(client=make_openai_client(async_client=True), model=settings.fpt_embed_model)
    scorers = [
        Faithfulness(model=judge_uri),
        AnswerRelevancy(model=judge_uri, embeddings=embeddings),
        ContextPrecision(model=judge_uri),
        ContextRecall(model=judge_uri),
        FactualCorrectness(model=judge_uri),
    ]

    result = mlflow.genai.evaluate(data=traces, scorers=scorers)

    # FR-12 (r3): tag technique + breakdown theo tier/persona — mlflow.genai.evaluate() tự
    # log điểm tổng hợp + assessment lên trace, nhưng không tự tag technique hay slice theo
    # synthesizer_name/persona_name (T26).
    from eval.judge_logging import breakdowns, log_run_metadata, rows_from_traces

    scored_traces = mlflow.search_traces(run_id=result.run_id, return_type="list")
    rows = rows_from_traces(scored_traces)

    params = {
        "eval_judge_model": settings.eval_judge_model or settings.fpt_chat_model,
        "eval_embed_model": settings.fpt_embed_model,
        "eval_top_k": args.top_k,
        "eval_dataset": args.dataset,
        "eval_dataset_size": len(traces),
    }
    log_run_metadata(args.technique, params, breakdowns(rows), run_id=result.run_id)

    print(f"Eval xong: {len(traces)} mẫu. Xem kết quả ở MLflow — tab Evaluations của experiment.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m eval", description="RAG evaluation CLI (RAGAS + MLflow)")
    top = parser.add_subparsers(dest="command", required=True)

    # --- python -m eval dataset {generate,review-queue,promote} ---
    p_dataset = top.add_parser("dataset", help="Build/Generate TestDataset: sinh + SME review + promote")
    dataset_sub = p_dataset.add_subparsers(dest="dataset_command", required=True)

    p_generate = dataset_sub.add_parser("generate", help="Sinh testset silver từ tài liệu đã index")
    p_generate.add_argument("--documents", nargs="+", default=None, help="Danh sách document id")
    p_generate.add_argument("--all", action="store_true", help="Dùng mọi tài liệu đã indexed")
    p_generate.add_argument(
        "--dataset", required=True,
        help="Tên MLflow Evaluation Dataset để upload mẫu sinh ra (FR-16, bắt buộc)",
    )
    p_generate.add_argument("--size", type=int, default=10, help="Tổng số câu hỏi sinh ra")
    p_generate.add_argument("--personas", default="personas.json", help="Đường dẫn personas.json (bắt buộc)")
    p_generate.add_argument("--out-dir", default="eval_runs/generate", help="Thư mục ghi artifact")
    p_generate.add_argument("--kg-file", default=None, help="KG ngoài theo contract v1 (FR-2), thay cho KG tự dựng")
    p_generate.add_argument("--w-single", type=float, default=0.5, help="Trọng số single-hop specific (mặc định 0.5)")
    p_generate.add_argument("--w-multi-abstract", type=float, default=0.25, help="Trọng số multi-hop abstract (mặc định 0.25)")
    p_generate.add_argument("--w-multi-specific", type=float, default=0.25, help="Trọng số multi-hop specific (mặc định 0.25)")
    p_generate.set_defaults(func=cmd_generate)

    p_review_queue = dataset_sub.add_parser("review-queue", help="Tạo MLflow Review Queue cho SME duyệt silver")
    p_review_queue.add_argument("--dataset", required=True, help="Tên dataset (tag dataset_name của trace silver)")
    p_review_queue.set_defaults(func=cmd_review_queue)

    p_promote = dataset_sub.add_parser("promote", help="Gom trace đã SME duyệt vào golden Evaluation Dataset")
    p_promote.add_argument("--dataset", required=True, help="Tên dataset (tag dataset_name của trace silver)")
    p_promote.set_defaults(func=cmd_promote)

    # --- python -m eval judge --dataset <name> (top-level, không phụ thuộc trạng thái dataset-build) ---
    p_judge = top.add_parser(
        "judge",
        help="Chạy RAG thật (Qdrant retrieval + answer) + ragas evaluate, log trace/assessment vào MLflow",
    )
    p_judge.add_argument("--dataset", required=True, help="Tên golden dataset (MLflow) hoặc đường dẫn silver JSONL")
    p_judge.add_argument("--top-k", type=int, default=5, help="Số chunk retrieval (mặc định khớp playground)")
    p_judge.add_argument(
        "--technique", default="trivial",
        help="Kỹ thuật RAG chấm (registry eval.techniques, mặc định 'trivial')",
    )
    p_judge.set_defaults(func=cmd_judge)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
