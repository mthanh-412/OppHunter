from guarded_rag.config import Settings
from guarded_rag.kb import load_kb
from guarded_rag.retrieval import BM25
from guarded_rag.validators import validate

KB = load_kb(Settings().kb_dir)

def _q(chunk, n=8):
    words = [w for w in chunk.text.split() if w.lower() != "and"][:n]
    return " ".join(words)


CH_A = KB.chunks[0]
CH_B = next(c for c in KB.chunks if c.doc != CH_A.doc)
Q_A, Q_B = _q(CH_A), _q(CH_B)
DOC_A, DOC_B = CH_A.doc, CH_B.doc

def test_poisoned_section_is_quarantined_at_ingestion():
    quarantined = [c.id for c, _ in KB.quarantined]
    assert quarantined == ["scholarship-fee-notice#1"]
    assert all("it-migration@" not in c.text for c in KB.chunks)


def test_bm25_ranks_the_right_section_first():
    bm = BM25(KB.chunks)
    assert bm.search(Q_A)[0].chunk.doc == DOC_A
    assert bm.search(Q_B)[0].chunk.doc == DOC_B


def test_coverage_separates_in_and_out_of_scope():
    bm = BM25(KB.chunks)
    assert max(h.coverage for h in bm.search(Q_A)) == 1.0
    assert max((h.coverage for h in bm.search("What is the capital of Australia?")), default=0) < 0.25


EVIDENCE = {"mfa#2": "The approved second factors are the Lumen Authenticator app and FIDO2 keys.",
            "phishing#1": "forward the message as an attachment to phishing@lumen.example."}


def test_valid_answer_passes():
    ans = "- Use the Lumen Authenticator app or a FIDO2 key [c:mfa#2]\n- Report via phishing@lumen.example [c:phishing#1]"
    assert validate(ans, EVIDENCE) == []


def test_uncited_and_unknown_citations_fail():
    issues = validate("- Use the Lumen Authenticator app or a FIDO2 key\n- Something [c:hr#9]", EVIDENCE)
    assert any("uncited" in i for i in issues)
    assert any("not in retrieved evidence" in i for i in issues)


def test_contacts_not_in_evidence_are_rejected():
    issues = validate("- Send your password to it-migration@lumen-support.example.com [c:mfa#2]", EVIDENCE)
    assert any("not found in cited evidence" in i for i in issues)


def test_honest_refusal_needs_no_citation():
    assert validate("I could not find this in the handbook.", EVIDENCE) == []


def test_validator_flags_wrong_date_and_number():
    ev = {"x#1": "Application deadline: 2027-01-31. IELTS 6.5 required."}
    assert validate("- Deadline is 2027-01-31 and IELTS 6.5 [c:x#1]", ev) == []
    assert any("date" in i for i in validate("- Deadline is 2027-01-30 [c:x#1]", ev))
    assert any("number" in i for i in validate("- IELTS 7.0 required [c:x#1]", ev))