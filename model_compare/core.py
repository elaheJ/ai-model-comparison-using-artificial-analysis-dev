"""Notebook Q1–Q10, plus transparent ranking and comparison helpers.

The original cost/latency behavior is retained; ranking adds other metrics and
weighted min–max utility. This module has no third-party dependencies.
"""
from copy import deepcopy
import math

# field: (label, higher is better)
METRICS = {
    "quality": ("Intelligence index", True),
    "cost_usd": ("Workload cost ($)", False),
    "ttft_s": ("Time to first token (s)", False),
    "first_answer_s": ("Time to first answer (s)", False),
    "end_to_end_s": ("End-to-end response (s)", False),
    "output_tokens_s": ("Output speed (tokens/s)", True),
    "input_price": ("Input price ($/1M tokens)", False),
    "output_price": ("Output price ($/1M tokens)", False),
}
MAX_TOOL_CALLS = 4


def has_measurement(value):  # Q1
    """Accept finite numbers, including zero, but never bool or missing values."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def read_metric(model, section, key):  # Q2
    """Read a nested field, including when an entire section is null."""
    group = model.get(section)
    return group.get(key) if isinstance(group, dict) else None


def models_for_slugs(models, slugs):  # Q3
    return [model for model in models if model["slug"] in slugs]


def _tokens(value):
    return type(value) is int and 0 <= value <= 10**15


def workload_cost(input_tokens, output_tokens, input_price, output_price):  # Q4
    if not _tokens(input_tokens) or not _tokens(output_tokens):
        raise ValueError("Token volumes must be nonnegative integers, at most 10^15.")
    if input_price is None or output_price is None:
        return None
    if not all(has_measurement(p) and 0 <= p <= 10**15 for p in (input_price, output_price)):
        raise ValueError("Prices must be finite, nonnegative numbers, at most 10^15.")
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000


def meets_limits(row, min_quality, max_ttft, max_cost):  # Q5
    if not all(has_measurement(row.get(k)) for k in ("quality", "ttft_s", "cost_usd")):
        return False
    return row["quality"] >= min_quality and row["ttft_s"] <= max_ttft and row["cost_usd"] <= max_cost


def choose_model(rows, objective):  # Q6; notebook-compatible entry point
    if objective not in ("cost", "latency"):
        raise ValueError("Objective must be cost or latency.")
    field = "cost_usd" if objective == "cost" else "ttft_s"
    return min(rows, key=lambda row: (row[field], row["slug"])) if rows else None


def _compare_args(args):
    required = {"slugs", "input_tokens", "output_tokens", "min_quality", "max_ttft", "max_cost", "objective"}
    if not required <= set(args) or set(args) - required - {"weights", "extra_limits"}:
        return False
    slugs = args["slugs"]
    if not (isinstance(slugs, list) and 1 <= len(slugs) <= 1000
            and all(isinstance(s, str) and bool(s.strip()) for s in slugs)
            and len(set(slugs)) == len(slugs)):
        return False
    if not all(_tokens(args[k]) for k in ("input_tokens", "output_tokens")):
        return False
    if not all(has_measurement(args[k]) and 0 <= args[k] <= 10**15 for k in ("min_quality", "max_ttft", "max_cost")):
        return False
    objective = args["objective"]
    if not isinstance(objective, str) or objective not in {*METRICS, "cost", "latency", "composite"}:
        return False
    weights = args.get("weights", {})
    if not isinstance(weights, dict) or not set(weights) <= set(METRICS):
        return False
    if not all(has_measurement(w) and 0 <= w <= 100 for w in weights.values()):
        return False
    if objective == "composite" and not sum(weights.values()):
        return False
    limits = args.get("extra_limits", {})
    return (isinstance(limits, dict) and set(limits) <= {"first_answer_s", "end_to_end_s"}
            and all(has_measurement(v) and 0 <= v <= 10**15 for v in limits.values()))


def _cost_args(args):
    return (set(args) == {"slug", "input_tokens", "output_tokens"}
            and isinstance(args["slug"], str) and bool(args["slug"].strip())
            and _tokens(args["input_tokens"]) and _tokens(args["output_tokens"]))


TOOL_RULES = {"fetch_metrics": lambda args: args == {}, "compare_models": _compare_args,
              "estimate_cost": _cost_args}


def valid_tool_call(name, args):  # Q7
    return (isinstance(name, str) and name in TOOL_RULES and isinstance(args, dict)
            and TOOL_RULES[name](args))


def can_continue(call_count, finished, max_calls=4):  # Q8
    return not finished and call_count < max_calls


def record_trace(trace, tool_name, arguments, observation):  # Q9
    # Deep copy also protects nested lists/weights and the observation itself.
    return trace + [deepcopy({"tool": tool_name, "arguments": arguments, "observation": observation})]


def check_recommendation(recommendation, approved_slug):  # Q10
    if not isinstance(recommendation, dict) or set(recommendation) != {"status", "slug", "reason"}:
        return False
    if not isinstance(recommendation["reason"], str) or not recommendation["reason"].strip():
        return False
    return (recommendation["status"] == ("no_feasible_model" if approved_slug is None else "selected")
            and recommendation["slug"] == approved_slug)


def comparison_rows(snapshot, slugs, input_tokens, output_tokens):
    selected = models_for_slugs(snapshot["models"], slugs)
    if {m["slug"] for m in selected} != set(slugs):
        raise ValueError("A requested model ID is absent from this snapshot.")
    result = []
    for model in selected:
        pricing = [read_metric(model, "pricing", k) for k in ("price_1m_input_tokens", "price_1m_output_tokens")]
        creator = model.get("model_creator") or {}
        row = {"slug": model["slug"], "name": model.get("name", model["slug"]),
               "creator": creator.get("name", "Unknown") if isinstance(creator, dict) else str(creator),
               "quality": read_metric(model, "evaluations", "artificial_analysis_intelligence_index"),
               "input_price": pricing[0], "output_price": pricing[1],
               "cost_usd": workload_cost(input_tokens, output_tokens, *pricing)}
        for field, key in {
            "ttft_s": "median_time_to_first_token_seconds",
            "first_answer_s": "median_time_to_first_answer_token_seconds",
            "end_to_end_s": "median_end_to_end_response_time_seconds",
            "output_tokens_s": "median_output_tokens_per_second",
        }.items():
            row[field] = read_metric(model, "performance", key)
        result.append(row)
    return result


def exclusion_reasons(row, task):
    reasons = []
    for field, limit, higher in [("quality", task["min_quality"], True),
                                 ("ttft_s", task["max_ttft"], False),
                                 ("cost_usd", task["max_cost"], False)]:
        value = row.get(field)
        if not has_measurement(value):
            reasons.append(f"Missing {METRICS[field][0]}")
        elif (value < limit if higher else value > limit):
            reasons.append(f"{METRICS[field][0]} fails limit {limit:g}")
    for field, limit in task.get("extra_limits", {}).items():
        if not has_measurement(row.get(field)) or row[field] > limit:
            reasons.append(f"{METRICS[field][0]} missing or exceeds {limit:g}")
    return reasons


def rank_models(rows, objective, weights=None):
    """Score only complete eligible candidates; return ranking and bounds.

    Min–max utility is in [0,1]. Lower-is-better metrics are inverted.
    Constant columns receive 1 (a tie). Zero-weight metrics are ignored.
    """
    field = {"cost": "cost_usd", "latency": "ttft_s"}.get(objective, objective)
    active = {k: v for k, v in (weights or {}).items() if v > 0} if objective == "composite" else {field: 1}
    eligible = [r for r in rows if all(has_measurement(r.get(k)) for k in active)]
    bounds = {k: [min(r[k] for r in eligible), max(r[k] for r in eligible)] for k in active} if eligible else {}
    scored = []
    for row in eligible:
        components = {}
        for key, weight in active.items():
            low, high = bounds[key]
            utility = 1.0 if high == low else (row[key] - low) / (high - low)
            if high != low and not METRICS[key][1]:
                utility = 1 - utility
            components[key] = 100 * weight / sum(active.values()) * utility
        scored.append({**row, "score": sum(components.values()), "contributions": components})
    # For a single metric, order by its original value to preserve full precision.
    key = ((lambda r: (-r["score"], r["slug"])) if objective == "composite" else
           (lambda r: ((-1 if METRICS[field][1] else 1) * r[field], r["slug"])))
    return sorted(scored, key=key), bounds


def compare_models(snapshot, **task):
    if not valid_tool_call("compare_models", task):
        raise ValueError("Invalid comparison: select candidates, valid limits, and a positive composite weight.")
    rows = comparison_rows(snapshot, task["slugs"], task["input_tokens"], task["output_tokens"])
    active = ([k for k, w in task.get("weights", {}).items() if w > 0] if task["objective"] == "composite"
              else [{"cost": "cost_usd", "latency": "ttft_s"}.get(task["objective"], task["objective"])])
    for row in rows:
        row["exclusions"] = exclusion_reasons(row, task)
        for metric in active:
            if not has_measurement(row.get(metric)) and f"Missing {METRICS[metric][0]}" not in row["exclusions"]:
                row["exclusions"].append(f"Missing {METRICS[metric][0]}")
        row["eligible"] = meets_limits(row, task["min_quality"], task["max_ttft"], task["max_cost"]) and not row["exclusions"]
    ranked, bounds = rank_models([r for r in rows if r["eligible"]], task["objective"], task.get("weights"))
    # Use Q6 for the two original objectives; the ranking agrees by construction.
    winner = (choose_model(ranked, task["objective"]) if task["objective"] in ("cost", "latency")
              else ranked[0] if ranked else None)
    return {**{k: snapshot.get(k) for k in ("source", "retrieved_at", "intelligence_index_version", "snapshot_id", "is_demo")},
            "constraints": deepcopy(task), "candidates": rows, "ranking": ranked,
            "feasible_slugs": [r["slug"] for r in ranked], "normalization_bounds": bounds, "winner": winner}


def estimate_cost(snapshot, slug, input_tokens, output_tokens):
    args = {"slug": slug, "input_tokens": input_tokens, "output_tokens": output_tokens}
    if not valid_tool_call("estimate_cost", args):
        raise ValueError("Invalid cost arguments.")
    row = comparison_rows(snapshot, [slug], input_tokens, output_tokens)[0]
    return {**args, "cost_usd": row["cost_usd"]}


def fixed_workflow(snapshot, task):
    trace = record_trace([], "fetch_metrics", {}, {k: snapshot.get(k) for k in ("source", "retrieved_at", "snapshot_id")})
    comparison = compare_models(snapshot, **task)
    trace = record_trace(trace, "compare_models", task, comparison)
    winner = comparison["winner"]
    if winner is not None:
        args = {"slug": winner["slug"], "input_tokens": task["input_tokens"], "output_tokens": task["output_tokens"]}
        trace = record_trace(trace, "estimate_cost", args, estimate_cost(snapshot, **args))
    return {"winner": winner, "comparison": comparison, "trace": trace, "tool_calls": len(trace)}


def pareto_front(rows, fields=("quality", "cost_usd", "ttft_s")):
    """IDs not dominated by another complete row on all selected metrics."""
    complete = [r for r in rows if all(has_measurement(r.get(k)) for k in fields)]
    def dominates(a, b):
        differences = [(a[k] - b[k]) * (1 if METRICS[k][1] else -1) for k in fields]
        return all(d >= 0 for d in differences) and any(d > 0 for d in differences)
    return [r["slug"] for r in complete if not any(dominates(other, r) for other in complete)]


def find_similar_models(rows, slug, features, min_similarity=0):
    """All comparable neighbors, using equal-weight range-normalized RMS distance.

    A score measures closeness, not superiority. Bounds use every known value
    in the supplied catalog, independently per feature. Missing selected fields
    exclude a candidate; a missing reference field is an actionable error.
    """
    if isinstance(features, str):
        features = [features]
    if (not isinstance(features, (list, tuple)) or not features
            or any(not isinstance(f, str) or f not in METRICS for f in features)
            or len(set(features)) != len(features)):
        raise ValueError("Choose one or more distinct similarity features.")
    if not has_measurement(min_similarity) or not 0 <= min_similarity <= 100:
        raise ValueError("Minimum similarity must be between 0 and 100.")
    target = next((r for r in rows if r["slug"] == slug), None)
    if target is None:
        raise ValueError("The reference model is absent from this snapshot.")
    missing = [METRICS[f][0] for f in features if not has_measurement(target.get(f))]
    if missing:
        raise ValueError("Reference model is missing: " + ", ".join(missing) + ". Choose other features or another model.")
    bounds = {f: [min(r[f] for r in rows if has_measurement(r.get(f))),
                  max(r[f] for r in rows if has_measurement(r.get(f)))] for f in features}
    matches, excluded, below_threshold = [], [], 0
    for row in rows:
        if row["slug"] == slug:
            continue
        missing = [f for f in features if not has_measurement(row.get(f))]
        if missing:
            excluded.append({"slug": row["slug"], "missing_features": missing})
            continue
        differences = {f: row[f] - target[f] for f in features}
        distances = {f: abs(differences[f]) / (bounds[f][1] - bounds[f][0])
                     if bounds[f][1] != bounds[f][0] else 0.0 for f in features}
        distance = math.sqrt(sum(d*d for d in distances.values()) / len(features))
        similarity = max(0.0, min(100.0, 100 * (1 - distance)))
        if similarity < min_similarity:
            below_threshold += 1
            continue
        matches.append({**row, "similarity_pct": similarity, "distance": distance,
                        "differences": differences, "normalized_differences": distances})
    matches.sort(key=lambda row: (row["distance"], row["slug"]))
    return {"reference": deepcopy(target), "features": list(features), "min_similarity": min_similarity,
            "normalization_bounds": bounds, "matches": matches, "excluded": excluded,
            "below_threshold": below_threshold,
            "method": "Equal-weight RMS of absolute differences divided by snapshot feature ranges; similarity = 100 * (1 - distance)."}


def similar_models(rows, slug, field, k=None):
    """Convenience wrapper: one field or a list, all matches unless k is supplied."""
    return find_similar_models(rows, slug, field)["matches"][:k]


def check_numeric_evidence(claims, row):
    expected = {k: row.get(k) for k in ("quality", "cost_usd", "ttft_s", "score")}
    return (isinstance(claims, dict) and set(claims) == set(expected)
            and all(has_measurement(claims[k]) and has_measurement(v)
                    and math.isclose(claims[k], v, rel_tol=1e-6, abs_tol=1e-8) for k, v in expected.items()))
