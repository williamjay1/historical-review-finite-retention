"""Episode-locked score correction on immutable shared-tape score streams.

Importable API: lock_scores(base, corr, eligible, tau, gap) -> ndarray.
No labels enter the wrapper; labels enter only the offline metric functions.
"""
from __future__ import annotations
import argparse, csv, hashlib, itertools, json, time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from revision_decision_audit import ROOT, receipts, data_for, episodes, cooldown_starts, ids, sha, readj

OUT = ROOT / 'results/revision_notification_design_20261001/system'
GAPS = (0, 1, 3)
COOLDOWNS = (0, 3, 6)
METHODS = ('base', 'local_nn', 'constrained', 'locked_local', 'locked_constrained',
           'parent_dedup_local', 'parent_dedup_constrained')


def lock_scores(base, corr, eligible, tau, gap):
    """Causal O(T), constant-state reference; preserve the first trigger score.

    A baseline parent closes at its (gap+1)th consecutive eligible low,
    or immediately at an unusable decision. Closing is never backdated.
    Original corrected scores survive before/at the first eligible high.
    Later baseline highs in the same parent recover the baseline scalar.
    Baseline lows and unusable decisions retain the original corrected score.
    """
    base = np.asarray(base); corr = np.asarray(corr); eligible = np.asarray(eligible, bool)
    if base.ndim != 1 or base.shape != corr.shape or base.shape != eligible.shape:
        raise ValueError('base, corr and eligible must be same-length one-dimensional arrays')
    if int(gap) != gap or gap < 0:
        raise ValueError('gap must be a nonnegative integer')
    out = corr.copy(); parent = False; notified = False; silence = 0
    for t in range(len(base)):
        if not eligible[t]:
            parent = False; notified = False; silence = 0
        elif base[t] >= tau:
            if not parent:
                parent = True; notified = False
            silence = 0
            if notified:
                out[t] = base[t]
            elif corr[t] >= tau:
                notified = True
        elif parent:
            silence += 1
            if silence > gap:
                parent = False; notified = False; silence = 0
    return out


@dataclass
class LockResult:
    score: np.ndarray
    parent: np.ndarray
    trigger: np.ndarray
    task_open: np.ndarray
    restored: np.ndarray
    base_onsets: np.ndarray


def parent_state(mask, eligible, gap):
    """Causal dense parent IDs including tolerated lows, excluding closing low."""
    mask = np.asarray(mask, bool); eligible = np.asarray(eligible, bool)
    pos, ep, onsets = episodes(mask, eligible, gap)
    n = len(mask); idx = np.arange(n, dtype=np.int64)
    mark = np.zeros(n, np.int32); mark[onsets] = 1
    parent = np.cumsum(mark, dtype=np.int32) - 1
    last = np.maximum.accumulate(np.where(mask & eligible, idx, -n - 1)) if n else idx
    epoch = np.cumsum(~eligible, dtype=np.int32)
    last_clip = np.clip(last, 0, max(n - 1, 0))
    live = eligible & (last >= 0) & (idx - last <= gap)
    if n:
        live &= epoch == epoch[last_clip]
    parent[~live] = -1
    return parent, onsets


def lock_diagnostics(base, corr, eligible, tau, gap):
    """O(T) vector realization, checked against the single-pass reference.

    The decision at t uses only corrected-high counts through t and the
    count before its baseline parent started. No future label or score is
    needed by the equivalent streaming state machine.
    """
    base = np.asarray(base); corr = np.asarray(corr); eligible = np.asarray(eligible, bool)
    n = len(base); parent, onsets = parent_state(base >= tau, eligible, gap)
    ch = (corr >= tau) & eligible
    count = np.cumsum(ch, dtype=np.int64)
    before_parent = count[onsets] - ch[onsets]
    before = np.zeros(n, np.int64)
    live = parent >= 0
    before[live] = before_parent[parent[live]]
    seen_before = live & (count - ch - before > 0)
    trigger = ch & live & ~seen_before
    restore = eligible & (base >= tau) & seen_before
    score = corr.copy(); score[restore] = base[restore]
    task = live & (count - before > 0)
    return LockResult(score, parent, np.flatnonzero(trigger), task, restore, onsets)


def savej(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2, allow_nan=False), encoding='utf-8')


