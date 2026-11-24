from digest.cards import validate_prompt, write_card
from digest.extract import check_practice, extract, rank
from digest.main import run_pipeline
from digest.models import Item
from digest.render import PASTE_LINE, render

REG = {
    "official_sources": [{"name": "Docs", "domains": ["anthropic.com"]}],
    "people": [{"name": "Ada Builder", "role": "Engineer", "company": "Lab", "tier": 1,
                "verified_by": ["a", "b"]}],
}

GOOD_SKILL = {
    "title": "Test after every change", "when": "after a feature lands", "mechanism": "skill",
    "install_prompt": "Create ~/.claude/skills/test-after/SKILL.md with description: "
                      "'Use automatically after any feature is added or changed'. Then append "
                      "'- After any feature change, use the test-after skill.' to ~/.claude/CLAUDE.md.",
}


class FakeLLM:
    """Routes by schema name; records calls."""
    def __init__(self, practices_by_url=None, card=None):
        self.p = practices_by_url or {}
        self.card = card or GOOD_SKILL
        self.calls = []

    def json(self, system, user, schema, name="out"):
        self.calls.append(name)
        if name == "practices":
            url = user.split("URL: ", 1)[1].split("\n", 1)[0]
            return {"practices": self.p.get(url, [])}
        if name == "ranking":
            n = user.count("\n[") + 1
            return {"ids": list(range(n))[::-1] + [99, 0]}  # reversed, out-of-range, dup
        if name == "card":
            return dict(self.card)


def P(practice, speaker):
    return {"practice": practice, "speaker": speaker, "use_case": "u", "quote": "q"}


def test_podcast_host_tip_dropped_guest_tip_kept():
    pod = Item("https://pod/1", "Ep", "podcast", hosts=["Host Name"], text="transcript")
    llm = FakeLLM({"https://pod/1": [P("host tip", "Host Name"), P("guest tip", "Ada Builder"),
                                     P("mystery", "UNKNOWN")]})
    practices, dropped = extract([pod], REG, llm)
    assert [p["practice"] for p in practices] == ["guest tip"]
    assert practices[0]["person"]["name"] == "Ada Builder"
    assert {d["practice"] for d in dropped} == {"host tip", "mystery"}


def test_official_page_tip_kept_without_person():
    it = Item("https://www.anthropic.com/engineering/x", "Post", "official", text="t")
    d = check_practice(it, P("x", ""), REG)
    assert d.keep and d.person is None


def test_official_page_named_registry_person_gets_credit():
    it = Item("https://www.anthropic.com/engineering/x", "Post", "official", text="t")
    assert check_practice(it, P("x", "Ada Builder"), REG).person["name"] == "Ada Builder"


def test_person_feed_quoting_outsider_dropped():
    it = Item("https://ada.blog/1", "Post", "person", author="Ada Builder", text="t")
    assert not check_practice(it, P("x", "Random Guy"), REG).keep
    assert check_practice(it, P("x", "Ada Builder"), REG).keep


def test_rank_dedupes_and_caps():
    ps = [P(f"p{i}", "") for i in range(7)]
    top = rank(ps, FakeLLM())
    assert len(top) == 5 and len({id(p) for p in top}) == 5


def test_validate_prompt_rules():
    assert validate_prompt(GOOD_SKILL) == []
    vague = {**GOOD_SKILL, "install_prompt": "Create ~/.claude/skills/x/SKILL.md describing testing."}
    errs = validate_prompt(vague)
    assert any("trigger" in e for e in errs) and any("CLAUDE.md" in e for e in errs)
    assert validate_prompt({"mechanism": "rule", "install_prompt": "Remember to test."})
    assert validate_prompt({"mechanism": "command", "install_prompt": "write ~/.claude/commands/t.md"}) == []


def test_bad_card_rejected_after_retries():
    pr = {**P("x", ""), "source_url": "https://u", "source_title": "T", "person": None}
    c, why = write_card(pr, FakeLLM(card={**GOOD_SKILL, "install_prompt": "just do it once"}))
    assert c is None and "failed checks" in why


def test_card_byline_comes_from_registry_not_llm():
    pr = {**P("x", "Ada Builder"), "source_url": "https://u", "source_title": "T",
          "person": REG["people"][0]}
    c, _ = write_card(pr, FakeLLM())
    assert (c["name"], c["role"], c["company"]) == ("Ada Builder", "Engineer", "Lab")


def test_render_has_required_card_parts():
    c = {**GOOD_SKILL, "name": "Ada <b>", "role": "Eng", "company": "Lab",
         "source_url": "https://u", "source_title": "T"}
    h = render([c], "2026-11-23")
    assert PASTE_LINE in h and "<b>Ada &lt;b&gt;, Eng, Lab</b>" in h and 'href="https://u"' in h
    assert "<pre" in h and 'name="viewport"' in h


def test_run_pipeline_end_to_end():
    items = [Item("https://www.anthropic.com/a", "A", "official"),
             Item("https://evil.com/a", "B", "official", text="t"),
             Item("https://pod/1", "Ep", "podcast", hosts=["Host"], text="tr")]
    llm = FakeLLM({"https://www.anthropic.com/a": [P("official tip", "")],
                   "https://pod/1": [P("host tip", "Host"), P("guest tip", "Ada Builder")]})
    cards, rep = run_pipeline(REG, llm, collect_fn=lambda r, days: (items, []),
                              text_fn=lambda u: "fetched body", log=lambda *_: None)
    assert len(cards) == 2
    assert {c["name"] for c in cards} == {"Anthropic", "Ada Builder"}
    reasons = " ".join(d["reason"] for d in rep["dropped"])
    assert "not an official domain" in reasons and "host" in reasons
