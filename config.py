import os
import unicodedata
from dotenv import load_dotenv

load_dotenv()

# Agility / VersionOne configuration
AGILITY_BASE_URL = os.getenv("AGILITY_BASE_URL", "https://www19.v1host.com/FedEx")

# The TeamRoom ID from the URL (Show/15671286)
TEAM_ROOM_OID = os.getenv("TEAM_ROOM_OID", "TeamRoom:15671286")

# VersionOne REST API path segments
V1_REST_PATH = "rest-1.v1/Data"
V1_QUERY_PATH = "query.v1"

# ART (Agile Release Train) to Team name mapping
# Keys are ART names; values are the exact team names as they appear in Agility.
ART_TEAM_MAP: dict = {
    "SCO - P&D - Conveyence": [
        "SCO - P&D - CONV - Conveyance System Team",
        "SCO - P&D - CONV - Demolition",
        "SCO - P&D - CONV - Endpoint Elites",
        "SCO - P&D - CONV - Monstars",
        "SCO - P&D - CONV - OCE",
        "SCO - P&D - CONV - Orbital",
        "SCO - P&D - CONV - Phoenix",
        "SCO - P&D - CONV - Scrumbags",
        "SCO - P&D - CONV - Sentinel",
        "SCO - P&D - CONV - Skywalkers",
        "SCO - P&D - CONV - Track Stars",
        "SCO - P&D - CONV - Trademark",
        "SCO - P&D - CONV - TuneSquad",
        "SCO - P&D - CONV - Xtra Mile",
        "SCO - P&D - Conveyance -  Quantum Crafters",
        "SCO - P&D - Conveyance - Achievers",
        "SCO - P&D - Conveyance - CoreCraft",
        "SCO - P&D - Conveyance - Inceptors",
        "SCO - P&D - Conveyance - Mavericks",
        "SCO - P&D - Conveyance - Pyramid",
        "SCO - P&D - Conveyance - Titans",
        "SCO - P&D- Conveyance - Camelswagger",
    ],
    "SCO - P&D - Plan N Prepare": [
        "SCO - P&D - PPO - A-Team",
        "SCO - P&D - PPO - Avengers",
        "SCO - P&D - PPO - Cargo Commandos",
        "SCO - P&D - PPO - Delivery Dragons",
        "SCO - P&D - PPO - Edgelords",
        "SCO - P&D - PPO - Express Eagles",
        "SCO - P&D - PPO - Falcons",
        "SCO - P&D - PPO - Managed Services",
        "SCO - P&D - PPO - Mile Movers",
        "SCO - P&D - PPO - No Blockers",
        "SCO - P&D - PPO - Pirates of Scrumbledore",
        "SCO - P&D - PPO - PLA",
        "SCO - P&D - PPO - RoadRunners",
        "SCO - P&D - PPO - RoD - DevOps & E2E",
        "SCO - P&D - PPO - RoD - Observability",
        "SCO - P&D - PPO - RoD - QA",
        "SCO - P&D - PPO - Sprinters",
        "SCO - P&D - PPO - Team 404: Name Does Not Exist",
        "SCO - P&D - PPO - Team ACE",
        "SCO - P&D - PPO - Team SPEED",
        "SCO - P&D - Plan & Prepare - NonSensicals",
        "SCO - P&D - Plan & Prepare - We Rock",
        "SCO - P&D -  Plan & Prepare - Managed Services NEW",
    ],
    "SCO - P&D - Run and Close": [
        "SCO - P&D - R&C - BackBenchers",
        "SCO - P&D - R&C - Code Busters",
        "SCO - P&D - R&C - DADS",
        "SCO - P&D - R&C - Dev-Inators",
        "SCO - P&D - R&C - DIRE-Ab-initio",
        "SCO - P&D - R&C - Eagles",
        "SCO - P&D - R&C - GG Endeavours",
        "SCO - P&D - R&C - GG Visionaries",
        "SCO - P&D - R&C - Ground Gremlins",
        "SCO - P&D - R&C - Ground Gremlins Offshore",
        "SCO - P&D - R&C - Hawks",
        "SCO - P&D - R&C - Jarvis",
        "SCO - P&D - R&C - Maximizers",
        "SCO - P&D - R&C - Megaminds",
        "SCO - P&D - R&C - Not Fast, Just Furious",
        "SCO - P&D - R&C - Optimizers",
        "SCO - P&D - R&C - PnD Express Support Crew",
        "SCO - P&D - R&C - PnD Ground Support Crew",
        "SCO - P&D - R&C - PnD Performance Testing",
        "SCO - P&D - R&C - PnD Vanguards",
        "SCO - P&D - R&C - Prodigies",
        "SCO - P&D - R&C - Synergies",
        "SCO - P&D - R&C - Synergies - CPC",
        "SCO - P&D - R&C - Tech Titans",
        "SCO - P&D - R&C - The Third Wheel",
        "SCO - P&D - Run and Close - Jarvis",
        "SCO - P&D - Run and Close - The Ionizers",
    ],
}

def _normalize(s: str) -> str:
    """Normalize a team name for comparison: lowercase, collapse whitespace,
    replace curly/smart quotes and typographic dashes with plain ASCII."""
    # Unicode normalize to decompose characters
    s = unicodedata.normalize("NFKD", s or "")
    # Replace curly apostrophes / right-single-quotation with straight apostrophe
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u02bc", "'")
    # Replace en-dash / em-dash with hyphen
    s = s.replace("\u2013", "-").replace("\u2014", "-")
    # Strip accents (decomposed diacritics)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Collapse whitespace and lowercase
    return " ".join(s.lower().split())


# Reverse lookup: normalised team name -> ART name  (built once at import time)
_TEAM_TO_ART: dict = {
    _normalize(team): art
    for art, teams in ART_TEAM_MAP.items()
    for team in teams
}


def get_art_for_team(team_name: str) -> str | None:
    """Return the ART for a team using exact full-name match (case/unicode-insensitive)."""
    return _TEAM_TO_ART.get(_normalize(team_name))


# Agility Story status values that count as "Delivered / Done"
DELIVERED_STATUSES = {
    "Accepted",
    "Done",
    "Completed",
    "Closed",
    "Delivered",
}
