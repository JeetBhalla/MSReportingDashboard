from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field


# --- Auth ---------------------------------------------------------------------

class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    message: str = "Authenticated successfully"


# --- Agility Domain Objects ---------------------------------------------------

class TeamModel(BaseModel):
    oid: str = Field(..., description="VersionOne OID e.g. Team:12345")
    name: str
    description: Optional[str] = None
    art: Optional[str] = Field(default=None, description="Agile Release Train (Program) name")


class SprintModel(BaseModel):
    oid: str = Field(..., description="Timebox OID e.g. Timebox:67890")
    name: str
    begin_date: Optional[str] = None
    end_date: Optional[str] = None
    team_oid: Optional[str] = None


class StoryModel(BaseModel):
    oid: str
    number: Optional[str] = None          # Human-readable ID e.g. S-12345, D-456
    item_type: str = "Story"              # Story | Defect | Spike
    name: str
    status: Optional[str] = None
    estimate: Optional[float] = None
    team_oid: Optional[str] = None
    sprint_oid: Optional[str] = None
    closed_date: Optional[str] = None   # ISO date when story reached a delivered status
    create_date: Optional[str] = None   # ISO date when story was created
    is_delivered: bool = False


# --- Summary / Analytics ------------------------------------------------------

class SprintSummary(BaseModel):
    sprint_oid: str
    sprint_name: str
    begin_date: Optional[str] = None
    end_date: Optional[str] = None
    total_planned: int = 0
    total_delivered: int = 0
    pull_forward_count: int = 0   # stories pulled in from backlog/future mid-sprint
    carry_over_count: int = 0    # stories brought IN from previous sprint (unfinished)
    planned_points: float = 0.0
    delivered_points: float = 0.0
    pull_forward_points: float = 0.0
    carry_over_points: float = 0.0
    stories: List[StoryModel] = []


class TeamSprintSummary(BaseModel):
    team_oid: str
    team_name: str
    sprints: List[SprintSummary] = []


class DashboardResponse(BaseModel):
    team_room_oid: str
    teams: List[TeamSprintSummary] = []
    generated_by: str = "FastAPI Direct"
