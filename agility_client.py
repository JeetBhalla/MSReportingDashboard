"""
agility_client.py
-----------------
Wrapper around the VersionOne (Agility) REST API.

Authentication : HTTP Basic Auth (username / password).
API docs       : https://community.versionone.com/VersionOne_Connect/Developer_Library/REST_API
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from config import (
    AGILITY_BASE_URL,
    DELIVERED_STATUSES,
    V1_REST_PATH,
    get_art_for_team,
)
from models import SprintModel, SprintSummary, StoryModel, TeamModel, TeamSprintSummary

logger = logging.getLogger(__name__)

# Regex helpers — match PF: / PF- / pf: / pf- (and same for CO) case-insensitively
_PF_RE = re.compile(r"^pf[:\-]", re.IGNORECASE)
_CO_RE = re.compile(r"^co[:\-]", re.IGNORECASE)


def _is_pf(name: str) -> bool:
    """Return True if *name* is a Pull Forward story (PF:/PF- prefix, any case)."""
    return bool(_PF_RE.match(name or ""))


def _is_co(name: str) -> bool:
    """Return True if *name* is a Carry Over story (CO:/CO- prefix, any case)."""
    return bool(_CO_RE.match(name or ""))


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _oid(asset: Dict[str, Any]) -> str:
    """Extract OID string from a V1 asset dict."""
    return asset.get("id", "")


def _attr(asset: Dict[str, Any], key: str) -> Any:
    """Safely read a V1 attribute value that may be nested."""
    val = asset.get("Attributes", {}).get(key, {})
    if isinstance(val, dict):
        return val.get("value")
    return val


def _relation_oid(asset: Dict[str, Any], key: str) -> Optional[str]:
    """Extract OID from a relation attribute (e.g. Team, Timebox)."""
    val = asset.get("Attributes", {}).get(key, {})
    if isinstance(val, dict):
        inner = val.get("value")
        if isinstance(inner, dict):
            return inner.get("idref")
        if isinstance(inner, str):
            return inner
    return None


# ------------------------------------------------------------------------------
# Client
# ------------------------------------------------------------------------------

class AgilityClient:
    """Thin async client for the VersionOne REST API (cookie/SSO auth)."""

    def __init__(self, base_url: str = AGILITY_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self._headers: Dict[str, str] = {"Accept": "application/json"}
        self._cookies: Optional[List[Dict]] = None
        self._client: Optional[httpx.AsyncClient] = None

    @classmethod
    def from_cookies(cls, cookies: List[Any], base_url: str = AGILITY_BASE_URL) -> "AgilityClient":
        """Create client authenticated via browser session cookies (OKTA/SSO)."""
        instance = cls(base_url=base_url)
        instance._cookies = cookies
        return instance

    # -- context manager -------------------------------------------------------

    async def __aenter__(self) -> "AgilityClient":
        # Build httpx cookies dict from Playwright cookie list if provided
        httpx_cookies = None
        if self._cookies:
            httpx_cookies = {c["name"]: c["value"] for c in self._cookies if "name" in c and "value" in c}
        self._client = httpx.AsyncClient(
            headers=self._headers,
            cookies=httpx_cookies,
            timeout=60.0,
            verify=False,
            follow_redirects=True,
        )
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._client:
            await self._client.aclose()

    # -- low-level helpers -----------------------------------------------------

    async def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.base_url}/{path}"
        logger.debug("GET %s params=%s", url, params)
        resp = await self._client.get(url, params=params)
        resp.raise_for_status()
        return resp.json()

    # -- Teams ------------------------------------------------------------------

    async def get_teams_for_team_room(self, team_room_oid: str) -> List[TeamModel]:
        """
        Return all Team assets. ART is assigned via the hardcoded
        ART_TEAM_MAP in config.py (case-insensitive team name lookup).
        """
        team_params: Dict[str, Any] = {
            "sel": "Name,Description",
            "fmt": "json",
            "pageSize": 500,
            "sort": "Name",
        }
        team_data = await self._get(f"{V1_REST_PATH}/Team", params=team_params)
        assets = team_data.get("Assets", [])

        teams: List[TeamModel] = []
        for a in assets:
            team_name = _attr(a, "Name") or "Unknown"
            teams.append(TeamModel(
                oid=_oid(a),
                name=team_name,
                description=_attr(a, "Description"),
                art=get_art_for_team(team_name),
            ))

        logger.info(f"Found {len(teams)} teams, {sum(1 for t in teams if t.art)} ART-matched")
        return teams

    # -- Sprints / Timeboxes ---------------------------------------------------

    async def get_sprints_for_team(
        self,
        team_oid: str,
        scope_oid: Optional[str] = None,
        year: Optional[int] = None,
    ) -> List[SprintModel]:
        """
        Fetch Timebox (sprint) records that are actually referenced by this
        team's stories.  We first fetch all stories for the team to collect
        the unique Timebox OIDs, then look up only those Timeboxes.
        This avoids the previous bug of fetching ALL system Timeboxes (500+)
        and then finding no matching buckets.

        Falls back to the legacy global-timebox fetch when scope_oid is given
        (used on the very first call before stories are available).
        """
        if scope_oid:
            # Legacy path — used when an explicit scope is provided
            params: Dict[str, Any] = {
                "sel": "Name,BeginDate,EndDate,Schedule",
                "where": f"Schedule.ScheduledScopes='{scope_oid}'",
                "fmt": "json",
                "pageSize": 500,
                "sort": "BeginDate",
            }
            data = await self._get(f"{V1_REST_PATH}/Timebox", params=params)
            assets = data.get("Assets", [])
            sprints = [
                SprintModel(
                    oid=_oid(a),
                    name=_attr(a, "Name") or "Unknown Sprint",
                    begin_date=_attr(a, "BeginDate"),
                    end_date=_attr(a, "EndDate"),
                    team_oid=team_oid,
                )
                for a in assets
            ]
            if year:
                year_str = str(year)
                sprints = [s for s in sprints if s.begin_date and s.begin_date.startswith(year_str)]
            return sprints

        # Primary path: derive sprint list from the team's own stories
        stories = await self.get_all_stories_for_team(team_oid, year=year)
        return await self.get_sprints_from_stories(team_oid, stories, year=year)

    async def get_sprints_from_stories(
        self,
        team_oid: str,
        stories: List[StoryModel],
        year: Optional[int] = None,
    ) -> List[SprintModel]:
        """
        Given a list of stories already fetched for a team, look up the
        Timebox (sprint) records for every unique sprint OID referenced by
        those stories.  This guarantees 1-to-1 matching between story buckets
        and sprint metadata.
        """
        # Collect unique timebox OIDs referenced by stories
        sprint_oids: List[str] = list({
            s.sprint_oid for s in stories if s.sprint_oid
        })

        if not sprint_oids:
            return []

        # VersionOne REST allows OR via pipe: ID='Timebox:1'|ID='Timebox:2'
        # But with many OIDs this can get long; batch in groups of 50.
        sprints: List[SprintModel] = []
        batch_size = 50
        for i in range(0, len(sprint_oids), batch_size):
            batch = sprint_oids[i : i + batch_size]
            where_clause = "|".join(f"ID='{oid}'" for oid in batch)
            params: Dict[str, Any] = {
                "sel": "Name,BeginDate,EndDate",
                "where": where_clause,
                "fmt": "json",
                "pageSize": batch_size + 10,
            }
            data = await self._get(f"{V1_REST_PATH}/Timebox", params=params)
            for a in data.get("Assets", []):
                sprints.append(SprintModel(
                    oid=_oid(a),
                    name=_attr(a, "Name") or "Unknown Sprint",
                    begin_date=_attr(a, "BeginDate"),
                    end_date=_attr(a, "EndDate"),
                    team_oid=team_oid,
                ))

        # Year filter
        if year:
            year_str = str(year)
            sprints = [s for s in sprints if s.begin_date and s.begin_date.startswith(year_str)]

        logger.info(
            "get_sprints_from_stories: team=%s stories=%d unique_sprint_oids=%d resolved=%d",
            team_oid, len(stories), len(sprint_oids), len(sprints),
        )
        return sprints

    # -- Stories / Defects / Spikes --------------------------------------------

    async def _fetch_assets_for_team(self, asset_type: str, team_oid: str) -> List[StoryModel]:
        """Fetch Story, Defect, or Spike assets for a team and return as StoryModel list."""
        params: Dict[str, Any] = {
            "sel": "Name,Number,Status.Name,Estimate,Team,Timebox,ClosedDate,CreateDate",
            "where": f"Team='{team_oid}'",
            "fmt": "json",
            "pageSize": 2000,
        }
        try:
            data = await self._get(f"{V1_REST_PATH}/{asset_type}", params=params)
        except Exception as exc:
            logger.warning("Could not fetch %s for team %s: %s", asset_type, team_oid, exc)
            return []
        assets = data.get("Assets", [])
        results: List[StoryModel] = []
        for a in assets:
            status = _attr(a, "Status.Name") or ""
            estimate_raw = _attr(a, "Estimate")
            try:
                estimate = float(estimate_raw) if estimate_raw is not None else 0.0
            except (TypeError, ValueError):
                estimate = 0.0
            closed_raw  = _attr(a, "ClosedDate")
            create_raw  = _attr(a, "CreateDate")
            closed_date = str(closed_raw)[:10] if closed_raw else None
            create_date = str(create_raw)[:10] if create_raw else None
            name = _attr(a, "Name") or "Untitled"
            # SPIKE: prefix anywhere overrides the asset_type label
            if name.startswith("SPIKE:"):
                item_type = "Spike"
            else:
                item_type = asset_type   # "Story", "Defect", or "Spike"
            results.append(
                StoryModel(
                    oid=_oid(a),
                    number=_attr(a, "Number") or None,
                    item_type=item_type,
                    name=name,
                    status=status,
                    estimate=estimate,
                    team_oid=_relation_oid(a, "Team"),
                    sprint_oid=_relation_oid(a, "Timebox"),
                    closed_date=closed_date,
                    create_date=create_date,
                    is_delivered=status in DELIVERED_STATUSES,
                )
            )
        logger.info("Fetched %d %s(s) for team %s", len(results), asset_type, team_oid)
        return results

    async def get_all_stories_for_team(self, team_oid: str, year: Optional[int] = None) -> List[StoryModel]:
        """Fetch Stories, Defects, and Spikes for a team and return merged list.
        Year filtering is handled at the sprint level, not here.
        """
        import asyncio as _asyncio
        story_task, defect_task, spike_task = await _asyncio.gather(
            self._fetch_assets_for_team("Story",  team_oid),
            self._fetch_assets_for_team("Defect", team_oid),
            self._fetch_assets_for_team("Spike",  team_oid),
        )
        all_items = story_task + defect_task + spike_task
        logger.info(
            "get_all_stories_for_team: team=%s stories=%d defects=%d spikes=%d total=%d",
            team_oid, len(story_task), len(defect_task), len(spike_task), len(all_items),
        )
        return all_items

    async def get_story_counts_for_team(
        self, team_oid: str,
        date_from: Optional[str] = None,
        date_to:   Optional[str] = None,
    ) -> Dict[str, int]:
        """Lightweight fetch: return only {committed, completed} counts for a team.
        Covers Stories, Defects, and Spikes.
        date_from / date_to are ISO date strings (YYYY-MM-DD) used to filter by
        sprint begin date.  Both default to the current calendar year.
        Used by ART-level overview charts that only need totals.
        """
        import asyncio as _asyncio
        import datetime as _dt
        _today = _dt.date.today()
        _df = date_from or f"{_today.year}-01-01"
        _dt2 = date_to   or f"{_today.year}-12-31"
        where = (
            f"Team='{team_oid}'"
            f";Timebox.BeginDate>='{_df}'"
            f";Timebox.BeginDate<='{_dt2}'"
        )
        params: Dict[str, Any] = {
            "sel":      "Name,Status.Name",
            "where":    where,
            "fmt":      "json",
            "pageSize": 2000,
        }
        async def _count(asset_type: str) -> List[Any]:
            try:
                data = await self._get(f"{V1_REST_PATH}/{asset_type}", params=params)
                return data.get("Assets", [])
            except Exception:
                return []

        story_assets, defect_assets, spike_assets = await _asyncio.gather(
            _count("Story"), _count("Defect"), _count("Spike"),
        )
        all_assets = story_assets + defect_assets + spike_assets
        # Exclude Pull Forward stories (PF: prefix) — they were added mid-sprint
        # and should not count towards committed (planned at sprint start).
        committed = sum(
            1 for a in all_assets
            if not _is_pf(_attr(a, "Name") or "")
        )
        completed = sum(
            1 for a in all_assets
            if not _is_pf(_attr(a, "Name") or "")
            and (_attr(a, "Status.Name") or "") in DELIVERED_STATUSES
        )
        return {"committed": committed, "completed": completed}

    # -- High-level aggregation ------------------------------------------------

    async def build_team_sprint_summary(
        self,
        team: TeamModel,
        sprints: List[SprintModel],
        all_stories: List[StoryModel],
    ) -> TeamSprintSummary:
        """
        Group pre-fetched stories by sprint and build a per-sprint summary
        for the given team.
        """
        sprint_map: Dict[str, SprintModel] = {s.oid: s for s in sprints}
        buckets: Dict[str, List[StoryModel]] = {s.oid: [] for s in sprints}

        # Bucket stories into their sprint
        for story in all_stories:
            sprint_ref = story.sprint_oid
            if sprint_ref and sprint_ref in buckets:
                buckets[sprint_ref].append(story)

        # Sort sprints by begin date first — needed for the carry-over window logic
        sorted_sprints = sorted(sprint_map.values(), key=lambda s: s.begin_date or "")
        # Build a prev-sprint begin_date lookup: for each sprint OID, what is
        # the begin_date of the immediately preceding sprint?
        # prev_begin kept for future use / logging but no longer drives carry-over
        prev_begin: Dict[str, str] = {}
        for idx, sp in enumerate(sorted_sprints):
            if idx > 0:
                prev_begin[sp.oid] = (sorted_sprints[idx - 1].begin_date or "")[:10]
            else:
                prev_begin[sp.oid] = ""   # first sprint — no predecessor

        summaries: List[SprintSummary] = []
        for sprint_oid, sprint_stories in buckets.items():
            sprint = sprint_map[sprint_oid]
            sprint_end   = (sprint.end_date   or "")[:10]
            sprint_begin = (sprint.begin_date  or "")[:10]
            prev_begin_date = prev_begin.get(sprint_oid, "")

            # ── Delivered within this sprint ────────────────────────────────
            # A story counts as delivered-in-sprint when its status is a
            # delivered status AND its ClosedDate (if present) is on/before the
            # sprint end date.  If ClosedDate is absent, trust the status.
            # SPECIAL CASE: If status is "Done", always count it as delivered
            # in the sprint (treat closed date as sprint end date).
            if sprint_end:
                delivered_in_sprint = [
                    s for s in sprint_stories
                    if s.is_delivered and (
                        s.status == "Done"  # If status is Done, always include
                        or not s.closed_date
                        or s.closed_date <= sprint_end
                    )
                ]
            else:
                delivered_in_sprint = [s for s in sprint_stories if s.is_delivered]

            # ── Pull Forward INTO this sprint ──────────────────────────────
            # PF: prefix — explicitly tagged by the team.
            pull_fwd = [s for s in sprint_stories if _is_pf(s.name)]

            # ── Carry-over INTO this sprint ─────────────────────────────────
            # CO: prefix — explicitly tagged by the team.
            carry_ins = [s for s in sprint_stories if _is_co(s.name)]

            # ── Planned at sprint start ─────────────────────────────────────
            # Exclude Pull Forward stories — those were added mid-sprint after
            # the sprint began, so they were not part of the original plan.
            planned_stories = [s for s in sprint_stories if not _is_pf(s.name)]

            # ── Planned stories that were actually delivered ─────────────────
            # Used for delivery rate %: how many of the planned stories got done.
            # PF deliveries are excluded so the rate stays within 0-100%.
            planned_delivered = [s for s in delivered_in_sprint if not _is_pf(s.name)]

            logger.debug(
                "Sprint %s | planned=%d (excl PF) delivered=%d carry_over=%d pull_forward=%d "
                "(sprint_begin=%s)",
                sprint.name, len(planned_stories), len(delivered_in_sprint),
                len(carry_ins), len(pull_fwd), sprint_begin,
            )

            summaries.append(
                SprintSummary(
                    sprint_oid=sprint_oid,
                    sprint_name=sprint.name,
                    begin_date=sprint.begin_date,
                    end_date=sprint.end_date,
                    total_planned=len(planned_stories),
                    total_delivered=len(delivered_in_sprint),
                    planned_delivered=len(planned_delivered),
                    pull_forward_count=len(pull_fwd),
                    carry_over_count=len(carry_ins),
                    planned_points=sum(s.estimate or 0 for s in planned_stories),
                    delivered_points=sum(s.estimate or 0 for s in delivered_in_sprint),
                    pull_forward_points=sum(s.estimate or 0 for s in pull_fwd),
                    carry_over_points=sum(s.estimate or 0 for s in carry_ins),
                    stories=sprint_stories,
                )
            )

        # Sort by begin date
        summaries.sort(key=lambda x: x.begin_date or "")

        # ── Apply sentinels for future sprints ───────────────────────────────
        # Sentinel (-1): sprint not yet started → pull_forward and carry_over
        # are not meaningful yet, display "–" in the UI.
        today = __import__('datetime').date.today().isoformat()
        for i, s in enumerate(summaries):
            sprint_begin = (s.begin_date or "")[:10]

            if sprint_begin and sprint_begin > today:
                summaries[i].pull_forward_count  = -1
                summaries[i].pull_forward_points = -1.0
                summaries[i].carry_over_count    = -1
                summaries[i].carry_over_points   = -1.0

        return TeamSprintSummary(
            team_oid=team.oid,
            team_name=team.name,
            sprints=summaries,
        )
