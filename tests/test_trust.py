import pytest

from digest.models import Item
from digest.trust import check, load_registry


@pytest.fixture
def reg():
    return {
        "official_sources": [
            {"name": "Docs", "domains": ["docs.anthropic.com", "github.com/anthropics/claude-code"]}
        ],
        "people": [
            {"name": "Ada Builder", "role": "Engineer", "company": "Lab", "tier": 1,
             "aliases": ["@ada"], "verified_by": ["linkedin", "blog byline"]},
            {"name": "Unproven Person", "role": "Engineer", "company": "Lab", "tier": 1,
             "verified_by": ["linkedin"]},
            {"name": "Outside Pro", "role": "Dev", "company": "Self", "tier": 3,
             "verified_by": ["a", "b"]},
        ],
    }


def test_registry_author_passes(reg):
    assert check(Item("https://x/1", "t", "person", author="Ada Builder"), reg).keep


def test_alias_and_case_pass(reg):
    assert check(Item("https://x/1", "t", "person", author="@ADA"), reg).keep


def test_unknown_reposter_fails(reg):
    it = Item("https://x/2", "t", "reshare", author="Random", original_author="Someone Else")
    assert not check(it, reg).keep


def test_reshare_of_registry_author_passes(reg):
    it = Item("https://x/2", "t", "reshare", author="Random", original_author="Ada Builder")
    assert check(it, reg).keep


def test_reshare_without_original_fails(reg):
    assert not check(Item("https://x/2", "t", "reshare", author="Random"), reg).keep


def test_podcast_host_quote_fails(reg):
    it = Item("https://pod/1", "t", "podcast", speaker="Host Name", host="Host Name")
    assert not check(it, reg).keep


def test_podcast_host_fails_even_if_in_registry(reg):
    it = Item("https://pod/1", "t", "podcast", speaker="Ada Builder", host="Ada Builder")
    assert not check(it, reg).keep


def test_podcast_verified_guest_passes(reg):
    it = Item("https://pod/1", "t", "podcast", speaker="Ada Builder", host="Host Name")
    assert check(it, reg).keep


def test_podcast_unknown_speaker_fails(reg):
    assert not check(Item("https://pod/1", "t", "podcast", host="Host Name"), reg).keep


def test_official_page_passes(reg):
    assert check(Item("https://docs.anthropic.com/en/x", "t", "official"), reg).keep
    assert check(Item("https://github.com/anthropics/claude-code/blob/main/CHANGELOG.md", "t", "official"), reg).keep


def test_fake_official_domain_fails(reg):
    assert not check(Item("https://docs.anthropic.com.evil.io/x", "t", "official"), reg).keep
    assert not check(Item("https://github.com/anthropics/claude-code-fake/x", "t", "official"), reg).keep


def test_fewer_than_two_proofs_fails(reg):
    assert not check(Item("https://x/1", "t", "person", author="Unproven Person"), reg).keep


def test_tier3_excluded_in_mvp(reg):
    assert not check(Item("https://x/1", "t", "person", author="Outside Pro"), reg).keep


def test_real_registry_loads_and_unverified_people_drop():
    reg = load_registry()
    assert len(reg["people"]) == 5
    assert not check(Item("https://x", "t", "person", author="Boris Cherny"), reg).keep
