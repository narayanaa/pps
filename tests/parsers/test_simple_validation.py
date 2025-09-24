from doc.psense.document.document import Document
from doc.psense.document.chapter import Chapter
from doc.psense.document.section import Section
from doc.psense.document.paragraph import Paragraph


def test_simple_validation_roundtrip():
	doc = Document(title="Test")
	ch = Chapter(title="C1", sections=[], number=1)
	sec = Section(title="S1", content=[Paragraph("hello")], level=1)
	ch.sections.append(sec)
	doc.chapters.append(ch)
	assert "Test" in doc.to_text()

