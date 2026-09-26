import pytest

from app.ingestion import InvalidDocument, Passage, chunk, extract


@pytest.mark.parametrize("name,data", [("x.exe", b"text"), ("x.md", b""), ("x.txt", b"\x00"), ("x.pdf", b"not a pdf"), ("x.txt", b"\xff")])
def test_invalid_upload(name, data):
    with pytest.raises(InvalidDocument):
        extract(name, data)


def test_upload_limit():
    with pytest.raises(InvalidDocument):
        extract("x.txt", b"abcd", max_bytes=3)


def test_sections_preserved():
    passages = extract("vpn.md", b"# VPN\nDemo policy\n## Access\nAsk IT.")
    assert [p.section for p in passages] == ["VPN", "Access"]
    assert "Ask IT." in passages[1].content


def test_whitespace_only_rejected():
    with pytest.raises(InvalidDocument):
        extract("x.txt", b" \n\t")


def test_chunk_metadata_and_coverage():
    content = "word " * 2000
    chunks = chunk([Passage(content, page=2, section="VPN")], size=100, overlap=15)
    assert len(chunks) > 20
    assert all(p.page == 2 and p.section == "VPN" for p in chunks)
    assert chunks[0].content.startswith("word")


def test_invalid_chunk_configuration():
    with pytest.raises(ValueError):
        chunk([Passage("test")], size=10, overlap=10)


def test_image_only_or_blank_pdf_rejected():
    import io
    from pypdf import PdfWriter
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    stream = io.BytesIO()
    writer.write(stream)
    with pytest.raises(InvalidDocument, match="No extractable text"):
        extract("scan.pdf", stream.getvalue())