PLAN = '''# Episode-locked correction: implementation and analysis plan

Written after the original audit and before the present pilot/full evaluation.
This is a post-result engineering extension, not preregistration. Main scope:
270 immutable primary score streams, 18 ESA and 252 SMD, all original tapes.
No fitting, new feedback, threshold selection or annotation-based tuning.

Primary parent and notification gap is zero; gaps one/three are fixed
sensitivities. A parent begins at an eligible baseline high. Up to g lows
keep it alive; the (g+1)th eligible low closes it when observed. Unusability
resets it immediately. The first original corrected high opens its task and
retains its original score. Subsequent baseline highs recover the baseline
scalar until this parent closes; low/unusable scores retain the correction.
Every operation is prefix causal and bounded above by the baseline score.
At equal parent/notification gap, a corrected parent sends at most one
notification and total starts cannot exceed the number of base parents.
Nominal-start counts have no analogous bound because the first trigger can
move from an anomalous baseline onset to a nominal decision.

Compare base, original local, original constrained, locked-local and
locked-constrained. Also retain original scores with delivery-only parent
deduplication: its first-trigger timestamps must exactly equal the wrapper.
This separates score restoration from the notification policy contribution.
Original corrected gap-one/three rules are ordinary gap-merging controls.
For every stream/gap also apply fixed cooldown three/six to its existing
onsets, leaving scores unchanged. Report every condition, no best-gap choice.

Metrics: total and nominal starts, nominal decision-timestamp starts, flagged
nominal cycles/exposure, raw global active-before-own-feedback incident IDs,
trigger-time active-before-own IDs, actual sent-high-episode contacts, and
policy-defined parent/task-open contacts and cycles. A carried/open task is
not credited as a raw score hit or a new incident notification. Own cutoffs
and active decision opportunities come from the existing independently
verified evaluator. Report duration, opportunity and event IDs; no inferred
channel-mask recovery. ESA scalar wrapper results are global only.

Tests: exhaustive short-state streams and random numeric streams check
bitwise reference/vector agreement, prefix invariance, first-score retention,
s<=base, alarm subset and at most one trigger per parent. All real streams
repeat reference/vector and prefix tests; dedup trigger equivalence is exact.
Reproduce original base/local/constrained active hit IDs and notification
metrics against the earlier audit. Seal receipts/scores/events/reviews and
label working copies before/after, and frozen code hashes across the run.
Pilot uses one sorted ESA and one sorted SMD fit. No outcome controls scope.

Aggregation: SMD averages seeds within device/backbone then sums devices;
ESA seed means are mission/backbone descriptive summaries. Event-run counts
are not independent events. Shared tapes stay fixed; this is not a deployed
own-query loop. Any subsequent own-loop result requires separate evaluation.
No assumed operator minutes, actual workload, nominal-count theorem or
annotation-end operational deadline is claimed. Computation/output remain D.
'''


def write_plan():
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / 'ANALYSIS_PLAN.md'
    if not p.exists():
        p.write_text(PLAN, encoding='utf-8')
        savej(OUT / 'plan_receipt.json', {'created_utc': datetime.now(timezone.utc).isoformat(),
             'plan_sha256': sha(p), 'retrospective': True, 'gaps': GAPS,
             'cooldowns': COOLDOWNS, 'methods': METHODS})


