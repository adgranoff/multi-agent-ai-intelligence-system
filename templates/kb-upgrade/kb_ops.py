#!/usr/bin/env python3
"""Master operations CLI for the knowledge base."""

import argparse
import csv
import json
import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List

import requests

import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from build_index import IndexBuilder  # noqa: E402
from combined_search import CombinedSearch  # noqa: E402
from common import default_kb_root, dump_frontmatter, find_api_key, list_entity_files, load_json, parse_frontmatter, save_json, slugify, utc_now_iso  # noqa: E402
from decay import ConfidenceDecay  # noqa: E402
from graph_builder import GraphBuilder  # noqa: E402
from graph_query import GraphQuery  # noqa: E402
from graph_report import GraphReport  # noqa: E402
from librarian import LibrarianRunner  # noqa: E402
from search import KBSearch  # noqa: E402


logger = logging.getLogger(__name__)


def parse_api_usage(api_log: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not api_log.exists():
        return rows
    for line in api_log.read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 5:
            continue
        ts, endpoint, model, tokens, cost = parts[:5]
        try:
            rows.append(
                {
                    "timestamp": ts,
                    "endpoint": endpoint,
                    "model": model,
                    "tokens": int(float(tokens)),
                    "cost": float(cost.replace("$", "")),
                }
            )
        except Exception:
            continue
    return rows


def entity_stats(kb_root: Path) -> Dict[str, Any]:
    files = list_entity_files(kb_root)
    counts = {"lab": 0, "model": 0, "person": 0, "company": 0, "investor": 0, "regulator": 0, "theme": 0}
    signals = 0
    stale = 0
    low_conf = 0
    contradictions = 0
    now = datetime.utcnow()

    for f in files:
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        t = fm.get("type", "unknown")
        if t in counts:
            counts[t] += 1
        signals += len(fm.get("signals", []) or [])

        conf = float(fm.get("confidence", 0.5))
        if conf < 0.3:
            low_conf += 1

        lc = fm.get("last_confirmed")
        if isinstance(lc, str):
            try:
                dt = datetime.strptime(lc[:10], "%Y-%m-%d")
                if (now - dt).days > 21:
                    stale += 1
            except Exception:
                pass

        for s in fm.get("signals", []) or []:
            if s.get("contradicts"):
                contradictions += 1
            if s.get("contradicting_claims"):
                contradictions += len(s.get("contradicting_claims", []))

    return {
        "counts": counts,
        "total_entities": sum(counts.values()),
        "signals": signals,
        "stale": stale,
        "low_conf": low_conf,
        "contradictions": contradictions,
    }


def cmd_process(args: argparse.Namespace) -> None:
    runner = LibrarianRunner(Path(args.kb_path))
    if args.file:
        report = runner.process_digest(Path(args.file), model=args.model, verify=args.verify, dry_run=args.dry_run)
        print(json.dumps(report, indent=2))
    else:
        reports = runner.process_pending(model=args.model, verify=args.verify, dry_run=args.dry_run)
        print(json.dumps(reports, indent=2))


def cmd_search(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    if args.graph:
        rows = CombinedSearch(kb_root).search(args.query, top_k=args.top_k, min_confidence=args.min_confidence)
        print(json.dumps(rows, indent=2) if args.json else "\n".join([f"{r['canonical_name']} ({r['type']}) score={r['score']}" for r in rows]))
        return

    rows = KBSearch(kb_root).query(
        query_text=args.query,
        top_k=args.top_k,
        entity_type=args.entity_type,
        min_confidence=args.min_confidence if args.min_confidence > 0 else None,
    )
    print(json.dumps(rows, indent=2) if args.json else "\n".join([f"{r['entity_name']} ({r['entity_type']}) score={r['score']}" for r in rows]))


def cmd_graph(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    if args.graph_cmd == "rebuild":
        g = GraphBuilder(kb_root)
        graph = g.build_graph()
        g.export()
        print(f"Graph rebuilt: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")
        return

    q = GraphQuery(kb_root)
    if args.graph_cmd == "connections":
        print(q.connections(args.entity))
    elif args.graph_cmd == "lineage":
        print(q.lineage(args.model))
    elif args.graph_cmd == "talent-flow":
        print(q.talent_flow(from_lab=args.from_lab, to_lab=args.to_lab))
    elif args.graph_cmd == "supply-chain":
        print(q.supply_chain(args.entity))
    elif args.graph_cmd == "landscape":
        print(q.landscape(args.entity))
    elif args.graph_cmd == "theme-map":
        print(q.theme_map(args.theme))
    elif args.graph_cmd == "anomalies":
        print(q.anomalies())


def cmd_status(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    stats = entity_stats(kb_root)
    idx_stats = IndexBuilder(kb_root).get_stats()["index"]
    graph_data = load_json(kb_root / "indexes" / "relations.json", {"metadata": {}})
    graph_edges = int((graph_data.get("metadata") or {}).get("edges", 0))

    incoming = list((kb_root / "digests" / "incoming").glob("*.md"))
    digest_log = load_json(kb_root / "indexes" / "digest-log.json", {"runs": []}).get("runs", [])
    last_processed = digest_log[-1]["processed_at"] if digest_log else "never"

    api_rows = parse_api_usage(kb_root / "logs" / "api-usage.log")
    today = datetime.utcnow().date().isoformat()
    month_prefix = today[:7]
    cost_today = sum(r["cost"] for r in api_rows if r["timestamp"].startswith(today))
    cost_month = sum(r["cost"] for r in api_rows if r["timestamp"].startswith(month_prefix))

    print("╔═══════════════════════════════════════════════════╗")
    print("║               Knowledge Base Ops                  ║")
    print("╠═══════════════════════════════════════════════════╣")
    print(f"║  Entities:     {stats['total_entities']:<4} total                       ║")
    print(f"║    Labs: {stats['counts']['lab']:<2} | Models: {stats['counts']['model']:<2} | People: {stats['counts']['person']:<2}            ║")
    print(f"║    Companies: {stats['counts']['company']:<2} | Investors: {stats['counts']['investor']:<2} | Regulators: {stats['counts']['regulator']:<2}   ║")
    print(f"║    Themes: {stats['counts']['theme']:<2}                                     ║")
    print(f"║  Signals:      {stats['signals']:<4}                           ║")
    print(f"║  Relations:    {graph_edges:<4} edges                         ║")
    print(f"║  Vector Index: {idx_stats.get('total_chunks', 0):<4} chunks                        ║")
    print("╠═══════════════════════════════════════════════════╣")
    print("║  Pipeline Status:                                 ║")
    print(f"║    Digests pending:    {len(incoming):<3}                           ║")
    print(f"║    Last processed:     {last_processed[:19]:<19}             ║")
    print("╠═══════════════════════════════════════════════════╣")
    print("║  Health:                                          ║")
    print(f"║    Stale (>21 days):       {stats['stale']:<3} entities             ║")
    print(f"║    Low confidence (<0.3):  {stats['low_conf']:<3} entities             ║")
    print(f"║    Contradictions:         {stats['contradictions']:<3} active               ║")
    print("╠═══════════════════════════════════════════════════╣")
    print(f"║  Costs ({month_prefix}):                                ║")
    print(f"║    Today:         ${cost_today:<7.4f}                        ║")
    print(f"║    Month:         ${cost_month:<7.4f}                        ║")
    print("╚═══════════════════════════════════════════════════╝")


def cmd_validate(args: argparse.Namespace) -> None:
    script = Path(__file__).parent / "validate_schema.py"
    rc = shutil.which("python3") or "python3"
    proc = __import__("subprocess").run([rc, str(script), "--kb-path", args.kb_path], check=False)
    raise SystemExit(proc.returncode)


def cmd_decay(args: argparse.Namespace) -> None:
    result = ConfidenceDecay(Path(args.kb_path)).run(apply_changes=args.apply)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(ConfidenceDecay.format_report(result))


def cmd_rebuild(args: argparse.Namespace) -> None:
    builder = IndexBuilder(Path(args.kb_path))
    result = builder.build_full() if args.full else builder.build_incremental()
    print(json.dumps(result, indent=2))


def _generate_weekly_memo(kb_root: Path) -> Path:
    key = find_api_key()
    stats = entity_stats(kb_root)
    digest_log = load_json(kb_root / "indexes" / "digest-log.json", {"runs": []}).get("runs", [])
    recent = digest_log[-10:]
    coverage_gaps: List[str] = []
    for run in recent:
        for gap in (((run.get("digest_assessment") or {}).get("coverage_gaps")) or []):
            if isinstance(gap, str) and gap not in coverage_gaps:
                coverage_gaps.append(gap)
    stale_entities = []
    for f in list_entity_files(kb_root):
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        lc = str(fm.get("last_confirmed", ""))[:10]
        if not lc:
            continue
        try:
            days = (datetime.utcnow() - datetime.strptime(lc, "%Y-%m-%d")).days
            if days > 21:
                stale_entities.append(fm.get("entity", f.stem))
        except Exception:
            continue

    prompt = (
        "Write an executive weekly intelligence memo for an AI strategy operator. "
        "Use sections: EXECUTIVE SUMMARY, MODEL LANDSCAPE, LAB DYNAMICS, TALENT RADAR, POLICY & REGULATION, "
        "EMERGING THEMES, CONTRADICTIONS & OPEN QUESTIONS, STALE INTELLIGENCE, COVERAGE GAPS, RECOMMENDED ACTIONS.\n\n"
        f"Entity stats: {json.dumps(stats)}\n"
        f"Recent digest runs: {json.dumps(recent)}\n"
    )

    def _fallback() -> str:
        top_updates = recent[-3:]
        lines = [
            f"# Weekly Intelligence Memo - {datetime.utcnow().date().isoformat()}",
            "",
            "## EXECUTIVE SUMMARY",
            f"- KB currently tracks {stats['total_entities']} entities across labs, models, people, companies, and themes.",
            f"- {len(recent)} digest runs were recorded in the recent window.",
            f"- {stats['signals']} total signals are currently indexed.",
            "",
            "## MODEL LANDSCAPE",
            f"- Models tracked: {stats['counts']['model']}.",
            "- See `reports/snapshots/models-YYYY-MM-DD.md` for current benchmark/pricing table.",
            "",
            "## LAB DYNAMICS",
            f"- Labs tracked: {stats['counts']['lab']}; relation graph edges: {load_json(kb_root / 'indexes' / 'relations.json', {'metadata': {}}).get('metadata', {}).get('edges', 0)}.",
            "",
            "## TALENT RADAR",
            f"- People tracked: {stats['counts']['person']}.",
            "",
            "## POLICY & REGULATION",
            f"- Regulators tracked: {stats['counts']['regulator']}.",
            "",
            "## EMERGING THEMES",
            f"- Themes tracked: {stats['counts']['theme']}.",
            "",
            "## CONTRADICTIONS & OPEN QUESTIONS",
            f"- Active contradictions flagged in KB: {stats['contradictions']}.",
            "",
            "## STALE INTELLIGENCE",
            f"- Entities with stale confirmation (>21 days): {stats['stale']}.",
            "- Stale entities: " + (", ".join(stale_entities[:10]) if stale_entities else "none"),
            "",
            "## COVERAGE GAPS",
            "- " + ("\n- ".join(coverage_gaps[:8]) if coverage_gaps else "No explicit coverage gaps recorded in recent runs."),
            "",
            "## RECOMMENDED ACTIONS",
            "1. Process pending digests daily and review contradictions weekly.",
            "2. Refresh stale entities and enrich missing model lineage relations.",
            "3. Rebuild index and graph after each ingest cycle.",
            "",
            "## RECENT RUN SNAPSHOT",
        ]
        if top_updates:
            for r in top_updates:
                lines.append(
                    f"- {r.get('digest', 'unknown')}: +{r.get('signals_added', 0)} signals, "
                    f"{r.get('entities_created', 0)} created, {r.get('entities_updated', 0)} updated."
                )
        else:
            lines.append("- No recent run entries found.")
        return "\n".join(lines) + "\n"

    if not key:
        text = _fallback()
    else:
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://example.invalid",
            "X-Title": "Weekly Memo",
        }
        payload = {
            "model": "deepseek/deepseek-chat-v3-0324",
            "messages": [
                {"role": "system", "content": "You are an AI industry intelligence editor."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 2200,
        }
        try:
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload, timeout=180)
            resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
        except requests.RequestException as exc:
            logger.warning("Weekly memo LLM call failed, using fallback memo: %s", exc)
            text = _fallback()

    out = kb_root / "reports" / "weekly" / f"memo-{datetime.utcnow().date().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text.strip() + "\n", encoding="utf-8")
    return out


def _generate_model_snapshot(kb_root: Path) -> Path:
    model_files = sorted((kb_root / "entities" / "models").glob("*.md"))
    rows = []
    for f in model_files:
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        md = fm.get("model_details", {}) or {}
        pricing = md.get("api_pricing", {}) or {}
        bench = {b.get("name"): b.get("score") for b in md.get("notable_benchmarks", []) or []}
        rows.append(
            {
                "Model": fm.get("entity", f.stem),
                "Lab": (fm.get("relations", {}) or {}).get("open_sourced_by", [""])[0] if isinstance((fm.get("relations", {}) or {}).get("open_sourced_by", []), list) else "",
                "Released": md.get("release_date"),
                "Context": md.get("context_window"),
                "$/M In": pricing.get("input_per_m"),
                "$/M Out": pricing.get("output_per_m"),
                "SWE-bench": bench.get("SWE-bench", ""),
                "MMLU": bench.get("MMLU", ""),
                "License": md.get("license"),
            }
        )

    rows.sort(key=lambda x: str(x.get("Released") or ""), reverse=True)

    out = kb_root / "reports" / "snapshots" / f"models-{datetime.utcnow().date().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write("| Model | Lab | Released | Context | $/M In | $/M Out | SWE-bench | MMLU | License |\n")
        f.write("|---|---|---|---|---:|---:|---|---|---|\n")
        for r in rows:
            f.write(
                f"| {r['Model']} | {r['Lab']} | {r['Released']} | {r['Context']} | {r['$/M In']} | {r['$/M Out']} | {r['SWE-bench']} | {r['MMLU']} | {r['License']} |\n"
            )
    return out


def _generate_theme_report(kb_root: Path) -> Path:
    theme_files = sorted((kb_root / "themes").glob("*.md"))
    out = kb_root / "reports" / "snapshots" / f"themes-{datetime.utcnow().date().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Theme Evolution Snapshot", ""]
    for f in theme_files:
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        lines.append(f"## {fm.get('entity', f.stem)}")
        lines.append(f"- Confidence: {fm.get('confidence')}")
        lines.append(f"- Last Updated: {fm.get('last_updated')}")
        lines.append(f"- Summary: {fm.get('summary', '')}")
        lines.append("")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def cmd_report(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    if args.report_type == "weekly":
        path = _generate_weekly_memo(kb_root)
    elif args.report_type == "models":
        path = _generate_model_snapshot(kb_root)
    else:
        path = _generate_theme_report(kb_root)
    print(f"Report saved: {path}")


def cmd_costs(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    rows = parse_api_usage(kb_root / "logs" / "api-usage.log")
    now = datetime.utcnow()
    if args.today:
        prefix = now.date().isoformat()
        rows = [r for r in rows if r["timestamp"].startswith(prefix)]
    elif args.month:
        prefix = now.date().isoformat()[:7]
        rows = [r for r in rows if r["timestamp"].startswith(prefix)]

    by_endpoint: Dict[str, float] = {}
    total = 0.0
    for r in rows:
        by_endpoint[r["endpoint"]] = by_endpoint.get(r["endpoint"], 0.0) + r["cost"]
        total += r["cost"]

    print("Cost Summary")
    for k, v in sorted(by_endpoint.items()):
        print(f"- {k}: ${v:.6f}")
    print(f"Total: ${total:.6f}")


def cmd_export(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    rows = []
    for f in list_entity_files(kb_root):
        fm, _ = parse_frontmatter(f.read_text(encoding="utf-8"))
        rows.append({
            "entity": fm.get("entity", f.stem),
            "type": fm.get("type"),
            "confidence": fm.get("confidence"),
            "status": fm.get("status"),
            "last_updated": fm.get("last_updated"),
            "path": str(f.relative_to(kb_root)),
        })

    out = kb_root / "reports" / "snapshots" / f"export-{datetime.utcnow().date().isoformat()}.{args.format}"
    out.parent.mkdir(parents=True, exist_ok=True)

    if args.format == "json":
        out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    else:
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()) if rows else ["entity", "type", "confidence", "status", "last_updated", "path"])
            w.writeheader()
            for r in rows:
                w.writerow(r)

    print(f"Export saved: {out}")


def cmd_archive(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    target = args.entity.lower()
    matches = []
    for f in list_entity_files(kb_root):
            fm, body = parse_frontmatter(f.read_text(encoding="utf-8"))
            if str(fm.get("entity", "")).lower() == target or f.stem.lower() == slugify(target):
                fm["status"] = "archived"
                fm["last_updated"] = utc_now_iso()
                f.write_text(dump_frontmatter(fm, body), encoding="utf-8")
                matches.append(str(f))
    if not matches:
        raise SystemExit(f"Entity not found: {args.entity}")
    print("Archived:")
    for m in matches:
        print(f"- {m}")


def cmd_backup(args: argparse.Namespace) -> None:
    kb_root = Path(args.kb_path)
    stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    out = kb_root.parent / f"intelligence-kb-backup-{stamp}"
    shutil.copytree(kb_root, out)
    print(f"Backup created: {out}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Knowledge base operations CLI")
    parser.add_argument("--kb-path", default=str(default_kb_root()))

    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("process")
    p.add_argument("file", nargs="?")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--quality", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--dry-run", action="store_true")

    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--graph", action="store_true")
    s.add_argument("--type", dest="entity_type")
    s.add_argument("--top-k", type=int, default=10)
    s.add_argument("--min-confidence", type=float, default=0.0)
    s.add_argument("--json", action="store_true")

    g = sub.add_parser("graph")
    gsub = g.add_subparsers(dest="graph_cmd", required=True)
    gc = gsub.add_parser("connections")
    gc.add_argument("entity")
    gl = gsub.add_parser("lineage")
    gl.add_argument("model")
    gt = gsub.add_parser("talent-flow")
    gt.add_argument("--from", dest="from_lab")
    gt.add_argument("--to", dest="to_lab")
    gs = gsub.add_parser("supply-chain")
    gs.add_argument("entity")
    gk = gsub.add_parser("landscape")
    gk.add_argument("entity")
    gm = gsub.add_parser("theme-map")
    gm.add_argument("theme")
    gsub.add_parser("anomalies")
    gsub.add_parser("rebuild")

    sub.add_parser("status")
    sub.add_parser("validate")

    d = sub.add_parser("decay")
    d.add_argument("--report", action="store_true")
    d.add_argument("--apply", action="store_true")
    d.add_argument("--json", action="store_true")

    rb = sub.add_parser("rebuild")
    rb.add_argument("--full", action="store_true")

    rp = sub.add_parser("report")
    rp.add_argument("report_type", choices=["weekly", "models", "themes"])

    c = sub.add_parser("costs")
    c.add_argument("--today", action="store_true")
    c.add_argument("--month", action="store_true")

    ex = sub.add_parser("export")
    ex.add_argument("--format", choices=["json", "csv"], default="json")

    ar = sub.add_parser("archive")
    ar.add_argument("entity")

    sub.add_parser("backup")

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "process":
        args.model = "quality" if args.quality else "fast"
        cmd_process(args)
    elif args.command == "search":
        cmd_search(args)
    elif args.command == "graph":
        cmd_graph(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "validate":
        cmd_validate(args)
    elif args.command == "decay":
        if not args.report and not args.apply:
            args.report = True
        cmd_decay(args)
    elif args.command == "rebuild":
        cmd_rebuild(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "costs":
        cmd_costs(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "archive":
        cmd_archive(args)
    elif args.command == "backup":
        cmd_backup(args)


if __name__ == "__main__":
    main()
