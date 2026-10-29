from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile


book = Path(__file__).with_name("smoke.xlsx")
required = {
    "[Content_Types].xml",
    "_rels/.rels",
    "xl/workbook.xml",
    "xl/_rels/workbook.xml.rels",
    "xl/styles.xml",
    "xl/worksheets/sheet1.xml",
}

with ZipFile(book) as archive:
    assert archive.testzip() is None
    assert required.issubset(archive.namelist())
    for name in required:
        ElementTree.fromstring(archive.read(name))
    sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
    assert "中文评论：很好用 &amp; &lt;满意&gt;" in sheet

book.unlink()
print("xlsx smoke test passed")
