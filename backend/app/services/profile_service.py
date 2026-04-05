from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

PROFILE_STORE_PATH = Path("backend/data/profiles.json")
_PROFILE_LOCK = Lock()
SUPPORTED_GOALS = {"upsc", "jee", "neet", "cat", "general"}


def _ensure_store() -> None:
    PROFILE_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not PROFILE_STORE_PATH.exists():
        PROFILE_STORE_PATH.write_text("{}", encoding="utf-8")


def _load_profiles() -> dict[str, dict]:
    _ensure_store()
    try:
        raw = PROFILE_STORE_PATH.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _save_profiles(profiles: dict[str, dict]) -> None:
    _ensure_store()
    PROFILE_STORE_PATH.write_text(json.dumps(profiles, ensure_ascii=False, indent=2), encoding="utf-8")


def _default_name_from_email(user_email: str) -> str:
    handle = user_email.split("@", 1)[0].strip()
    if not handle:
        return "PaperCast User"
    return handle.replace(".", " ").replace("_", " ").title()


def _normalize_goal(goal: str) -> str:
    normalized = (goal or "general").strip().lower()
    return normalized if normalized in SUPPORTED_GOALS else "general"


def get_or_create_profile(user_email: str, name: str = "", profile_image: str = "") -> dict:
    email = user_email.strip().lower()
    if not email:
        raise ValueError("user_email is required.")

    with _PROFILE_LOCK:
        profiles = _load_profiles()
        profile = profiles.get(email)
        if not profile:
            profile = {
                "user_email": email,
                "name": name.strip() or _default_name_from_email(email),
                "email": email,
                "institution": "",
                "bio": "",
                "profile_image": profile_image.strip(),
                "goal": "general",
            }
            profiles[email] = profile
            _save_profiles(profiles)
        elif "goal" not in profile:
            profile["goal"] = "general"
            profiles[email] = profile
            _save_profiles(profiles)
        return profile


def update_profile(
    user_email: str,
    name: str,
    institution: str,
    bio: str,
    profile_image: str = "",
    goal: str = "",
) -> dict:
    email = user_email.strip().lower()
    if not email:
        raise ValueError("user_email is required.")

    with _PROFILE_LOCK:
        profiles = _load_profiles()
        current = profiles.get(email, {})
        profile = {
            "user_email": email,
            "name": name.strip() or current.get("name") or _default_name_from_email(email),
            "email": email,
            "institution": institution.strip(),
            "bio": bio.strip(),
            "profile_image": profile_image.strip() or current.get("profile_image", ""),
            "goal": _normalize_goal(goal) if goal.strip() else _normalize_goal(str(current.get("goal", "general"))),
        }
        profiles[email] = profile
        _save_profiles(profiles)
        return profile


def get_user_goal(user_email: str) -> str:
    profile = get_or_create_profile(user_email=user_email)
    return _normalize_goal(str(profile.get("goal", "general")))


def update_user_goal(user_email: str, goal: str) -> dict:
    email = user_email.strip().lower()
    if not email:
        raise ValueError("user_email is required.")

    normalized_goal = _normalize_goal(goal)
    with _PROFILE_LOCK:
        profiles = _load_profiles()
        current = profiles.get(email, {})
        profile = {
            "user_email": email,
            "name": str(current.get("name", "")).strip() or _default_name_from_email(email),
            "email": email,
            "institution": str(current.get("institution", "")).strip(),
            "bio": str(current.get("bio", "")).strip(),
            "profile_image": str(current.get("profile_image", "")).strip(),
            "goal": normalized_goal,
        }
        profiles[email] = profile
        _save_profiles(profiles)
        return profile
