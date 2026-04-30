"""
validate_sprint_data.py
-----------------------
Standalone validation script to cross-check pull-over and carry-over counts
against the Agility board for a specific team.

Usage:
    python validate_sprint_data.py [team_name_fragment]

Example:
    python validate_sprint_data.py "GG Endeavours"
    python validate_sprint_data.py "BackBenchers"

If no argument is given, defaults to "GG Endeavours".

Requires a valid saved auth session (.auth_session.json).
Run auth_browser.py first if not authenticated.
"""

from __future__ import annotations

import asyncio
import sys
import datetime

from auth_browser import load_saved_session
from agility_client import AgilityClient
from config import AGILITY_BASE_URL, DELIVERED_STATUSES


TEAM_FRAGMENT = sys.argv[1] if len(sys.argv) > 1 else "GG Endeavours"
TODAY = datetime.date.today().isoformat()

SEP  = "─" * 90
SEP2 = "━" * 90


def _status_icon(status: str | None) -> str:
    if status in DELIVERED_STATUSES:
        return "[YES]"
    return "[NO] "


async def main() -> None:
    cookies = load_saved_session()
    if not cookies:
        print("❌  No saved session found. Run auth_browser.py first.")
        sys.exit(1)

    async with AgilityClient.from_cookies(cookies, base_url=AGILITY_BASE_URL) as client:
        # ── 1. Fetch all teams and find the target ─────────────────────────
        all_teams = await client.get_teams_for_team_room(team_room_oid="")
        matched = [t for t in all_teams if TEAM_FRAGMENT.lower() in t.name.lower()]
        if not matched:
            print(f"❌  No team found matching '{TEAM_FRAGMENT}'")
            print("Available teams:")
            for t in sorted(all_teams, key=lambda x: x.name):
                print(f"  {t.name}")
            sys.exit(1)

        team = matched[0]
        print(f"\n{'='*90}")
        print(f"  TEAM : {team.name}")
        print(f"  OID  : {team.oid}")
        print(f"  TODAY: {TODAY}")
        print('='*90)

        # ── 2. Fetch stories first, then derive sprints from story Timebox OIDs
        stories = await client.get_all_stories_for_team(team.oid)
        sprints = await client.get_sprints_from_stories(team.oid, stories)

        print(f"\n  Sprints fetched : {len(sprints)}")
        print(f"  Stories fetched : {len(stories)}\n")

        # ── 3. Bucket stories by sprint ────────────────────────────────────
        sprint_map = {s.oid: s for s in sprints}
        buckets: dict[str, list] = {s.oid: [] for s in sprints}
        unassigned = []

        for story in stories:
            if story.sprint_oid and story.sprint_oid in buckets:
                buckets[story.sprint_oid].append(story)
            else:
                unassigned.append(story)

        # Sort sprints by begin date
        sprints_sorted = sorted(sprints, key=lambda s: s.begin_date or "")

        # Build prev-sprint begin_date lookup (kept for reference / logging)
        prev_begin_map: dict[str, str] = {}
        for idx, sp in enumerate(sprints_sorted):
            prev_begin_map[sp.oid] = (sprints_sorted[idx - 1].begin_date or "")[:10] if idx > 0 else ""

        # ── 4. Per-sprint breakdown ────────────────────────────────────────
        summaries = []
        for sprint in sprints_sorted:
            sprint_stories  = buckets[sprint.oid]
            sprint_end      = (sprint.end_date   or "")[:10]
            sprint_begin    = (sprint.begin_date or "")[:10]
            prev_begin_date = prev_begin_map.get(sprint.oid, "")

            # Delivered-in-sprint logic (mirrors agility_client.py)
            if sprint_end:
                delivered_in_sprint = [
                    s for s in sprint_stories
                    if s.is_delivered and (
                        not s.closed_date
                        or s.closed_date <= sprint_end
                    )
                ]
            else:
                delivered_in_sprint = [s for s in sprint_stories if s.is_delivered]

            # Pull Forward: PF: prefix only
            pull_fwd = [s for s in sprint_stories if s.name.startswith("PF:")]

            # Carry-over: CO: prefix only
            carry_ins = [s for s in sprint_stories if s.name.startswith("CO:")]

            # Planned at sprint start: exclude Pull Forward stories (added mid-sprint)
            planned_stories = [s for s in sprint_stories if not s.name.startswith("PF:")]

            sprint_ended   = bool(sprint_end   and sprint_end   < TODAY)
            sprint_started = bool(sprint_begin and sprint_begin <= TODAY)
            sprint_future  = bool(sprint_begin and sprint_begin > TODAY)

            state = "FUTURE  " if sprint_future else ("CURRENT " if not sprint_ended else "PAST    ")

            summaries.append({
                "sprint":              sprint,
                "sprint_stories":      sprint_stories,
                "planned_stories":     planned_stories,
                "delivered_in_sprint": delivered_in_sprint,
                "carry_ins":           carry_ins,
                "pull_fwd":            pull_fwd,
                "sprint_ended":        sprint_ended,
                "sprint_started":      sprint_started,
                "sprint_future":       sprint_future,
                "state":               state,
                "sprint_begin":        sprint_begin,
                "sprint_end":          sprint_end,
                "prev_begin_date":     prev_begin_date,
            })

        # Compute display values (mirrors agility_client.py)
        for i, row in enumerate(summaries):
            if row["sprint_future"]:
                row["pull_fwd_display"]    = "–"
                row["carry_over_display"]  = "–"
            else:
                pf = len(row["pull_fwd"])
                row["pull_fwd_display"]   = str(pf) if pf > 0 else "–"
                row["carry_over_display"] = str(len(row["carry_ins"]))

        # ── 5. Print summary table ─────────────────────────────────────────
        print(f"{'Sprint':<45} {'State':<10} {'Planned':>8} {'Delivered':>10} {'Pull Fwd':>10} {'Carry Over':>11}")
        print(SEP)
        for row in summaries:
            s = row["sprint"]
            print(
                f"{s.name:<45} {row['state']:<10} "
                f"{len(row['planned_stories']):>8} "
                f"{len(row['delivered_in_sprint']):>10} "
                f"{row.get('pull_fwd_display', '–'):>10} "
                f"{row.get('carry_over_display', '–'):>11}"
            )

        # ── 6. Per-sprint story detail for past/current sprints ───────────
        print(f"\n{'='*90}")
        print("  STORY-LEVEL DETAIL (for cross-check with Agility board)")
        print('='*90)

        for row in summaries:
            if row["sprint_future"]:
                continue  # skip future sprints

            s = row["sprint"]
            sprint_end   = (s.end_date   or "")[:10]
            sprint_begin = (s.begin_date or "")[:10]

            print(f"\n{'='*60}")
            print(f"  {s.name}  [{sprint_begin} -> {sprint_end}]  {row['state'].strip()}")
            print(f"  Prev sprint begin      : {row['prev_begin_date'] or '(first sprint)'}")
            print(f"  Total stories in bucket: {len(row['sprint_stories'])} (incl. Pull Forwards)")
            print(f"  Planned at sprint start: {len(row['planned_stories'])} (excl. PF: stories)")
            print(f"  Delivered in sprint    : {len(row['delivered_in_sprint'])}")
            print(f"  Pull Forward (count)   : {row.get('pull_fwd_display','–')}")
            print(f"  Carry Over             : {row.get('carry_over_display','–')}")
            print()

            # All stories in this sprint's bucket
            print(f"  {'#':<4} {'Number':<12} {'Type':<8} {'Status':<15} {'Delivered?':<11} {'Created':<12} {'Closed':<12}  Story Name")
            print(f"  {'-'*110}")
            for idx, st in enumerate(sorted(row["sprint_stories"], key=lambda x: x.name), 1):
                delivered_flag = "[YES]" if st.is_delivered else "[NO] "
                num = st.number or st.oid
                late = ""
                if st.is_delivered and st.closed_date and sprint_end and st.closed_date > sprint_end:
                    late = "  [LATE]"
                carry  = "  [CARRY]"    if st.name.startswith("CO:")    else ""
                pf_tag = "  [PULL FWD]" if st.name.startswith("PF:")    else ""
                print(
                    f"  {idx:<4} {num:<12} {st.item_type:<8} {(st.status or '?'):<15} {delivered_flag:<11} "
                    f"{(st.create_date or '?'):<12} {(st.closed_date or '-'):<12}  "
                    f"{st.name[:50]}{late}{carry}{pf_tag}"
                )

        # ── 7. Explanation of carry-over logic for validation ─────────────
        print(f"\n{'='*90}")
        print("  LEGEND")
        print('='*90)
        print("  [YES]   Story delivered within sprint window")
        print("  [NO]    Story NOT delivered")
        print("  [LATE]  Delivered, but ClosedDate > sprint end")
        print("  [PULL FWD] Name starts with 'PF:'")
        print("  [CARRY]    Name starts with 'CO:'")
        print("  Type: Story | Defect | Spike  (Spike also auto-detected via 'SPIKE:' prefix)")
        print()
        print(f"  DELIVERED_STATUSES = {DELIVERED_STATUSES}")
        print()
        print("  Pull Forward into sprint N = stories with PF: prefix")
        print("  Carry-over into sprint N   = stories with CO: prefix")
        print()


if __name__ == "__main__":
    asyncio.run(main())
