from proshowpdf.core.naming import sanitize_filename, build_pdf_name, resolve_collision
from proshowpdf.core.models import ConflictPolicy


def test_sanitize_removes_illegal_windows_chars():
    assert sanitize_filename('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_trims_dots_spaces_and_reserved_names():
    assert sanitize_filename("  hello.  ") == "hello"
    assert sanitize_filename("CON") == "_CON"
    assert sanitize_filename("") == "page"


def test_sanitize_truncates_long_names():
    assert len(sanitize_filename("x" * 300)) <= 150


def test_build_pdf_name_prefers_title():
    assert build_pdf_name("My Page", "https://x.com").endswith(".pdf")
    assert build_pdf_name("My Page", "https://x.com").startswith("My Page")


def test_build_pdf_name_falls_back_to_domain_and_timestamp():
    name = build_pdf_name("", "https://www.example.com/path")
    assert name.startswith("example.com_")
    assert name.endswith(".pdf")


def test_resolve_collision_rename(tmp_path):
    (tmp_path / "a.pdf").write_bytes(b"x")
    result = resolve_collision(tmp_path / "a.pdf", ConflictPolicy.RENAME)
    assert result.name == "a (1).pdf"


def test_resolve_collision_overwrite(tmp_path):
    target = tmp_path / "a.pdf"
    target.write_bytes(b"x")
    assert resolve_collision(target, ConflictPolicy.OVERWRITE) == target
