# models.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal


# =========================
# Languages
# =========================
Lang = Literal["uz", "ru", "en"]

LANG_UZ: Lang = "uz"
LANG_RU: Lang = "ru"
LANG_EN: Lang = "en"
SUPPORTED_LANGS: tuple[Lang, ...] = (LANG_UZ, LANG_RU, LANG_EN)


# =========================
# User Steps (FSM-lite)
# =========================
Step = Literal[
    "choose_lang",
    "wait_name",
    "main_menu",
    "wait_risk",
    "wait_amount",
    "wait_phone",
    "wait_source",
    "ask_free_question",
]

STEP_CHOOSE_LANG: Step = "choose_lang"
STEP_WAIT_NAME: Step = "wait_name"
STEP_MAIN_MENU: Step = "main_menu"
STEP_WAIT_RISK: Step = "wait_risk"
STEP_WAIT_AMOUNT: Step = "wait_amount"
STEP_WAIT_PHONE: Step = "wait_phone"
STEP_WAIT_SOURCE: Step = "wait_source"
STEP_ASK_FREE_QUESTION: Step = "ask_free_question"


# =========================
# Risk Profiles (User choice)
# =========================
RiskProfile = Literal["halol", "konservativ", "yuqori"]

RISK_HALOL: RiskProfile = "halol"           # Low risk (15–18% yillik)
RISK_KONSERV: RiskProfile = "konservativ"   # Medium risk (15–18% yoki 20–25 siz belgilaysiz)
RISK_YUQORI: RiskProfile = "yuqori"         # High/Aggressive (30–50% yillik)

RISK_PROFILES: tuple[RiskProfile, ...] = (RISK_HALOL, RISK_KONSERV, RISK_YUQORI)


# =========================
# Lead Status (Admin result)
# =========================
LeadStatus = Literal["new", "called", "no_answer"]

LEAD_NEW: LeadStatus = "new"
LEAD_CALLED: LeadStatus = "called"
LEAD_NO_ANSWER: LeadStatus = "no_answer"

LEAD_STATUSES: tuple[LeadStatus, ...] = (LEAD_NEW, LEAD_CALLED, LEAD_NO_ANSWER)


# =========================
# Event Types (analytics / stats)
# =========================
EventType = Literal[
    "start",
    "lang_set",
    "name_set",
    "risk_selected",
    "amount_set",
    "phone_set",
    "source_set",
    "free_question",
    "menu_click",
    "admin_mark_called",
    "admin_mark_no_answer",
    "broadcast_sent",
    "reminder_sent",
]

# Admin status mapping
ADMIN_MARK_EVENT: dict[LeadStatus, EventType] = {
    LEAD_CALLED: "admin_mark_called",
    LEAD_NO_ANSWER: "admin_mark_no_answer",
}


# =========================
# Data containers (optional, helpful)
# =========================
@dataclass
class UserProfile:
    tg_id: int
    username: str | None = None
    full_name: str | None = None
    name: str | None = None
    lang: Lang = LANG_UZ
    step: Step = STEP_CHOOSE_LANG

    risk_profile: RiskProfile | None = None
    amount: float | None = None
    phone: str | None = None
    source: str | None = None
    reminder_sent_at: str | None = None

    lead_status: LeadStatus = LEAD_NEW
    created_at: str | None = None
    last_seen: str | None = None
