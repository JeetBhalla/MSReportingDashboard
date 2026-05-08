import os
import unicodedata

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
    # ── SCO - P&D ──────────────────────────────────────────────────────────
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
        "SCO - P&D - PPO - Prod Reliability Crew",
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
        "SCO - P&D - R&C - The Hallucinators",
        "SCO - P&D - R&C - The Third Wheel",
        "SCO - P&D - Run and Close - Jarvis",
        "SCO - P&D - Run and Close - The Ionizers",
    ],
    # ── SCO - SRT ─────────────────────────────────────────────────────────
    "SCO - SRT - Run Operations Sort ART": [
        "SCO - SRT - RunOpsSort - Coding Comrades",
        "SCO - SRT - RunOpsSort - Goal Diggers",
        "SCO - SRT - RunOpsSort - League of Scrummers",
        "SCO - SRT - RunOpsSort - Mobile UI",
        "SCO - SRT - RunOpsSort - Positive",
        "SCO - SRT - RunOpsSort - QA SORTERS",
        "SCO - SRT - RunOpsSort - Shipyard",
        "SCO - SRT - RunOpsSort - SortX",
        "SCO - SRT - RunOpsSort - SortY",
        "SCO - SRT - RunOpsSort - SortZ",
        "SCO - SRT - RunOpsSort - Swat Kats",
        "SCO - SRT - RunOpsSort - Team ISL",
        "SCO - SRT - RunOpsSort - Teck Warriors",
        "SCO - SRT - RunOpsSort - Wafflehaus",
        "SCO - SRT - EU Sort - AmpedMob Team",
        "SCO - SRT - EU Sort - Conquerors Team",
        "SCO - SRT - EU Sort - Copernicus Team",
        "SCO - SRT - EU Sort - DYNAMO Team",
        "SCO - SRT - EU Sort - Falcon Team",
        "SCO - SRT - EU Sort - Navigators Team",
        "SCO - SRT - EU Sort - Phantom Express Team",
        "SCO - SRT - EU Sort - Phoenix Team",
        "SCO - SRT - EU Sort - Retro-Actions Team",
        "SCO - SRT - EU Sort - Sorter Squad",
        "SCO - SRT - EU Sort - System Team",
        "SCO - SRT - EU Sort - Ukuduma Team",
        "SCO - SRT - EU Sort - Warriors Team",
        "SCO - SRT - Dock & Yard - Avengers",
        "SCO - SRT - Dock & Yard - NKOTD",
        "SCO - SRT - Dock & Yard - No Comment",
        "SCO - SRT - Dock & Yard - Scantastic League",
        "SCO - SRT - Dock & Yard - Terminators",
    ],
    "SCO - SRT - Plan & Prepare ART": [
        "SCO - SRT - P&P - Bonham-APS",
        "SCO - SRT - P&P - Elite Squadron",
        "SCO - SRT - P&P - HawkX",
        "SCO - SRT - P&P - Null Pointers",
        "SCO - SRT - P&P - Peak Performers",
        "SCO - SRT - P&P - Phoenix Force",
        "SCO - SRT - P&P - Sort it Out",
        "SCO - SRT - P&P - Sort it Out ACN",
        "SCO - SRT - P&P - Swift Planners",
        "SCO - SRT - P&P - Ukuduma",
        "SCO - SRT - Plan & Prep - Blue Ocean",
        "SCO - SRT - Plan & Prep - DOCKpack",
        "SCO - SRT - Plan & Prep - OneVoice",
        "SCO - SRT - Plan & Prep - Short Circuit",
    ],
    "SCO - SRT - Closing ART": [
        "SCO - SRT - CLO - (Non dev) R&D",
        "SCO - SRT - CLO - Busybeavers",
        "SCO - SRT - CLO - DIY",
        "SCO - SRT - CLO - Edge",
        "SCO - SRT - CLO - Mavericks",
        "SCO - SRT - CLO - Mavericks 2",
        "SCO - SRT - Closing - CYC",
        "SCO - SRT - Closing - Fitastic",
        "SCO - SRT - Closing - GitWrecked",
        "SCO - SRT - Closing - GitWrecked APS",
        "SCO - SRT - Closing - MoMoney",
        "SCO - SRT - Closing - SMTM",
    ],
    # ── SCO - IA ──────────────────────────────────────────────────────────
    "SCO - IA - FAAR": [
        "SCO - IA -  FAAR - FAARchitects",
        "SCO - IA -  FAAR - Magnificent 7",
        "SCO - IA -  FAAR - Optimus Prime",
        "SCO - IA -  FAAR - SharpShooters",
        "SCO - IA -  FAAR - Strikers",
        "SCO - IA -  FAAR - Transformers",
        "SCO - IA - FAAR - Fantastic 4",
        "SCO - IA - FAAR - Magnificent 7 Accenture",
        "SCO - IA - FAAR - Megatron",
        "SCO - IA - FAAR - Pathfinders",
        "SCO - IA - FAAR - TechTitans",
    ],
    "SCO - IA - People & Planning ART": [
        "SCO - IA - P&P - BumbleBees",
        "SCO - IA - P&P - Coding Koalas",
        "SCO - IA - P&P - HoneyBees",
        "SCO - IA - P&P - Mavericks",
        "SCO - IA - P&P - Purple Eagles",
        "SCO - IA - P&P - Stack Smashers",
        "SCO - IA - P&P - SuperKings",
        "SCO - IA - P&P - Superstars",
        "SCO - IA - P&P - Team Alpha",
        "SCO - IA - P&P - Team Spirits",
        "SCO - IA - P&P - Tech Titans",
        "SCO - IA - P&P - Technocrats",
        "SCO - IA - P&P: Reporting",
    ],
    "SCO - IA - TVS": [
        "SCO - IA - TVS - Production Support Team",
        "SCO - IA - TVS - Scrumday, Scrumhow",
    ],
    # ── SCO - LH ──────────────────────────────────────────────────────────
    "SCO - LH - EXE": [
        "SCO - LH - EXE - 404 Not Found",
        "SCO - LH - EXE - 4Runners",
        "SCO - LH - EXE - AgileCrew",
        "SCO - LH - EXE - Boaty McBoatface",
        "SCO - LH - EXE - Celestials",
        "SCO - LH - EXE - Cookie Scrumblers",
        "SCO - LH - EXE - Fast & Curious",
        "SCO - LH - EXE - Guardians of the Galaxy",
        "SCO - LH - EXE - Hawkeyes",
        "SCO - LH - EXE - Hypertext Assassins",
        "SCO - LH - EXE - Jack of All Trades",
        "SCO - LH - EXE - Linehaul Defenders",
        "SCO - LH - EXE - PEAK is Coming",
        "SCO - LH - EXE - Road Warriors",
        "SCO - LH - EXE - SprintMasters",
        "SCO - LH - EXE - Titans",
        "SCO - LH - EXE - Webslingers",
        "SCO - LH - EXE - Wildcards HexStack",
        "SCO - LH - Execution ART - Gryffindor",
        "SCO - LH - Execution ART - Last Tango in Linehaul",
        "SCO - LH - Execution ART - Linehaul Troopers",
        "SCO - LH - Execution ART - Ravenclaw",
        "SCO - LH - Execution ART - Slytherin",
        "SCO - LH - Execution ART - Unstoppables",
    ],
    # ── SCO - TN ──────────────────────────────────────────────────────────
    "SCO - TN - NE": [
        "SCO - TN - NE - Bears, Beets, Battlestar Galactica",
        "SCO - TN - NE - CloudBirds",
        "SCO - TN - NE - IMS-R",
        "SCO - TN - NE - LUNCH",
        "SCO - TN - NE - No Loose Ends",
        "SCO - TN - NE - Notorious MIT",
        "SCO - TN - NE - Power Beats",
        "SCO - TN - NE - Rhythm",
        "SCO - TN - NE - Star Beats",
        "SCO - TN - NE - Strikers",
        "SCO - TN - NE - The Avengers",
        "SCO - TN - NE - The Visionaries",
        "SCO - TN - NE - Three Musketeers",
        "SCO - TN - NE - Top Beats",
        "SCO - TN - NE - UVSDK/SPLITS",
        "SCO - TN - NE - Yoddhas",
    ],
    "SCO - TN - EPART": [
        "SCO - TN - EPART - ADT",
        "SCO - TN - EPART - Transformers",
    ],
    "SCO - TN - ELRS": [
        "SCO - TN - ELRS - LSSI Banded Bandits",
        "SCO - TN - ELRS - LSSI GSAP",
        "SCO - TN - ELRS - LSSI Tech Leads",
    ],
    # ── SCO - ORP ─────────────────────────────────────────────────────────
    "SCO - ORP - GFA": [
        "SCO - ORP - GFA - Alpha",
        "SCO - ORP - GFA - Autobots",
        "SCO - ORP - GFA - Dancing Poodles from Saturn",
        "SCO - ORP - GFA - Dragons",
        "SCO - ORP - GFA - Enablers",
        "SCO - ORP - GFA - Himalayans",
        "SCO - ORP - GFA - MaahiWayz",
        "SCO - ORP - GFA - Thunderbolts",
        "SCO - ORP - GFA - Uniform Allotment",
    ],
    "SCO - ORP - RCC": [
        "SCO - ORP - RCC - Boats and Code",
        "SCO - ORP - RCC - Easy Scrum",
        "SCO - ORP - RCC - Odyssey",
        "SCO - ORP - RCC - Ravenclaw",
        "SCO - ORP - RCC - System Team",
        "SCO - ORP - RCC - Vin Diesel",
    ],
    "SCO - ORP - TVS": [
        "SCO - ORP - TVS - Micro Titans",
        "SCO - ORP - TVS - Mission Impossible",
        "SCO - ORP - TVS - Scrum N Coke",
        "SCO - ORP - TVS - The Enablers",
        "SCO - ORP - TVS - The Incredibles",
    ],
    # ── Other ─────────────────────────────────────────────────────────────
    "FXE Facility Asset Maximo": [],
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