def property_case(base, corr, eligible, tau, gap, prefixes=True):
    r = lock_diagnostics(base, corr, eligible, tau, gap)
    ref = lock_scores(base, corr, eligible, tau, gap)
    assert r.score.dtype == ref.dtype and r.score.tobytes() == ref.tobytes(), 'bitwise vector/reference mismatch'
    assert np.all(r.score >= corr), 'wrapper reduced the original correction'
    assert np.all(r.score <= base), 'score exceeds base'
    assert not np.any((r.score >= tau) & ~(base >= tau)), 'alarm not subset'
    assert np.array_equal(r.score[r.trigger], np.asarray(corr)[r.trigger]), 'first score changed'
    pos, ep, on = episodes(r.score >= tau, eligible, gap)
    assert np.array_equal(on, r.trigger), 'delivery-only trigger mismatch'
    if len(on):
        assert np.all(np.bincount(r.parent[on], minlength=len(r.base_onsets)) <= 1), 'parent fragmented'
    assert len(on) <= len(r.base_onsets)
    if prefixes:
        n = len(base)
        cuts = {0, min(1, n), n // 2, max(0, n - 1), n}
        if len(r.trigger):
            cuts.update([int(r.trigger[0]), min(n, int(r.trigger[0]) + 1)])
        resets = np.flatnonzero((~np.asarray(eligible, bool)) | (r.parent < 0))
        if len(resets): cuts.add(min(n, int(resets[0]) + 1))
        for cut in sorted(cuts):
            sub = lock_diagnostics(base[:cut], corr[:cut], eligible[:cut], tau, gap)
            assert np.array_equal(sub.score, r.score[:cut]), 'score prefix changed'
            assert np.array_equal(sub.parent, r.parent[:cut]), 'parent prefix changed'
            assert np.array_equal(sub.task_open, r.task_open[:cut]), 'task prefix changed'
            assert np.array_equal(sub.trigger, r.trigger[r.trigger < cut]), 'trigger prefix changed'
    return r


def self_tests():
    # 0 low, 1 suppressed baseline high, 2 retained high, 3 unusable high.
    total = 0
    for states in itertools.product(range(4), repeat=5):
        v = np.array(states)
        b = np.where(v == 0, .7, 2.).astype(np.float32)
        c = np.where((v == 2) | (v == 3), 1.2, .2).astype(np.float32)
        for g in GAPS:
            property_case(b, c, v != 3, 1., g); total += 1
    rng = np.random.default_rng(20261001)
    for _ in range(160):
        b = rng.uniform(0, 4, 257).astype(np.float32)
        c = (b * rng.uniform(0, 1, len(b))).astype(np.float32)
        eligible = rng.random(len(b)) > .04
        for g in GAPS:
            property_case(b, c, eligible, 1., g); total += 1
    # Nominal notifications can increase under the total-count bound.
    b = np.array([2., 2.], np.float32); c = np.array([.2, 1.2], np.float32)
    rr = property_case(b, c, np.ones(2, bool), 1., 0)
    assert rr.base_onsets.tolist() == [0] and rr.trigger.tolist() == [1]
    result = {'passed': True, 'test_cases': total, 'exhaustive_length': 5,
              'random_numeric_streams': 160, 'first_trigger_score_preserved': True,
              'nominal_counterexample': {'base_onset': 0, 'locked_onset': 1,
                    'offline_labels': ['anomaly', 'nominal']}}
    savej(OUT / 'property_self_tests.json', result)
    return result


def contact_count(pos, group, indices, delivered_groups):
    """Distinct sent episodes/parents with actual high decisions in indices."""
    if not len(indices) or not len(pos) or not len(delivered_groups): return 0
    hit = np.intersect1d(pos, indices, assume_unique=True)
    if not len(hit): return 0
    groups = np.unique(group[np.searchsorted(pos, hit)])
    return int(np.isin(groups, delivered_groups).sum())


def hit_at(onsets, indices):
    return bool(len(np.intersect1d(onsets, indices, assume_unique=True)))


def boolean_ids(values):
    return {key for key, val in values.items() if val}


def resolution_data(p, info):
    """Read the 56 saved stride-one streams; no fitting or tape replay."""
    folder = p.parent
    saved = pd.read_csv(folder / 'event_results.csv')
    times = np.load(folder / 'decision_samples.npy', mmap_mode='r')
    labels = np.loadtxt(Path(info['data']['working_directory']) / 'test_label.txt', dtype=np.int8)
    stride = info['stride']; width = info['width_samples']
    assert stride == 1 and width == 10 and info['seed'] == 0
    assert np.array_equal(times, 9 + np.arange(len(times)) * stride)
    cumulative = np.r_[0, np.cumsum(labels != 0)]
    feature_pure = cumulative[times + 1] == cumulative[times - width + 1]
    decision_pure = cumulative[times + 1] == cumulative[times - stride + 1]
    ev = {}
    for _, r in saved[saved.method == 'base'].iterrows():
        ident = str(int(r.event_id)); a = int(r.start_sample); z = int(r.end_sample_exclusive)
        ix = np.flatnonzero((times - width + 1 < z) & (times >= a))
        act = np.flatnonzero((times >= a) & (times < z))
        cutoff = int(r.own_feedback_effective_decision_sample) if not pd.isna(r.own_feedback_effective_decision_sample) else len(labels) + width
        activepre = act[times[act] < cutoff]
        ev[ident] = dict(category='anomaly', idx=ix, pre=ix[times[ix] < cutoff], active=act,
            activepre=activepre, affected=[], repeated_rare=False, cutoff=cutoff,
            opportunity=bool(len(activepre)), affected_opportunity=None)
    return dict(tau=info['model']['threshold'], eligible=np.ones(len(times), bool),
        valid=np.ones(len(times), bool), nominal=feature_pure, nominal_feature_support=feature_pure,
        nominal_decision_bin=decision_pure, nominal_decision=labels[times] == 0, events=ev,
        saved=saved, unit=info['entity'], backbone=info['backbone'], seed=0, duration=stride,
        decision_coordinates=times)


def resolution_receipts():
    selected = []
    for p in sorted((ROOT / 'results/revision_20261001/resolution/runs').glob('*/*_stride1/complete.json')):
        original = readj(p)
        assert original['kind'] in ('pca', 'ridge') and original['seed'] == 0
        info = dict(original); info['data'] = dict(original['data'])
        info['data']['working_directory'] = original['data']['source']
        info['backbone'] = original['kind']; info['methods'] = pd.read_csv(p.parent / 'metrics.csv').method.tolist()
        info['_resolution'] = True
        selected.append(('SMD', p, info))
    assert len(selected) == 56 and len({x[2]['entity'] for x in selected}) == 28
    return selected


def evaluate_run(suite, p, info, metric_writer, event_writer, dest, old_lookup):
    d = resolution_data(p, info) if info.get('_resolution') else data_for(suite, p, info)
    folder = p.parent
    scores = np.load(folder / 'scores.npy', mmap_mode='r')
    assert len(scores) == len(d['eligible'])
    indices = {m: info['methods'].index(m) for m in ('base', 'local_nn', 'constrained')}
    raw = {m: np.asarray(scores[:, k]) for m, k in indices.items()}
    base = raw['base']; tau = d['tau']; eligible = d['eligible']; nominal = d['nominal']
    assert all(np.all(x <= base) and np.isfinite(x).all() for x in raw.values())
    originals = [p, folder / 'scores.npy', folder / 'event_results.csv', folder / 'reviews.json']
    if suite == 'SMD': originals += [Path(info['data']['working_directory']) / 'test_label.txt']
    else: originals += [folder / 'channel_alarms.npy', d['qpath']]
    seals = {str(f.relative_to(ROOT)): sha(f) for f in originals}
    run_name = f"{info['entity']}_{folder.name}" if info.get('_resolution') else folder.name
    shared = dict(dataset=suite, run=run_name, unit=d['unit'], backbone=d['backbone'], seed=d['seed'])
    event_meta = {}
    if suite == 'ESA':
        a = info['arguments']; prep = ROOT / f"datasets/m{a['mission']}_{a['subset']}_b{a['block']}"
        event_meta = {e['id']: e for e in readj(prep / 'events.json')}
    else:
        event_meta = {str(int(r.event_id)): r._asdict() for r in d['saved'][d['saved'].method == 'base'].itertuples()}
    active_ids = {}; anomalies = {i: e for i, e in d['events'].items() if e['category'] == 'anomaly'}
    for m in raw:
        active_ids[m] = {i for i, e in anomalies.items() if np.any(raw[m][e['activepre']] >= tau)}
        if info.get('_resolution'):
            original_rows = d['saved'][d['saved'].method == m]
            original_ids = {str(int(r.event_id)) for r in original_rows.itertuples()
                if str(r.active_event_detected_before_own_feedback).lower() == 'true'}
            assert active_ids[m] == original_ids, (run_name, m, 'saved fine active IDs')
            original_metrics = pd.read_csv(folder / 'metrics.csv').set_index('method').loc[m]
            assert np.isclose(int(np.sum((raw[m] >= tau) & nominal)),
                original_metrics.feature_pure_nominal_flagged_fraction * original_metrics.feature_pure_nominal_decisions, atol=1e-6)
        else:
            prior = old_lookup[(suite, folder.name, m)]
            assert active_ids[m] == set(json.loads(prior['active_before_own_hit_ids'])), (folder.name, m, 'original active IDs')
            assert int(np.sum((raw[m] >= tau) & nominal)) == int(prior['nominal_flagged_cycles'])
    archive = {}; metric_rows = []; property_runs = 0
    for g in GAPS:
        locks = {}
        for m in ('local_nn', 'constrained'):
            locks[m] = property_case(base, raw[m], eligible, tau, g)
            property_runs += 1
            archive[f'{m}_locked_score_g{g}'] = locks[m].score
        parent, base_onsets = parent_state(base >= tau, eligible, g)
        curves = {**raw, 'locked_local': locks['local_nn'].score,
                  'locked_constrained': locks['constrained'].score,
                  'parent_dedup_local': raw['local_nn'], 'parent_dedup_constrained': raw['constrained']}
        for m in METHODS:
            x = curves[m]; mask = (x >= tau) & eligible
            pos, ep, standard_on = episodes(mask, eligible, g)
            is_parent = m.startswith('locked_') or m.startswith('parent_dedup_')
            source = 'local_nn' if m.endswith('local') else 'constrained'
            if is_parent:
                intrinsic = locks[source].trigger
                group = parent[pos]
                assert np.all(group >= 0)
                task_parent = parent
            else:
                intrinsic = standard_on; group = ep
                task_parent, _ = parent_state(mask, eligible, g)
            if m.startswith('locked_'): assert np.array_equal(intrinsic, standard_on)
            archive[f'{m}_onsets_g{g}'] = intrinsic
            raw_hits = {i: bool(mask[e['activepre']].any()) for i, e in anomalies.items()}
            raw_hit_ids = boolean_ids(raw_hits)
            for cooldown in COOLDOWNS:
                on = intrinsic if cooldown == 0 else cooldown_starts(intrinsic, cooldown)
                delivered = task_parent[on]
                # Lifetime starts at a retained notification, never at its parent onset.
                start_at_group = np.full(len(base_onsets) if is_parent else len(standard_on), len(base), np.int64)
                start_at_group[delivered] = on
                live = task_parent >= 0; opened = np.zeros(len(base), bool)
                opened[live] = np.arange(len(base))[live] >= start_at_group[task_parent[live]]
                trig_ids = {i for i, e in anomalies.items() if hit_at(on, e['activepre'])}
                contacts = {}; tasks = {}; event_rows = []
                for ident, e in d['events'].items():
                    ai = e['activepre']; pre = e['pre']; rmeta = event_meta[ident]
                    act_hit = bool(mask[ai].any()); trigger_hit = hit_at(on, ai)
                    actual_contact = contact_count(pos, group, ai, delivered)
                    recognition_contact = contact_count(pos, group, pre, delivered)
                    task_contact = bool(opened[ai].any())
                    if e['category'] == 'anomaly':
                        contacts[ident] = actual_contact > 0; tasks[ident] = task_contact
                    if suite == 'ESA':
                        duration = sum(b - a for a, b in rmeta['intervals']) / (d['duration'] * 1e9)
                        annotation_components = len(rmeta['intervals'])
                    else:
                        duration = (int(rmeta['end_sample_exclusive']) - int(rmeta['start_sample'])) / d['duration']
                        annotation_components = 1
                    event_rows.append(dict(**shared, method=m, parent_gap=g, notification_gap=g,
                        cooldown_cycles=cooldown, incident_id=ident, category=e['category'], later_rare=e['repeated_rare'],
                        duration_original_cycles=duration, annotation_components=annotation_components,
                        own_feedback_cutoff_original_coordinate=e['cutoff'], active_decision_opportunities=len(ai),
                        active_opportunity=bool(len(ai)), raw_active_before_own_hit=act_hit,
                        trigger_active_before_own_hit=trigger_hit, sent_high_episode_active_contacts=actual_contact,
                        sent_high_episode_preown_recognition_contacts=recognition_contact,
                        sent_preown_recognition_starts=int(len(np.intersect1d(on, pre, assume_unique=True))),
                        sent_active_preown_starts=int(len(np.intersect1d(on, ai, assume_unique=True))),
                        policy_task_open_active_contact=task_contact,
                        base_raw_active_hit=ident in active_ids['base']))
                row = dict(**shared, method=m, parent_gap=g, notification_gap=g, cooldown_cycles=cooldown,
                    total_notifications=len(on), nominal_notifications=int(nominal[on].sum()),
                    nominal_decision_notifications=int(d['nominal_decision'][on].sum()),
                    flagged_cycles=int(mask.sum()), nominal_flagged_cycles=int((mask & nominal).sum()),
                    nominal_flagged_exposure_original_coordinate=float((mask & nominal).sum() * d['duration']),
                    policy_task_open_cycles=int(opened.sum()), policy_nominal_task_open_cycles=int((opened & nominal).sum()),
                    incident_opportunities=sum(e['opportunity'] for e in anomalies.values()),
                    raw_active_before_own_hits=len(raw_hit_ids), raw_active_before_own_hit_ids=ids(raw_hit_ids),
                    trigger_active_before_own_hits=len(trig_ids), trigger_active_before_own_hit_ids=ids(trig_ids),
                    sent_high_episode_active_contact_ids=ids(boolean_ids(contacts)),
                    policy_task_open_active_contact_ids=ids(boolean_ids(tasks)),
                    base_parent_episodes=len(base_onsets), max_notifications_per_base_parent=int(np.bincount(parent[on], minlength=len(base_onsets)).max()) if len(on) else 0,
                    raw_new_base_loss_ids=ids(active_ids['base'] - raw_hit_ids),
                    raw_recovered_local_loss_ids=ids((active_ids['base'] - active_ids['local_nn']) & raw_hit_ids),
                    shared_requested_reviews=int(info['requested_reviews']) if m != 'base' else 0,
                    channel_evidence_evaluated=False, shared_tape_unchanged=True)
                if info.get('_resolution'):
                    for definition, nominal_mask in [('feature_support', d['nominal_feature_support']),
                            ('decision_bin', d['nominal_decision_bin']), ('current_decision', d['nominal_decision'])]:
                        row[f'nominal_{definition}_notifications'] = int(nominal_mask[on].sum())
                        row[f'nominal_{definition}_flagged_cycles'] = int((mask & nominal_mask).sum())
                        row[f'nominal_{definition}_flagged_exposure_samples'] = int((mask & nominal_mask).sum() * d['duration'])
                    row['decision_stride_samples'] = info['stride']
                    row['feature_support_samples'] = info['width_samples']
                    row['legacy_nominal_definition'] = 'ten-sample-feature-support-pure'
                if is_parent: assert row['max_notifications_per_base_parent'] <= 1
                if m in raw and cooldown == 0 and not info.get('_resolution'):
                    prior = old_lookup[(suite, folder.name, m)]
                    assert row['total_notifications'] == int(prior[f'all_notifications_gap{g}'])
                    assert row['nominal_notifications'] == int(prior[f'nominal_notifications_gap{g}'])
                row['_trig'] = trig_ids; row['_events'] = event_rows
                metric_rows.append(row)
        # Exact delivery-only equivalence holds even after the same cooldown.
        for a, b in [('locked_local', 'parent_dedup_local'), ('locked_constrained', 'parent_dedup_constrained')]:
            assert np.array_equal(archive[f'{a}_onsets_g{g}'], archive[f'{b}_onsets_g{g}'])
    keyed = {(r['method'], r['parent_gap'], r['cooldown_cycles']): r for r in metric_rows}
    for row in metric_rows:
        g = row['parent_gap']; c = row['cooldown_cycles']; bm = keyed[('base', g, c)]
        row['new_base_trigger_loss_ids'] = ids(bm['_trig'] - row['_trig'])
        row['new_base_trigger_gain_ids'] = ids(row['_trig'] - bm['_trig'])
        row['new_base_raw_loss_count'] = len(json.loads(row['raw_new_base_loss_ids']))
        row['new_base_trigger_loss_count'] = len(bm['_trig'] - row['_trig'])
        row['new_base_trigger_gain_count'] = len(row['_trig'] - bm['_trig'])
        row['nominal_notifications_saved_vs_base'] = bm['nominal_notifications'] - row['nominal_notifications']
        row['total_notifications_saved_vs_base'] = bm['total_notifications'] - row['total_notifications']
        if row['method'] in ('locked_local', 'locked_constrained'):
            original = 'local_nn' if row['method'] == 'locked_local' else 'constrained'
            rm = keyed[(original, g, c)]
            row['original_correction_method'] = original
            row['nominal_notifications_saved_vs_original'] = rm['nominal_notifications'] - row['nominal_notifications']
            row['total_notifications_saved_vs_original'] = rm['total_notifications'] - row['total_notifications']
            row['nominal_flagged_cycles_restored_vs_original'] = row['nominal_flagged_cycles'] - rm['nominal_flagged_cycles']
            row['raw_active_hits_restored_vs_original'] = row['raw_active_before_own_hits'] - rm['raw_active_before_own_hits']
            row['trigger_active_hit_ids_gained_vs_original'] = ids(row['_trig'] - rm['_trig'])
            row['trigger_active_hit_ids_lost_vs_original'] = ids(rm['_trig'] - row['_trig'])
        else:
            row.update(original_correction_method='', nominal_notifications_saved_vs_original='',
                total_notifications_saved_vs_original='', nominal_flagged_cycles_restored_vs_original='',
                raw_active_hits_restored_vs_original='', trigger_active_hit_ids_gained_vs_original='',
                trigger_active_hit_ids_lost_vs_original='')
    # Keep private comparison sets intact until all paired rows are derived.
    for row in metric_rows:
        events = row.pop('_events'); row.pop('_trig')
        if metric_writer['writer'] is None:
            metric_writer['writer'] = csv.DictWriter(metric_writer['file'], fieldnames=list(row)); metric_writer['writer'].writeheader()
        metric_writer['writer'].writerow(row)
        for e in events:
            if event_writer['writer'] is None:
                event_writer['writer'] = csv.DictWriter(event_writer['file'], fieldnames=list(e)); event_writer['writer'].writeheader()
            event_writer['writer'].writerow(e)
    stream_dir = dest / 'streams'; stream_dir.mkdir(exist_ok=True)
    if info.get('_resolution'): archive['decision_samples'] = d['decision_coordinates']
    np.savez_compressed(stream_dir / (run_name + '.npz'), **archive)
    assert all(sha(ROOT / f) == seal for f, seal in seals.items()), 'original input changed'
    return dict(**shared, metric_rows=len(metric_rows), event_rows=sum(len(d['events']) for _ in metric_rows),
                real_stream_property_checks=property_runs, original_seals=seals, passed=True)


def summarize(dest):
    frame = pd.read_csv(dest / 'run_metrics.csv')
    numeric = ['total_notifications', 'nominal_notifications', 'flagged_cycles', 'nominal_flagged_cycles',
        'raw_active_before_own_hits', 'trigger_active_before_own_hits', 'new_base_raw_loss_count',
        'new_base_trigger_loss_count', 'new_base_trigger_gain_count', 'nominal_notifications_saved_vs_base',
        'total_notifications_saved_vs_base', 'policy_task_open_cycles', 'policy_nominal_task_open_cycles']
    keys = ['dataset', 'unit', 'backbone', 'method', 'parent_gap', 'cooldown_cycles']
    seed = frame.groupby(keys, as_index=False)[numeric].mean()
    seed.to_csv(dest / 'seed_collapsed_by_unit.csv', index=False)
    out = []
    for (dataset, backbone, method, gap, cd), part in seed.groupby(['dataset', 'backbone', 'method', 'parent_gap', 'cooldown_cycles']):
        if dataset == 'ESA':
            for _, row in part.iterrows(): out.append(row.to_dict())
        else:
            out.append(dict(dataset=dataset, unit=f'all{part.unit.nunique()}devices', backbone=backbone, method=method,
                parent_gap=int(gap), cooldown_cycles=int(cd), **{n:float(part[n].sum()) for n in numeric}))
    agg = pd.DataFrame(out); agg.to_csv(dest / 'aggregate_summary.csv', index=False)
    primary = frame[(frame.parent_gap == 0) & (frame.cooldown_cycles == 0)]
    lines = ['# Episode-locked correction: retrospective shared-tape results', '',
        f'All {frame.run.nunique()} saved score streams passed causal prefix, reference equivalence, score-bound, alarm-subset and parent notification tests. The score and tape inputs remained unchanged.', '',
        'An episode lock and delivery-only parent deduplication have exactly equal notification trigger timestamps at every evaluated gap and cooldown. They therefore have equal total and nominal notification counts and trigger-time incident evidence. Their score-level and sent-high contact evidence can differ. Score restoration must not be presented as a new incident notification or as a new learned detector.', '',
        '| Dataset / backbone | Variant | Total notification savings vs base | Nominal savings vs base | Newly lost raw active records | Newly lost baseline timely trigger records |',
        '|---|---|---:|---:|---:|---:|']
    for _, x in agg[(agg.parent_gap == 0) & (agg.cooldown_cycles == 0) & agg.method.isin(['local_nn','constrained','locked_local','locked_constrained'])].iterrows():
        lines.append(f"| {x.dataset} {x.unit} / {x.backbone} | {x.method} | {x.total_notifications_saved_vs_base:.3f} | {x.nominal_notifications_saved_vs_base:.3f} | {x.new_base_raw_loss_count:.3f} | {x.new_base_trigger_loss_count:.3f} |")
    smd_scope = frame[frame.dataset == 'SMD'][['run', 'unit', 'seed']].drop_duplicates()
    lines += ['', f'SMD counts average the available paired seeds within each device and sum {smd_scope.unit.nunique()} devices ({smd_scope.run.nunique()} fitted streams); ESA rows are seed means within mission/backbone. These are descriptive repeated-fit summaries, not independent-event estimates. All retained and withdrawn incident IDs are in run_metrics.csv and event_metrics.csv.', '',
        'The total-notification bound follows only for a wrapper using the same gap as its baseline parent state, and compares it with the raw number of baseline parents. It need not hold against an independently cool-downed baseline, because triggers can shift. No nominal-notification bound is asserted: a delayed first trigger can change the offline nominal label. All same-score ordinary gap-merging and fixed cooldown 3/6 comparators are retained. Policy task-open exposure and carried contacts are separate from score hits and timely notification starts.', '',
        'This experiment conditions on the common saved shadow-feedback tape. It does not establish outcomes for a deployed corrected-score query loop. The scalar restoration does not reconstruct or claim affected-channel evidence. All choices were fixed before this replay after the prior audit; no deployment optimum or measured operator-time reduction is claimed.']
    (dest / 'ENGLISH_RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--pilot', action='store_true'); ap.add_argument('--self-test', action='store_true'); ap.add_argument('--fine', action='store_true')
    args = ap.parse_args(); write_plan(); tests = self_tests()
    if args.self_test: print(json.dumps(tests), flush=True); return
    selected = resolution_receipts() if args.fine else receipts()
    if args.fine:
        savej(OUT / 'FINE_ANALYSIS_PLAN.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
            scope='all 56 saved stride-one PCA/Ridge seed-zero streams; no training or score replay',
            retrospective=True, methods=METHODS, gaps=GAPS, cooldowns=COOLDOWNS,
            clocks='original physical decision_samples.npy, event own cutoffs from corresponding saved event rows',
            legacy_nominal_definition='all 10 feature-support samples normal',
            decision_bin_nominal='all stride samples through current timestamp normal; stride one is current sample',
            current_decision_nominal='current timestamp label is zero',
            cross_cadence_bins_not_equated=True))
    if args.pilot: selected = selected[:2] if args.fine else [next(x for x in selected if x[0] == ds) for ds in ('ESA', 'SMD')]
    dest = OUT / ('fine_pilot' if args.fine and args.pilot else 'fine56' if args.fine else 'pilot' if args.pilot else 'full'); dest.mkdir(parents=True, exist_ok=True)
    frozen = {str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'scripts/correction.py',ROOT/'scripts/experiment.py',ROOT/'scripts/revision_decision_audit.py']}
    prior = pd.read_csv(ROOT/'results/revision_20261001/decision_audit/full/run_metrics.csv', dtype={'run':str})
    old = {(r['dataset'],r['run'],r['method']):r for r in prior.to_dict('records')}
    start = time.perf_counter(); results = []
    try:
        with (dest/'run_metrics.csv').open('w', encoding='utf-8', newline='') as mf, (dest/'event_metrics.csv').open('w', encoding='utf-8', newline='') as ef:
            mw={'file':mf,'writer':None}; ew={'file':ef,'writer':None}
            for suite,p,j in selected:
                result = evaluate_run(suite,p,j,mw,ew,dest,old); results.append(result)
                print('DONE',len(results),len(selected),suite,result['run'],round(time.perf_counter()-start,2),flush=True)
        assert all(sha(ROOT/f)==h for f,h in frozen.items())
        summarize(dest)
        savej(dest/'validation.json',dict(passed=True, complete=len(results)==len(selected),
            runs=len(results), scope={'ESA':sum(x['dataset']=='ESA' for x in results),'SMD':sum(x['dataset']=='SMD' for x in results)},
            seconds=time.perf_counter()-start, property_self_tests=tests,
            method_names=METHODS,gaps=GAPS,cooldowns=COOLDOWNS,
            analysis_script_sha256=sha(Path(__file__)),frozen_code_seals=frozen,
            run_validations=results,review_tape_unchanged=True,channel_recovery_not_inferred=True,
            delivery_only_trigger_equivalence=True,retrospective=True,fine_resolution=args.fine))
        print('COMPLETE',dest,round(time.perf_counter()-start,2),flush=True)
    except Exception as exc:
        savej(dest/'FAILURE.json',{'exception':repr(exc),'completed_runs':len(results),'seconds':time.perf_counter()-start,'scope_not_silently_changed':True})
        raise


if __name__ == '__main__': main()
