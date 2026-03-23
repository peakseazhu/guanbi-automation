# Publish Validation Branch Promotion Sweep Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Determine whether any remaining `publish-stage-task1` changes should be selectively promoted into `main`, and if so, promote only evidence-backed foundation changes.

**Architecture:** Review `main..publish-stage-task1` as three buckets: branch-only live verification assets, historical/doc divergence, and potential foundation-grade runtime changes. Keep live verification scaffolding on the validation branch unless a change is proven necessary by real evidence, independent of machine-private resources, and able to pass fresh verification on `main`.

**Tech Stack:** Git worktrees, Python, pytest, Markdown session archives

---

### Task 1: Build a promotion candidate inventory

**Files:**
- Modify: `docs/plans/2026-03-23-validation-branch-promotion-sweep-plan.md`
- Read: `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-design.md`
- Read: `.worktrees/publish-stage-task1/docs/plans/2026-03-22-publish-live-verification-implementation-plan.md`
- Read: `.worktrees/publish-stage-task1/docs/archive/sessions/2026-03-22-publish-live-verification-implementation.md`
- Read: `docs/archive/sessions/2026-03-23-publish-live-verification-promotion.md`

**Step 1: Enumerate branch delta**

Run: `git diff --stat main..publish-stage-task1`
Expected: See all remaining validation-branch-only files and modules.

**Step 2: Group files into decision buckets**

Buckets:
- `live-verification-only`
- `potential-foundation`
- `docs/history divergence only`

**Step 3: Record inventory notes**

Record which code paths are still validation-only and why they are not automatically promotable.

### Task 2: Evaluate remaining code deltas against the promotion bar

**Files:**
- Read: `.worktrees/publish-stage-task1/guanbi_automation/application/publish_live_verification_service.py`
- Read: `.worktrees/publish-stage-task1/guanbi_automation/application/live_verification_spec.py`
- Read: `.worktrees/publish-stage-task1/guanbi_automation/domain/live_verification.py`
- Read: `.worktrees/publish-stage-task1/guanbi_automation/infrastructure/feishu/client.py`
- Read: `.worktrees/publish-stage-task1/guanbi_automation/infrastructure/feishu/target_planner.py`
- Read: `.worktrees/publish-stage-task1/tests/application/test_publish_live_verification_service.py`
- Read: `.worktrees/publish-stage-task1/tests/infrastructure/feishu/test_client.py`
- Read: `.worktrees/publish-stage-task1/tests/infrastructure/feishu/test_target_planner.py`

**Step 1: Identify evidence-backed necessity**

For each runtime delta, answer:
- Did real publish live verification depend on it?
- Is it general-purpose foundation behavior or validation scaffolding?
- Does it encode any machine-private or target-private information?

**Step 2: Decide promotability**

Use the fixed bar:
1. Proven necessary by real evidence
2. No machine-private dependency
3. Foundation scope
4. Fresh verification feasible on `main`

**Step 3: Write down explicit keep/promote decisions**

No ambiguous middle state. Each candidate ends as either:
- `promote now`
- `keep on validation branch`
- `needs new evidence`

### Task 3: Implement only the approved delta

**Files:**
- Modify only files required by approved promotion decisions
- Test only files relevant to approved promotion decisions

**Step 1: Write or port failing tests on `main`**

Run focused pytest against the selected area first.

**Step 2: Apply the minimum code change**

Implement only the proven foundation delta. Do not move local spec, real target identifiers, evidence archives, or real-sample entrypoints into `main`.

**Step 3: Re-run focused verification**

Run: focused pytest for the changed area
Expected: pass

**Step 4: Re-run fresh main full suite**

Run: `PYTHONPATH='D:\get_bi_data__1;D:\get_bi_data__1\.packages' + D:\miniconda3\envs\feishu-broadcast\python.exe -m pytest tests -v -p no:cacheprovider`
Expected: full suite passes on `main`

### Task 4: Update authority docs and handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/plans/master-system-design.md`
- Modify: `docs/plans/master-implementation-roadmap.md`
- Modify: `docs/archive/decision-log.md`
- Modify: `docs/archive/sessions/2026-03-23-next-session-handoff.md`
- Create: `docs/archive/sessions/2026-03-23-validation-branch-promotion-sweep.md`

**Step 1: Archive the actual decision**

Capture:
- which deltas were reviewed
- which deltas were promoted or rejected
- why

**Step 2: Update recovery truth**

Ensure `README` and handoff describe the new latest session archive and the latest promotion boundary.

**Step 3: Verify docs match Git reality**

Check current HEADs and branch roles so the docs do not become stale on commit.
