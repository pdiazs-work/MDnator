import pytest

from src.core.converter import DocumentConverter


def test_convert_txt(tmp_path):
    sample = tmp_path / "sample.txt"
    sample.write_text("hola mundo desde MDnator")
    converter = DocumentConverter()
    result = converter.convert(str(sample))
    assert isinstance(result, str)
    assert len(result) > 0


def test_convert_missing_file():
    converter = DocumentConverter()
    with pytest.raises(RuntimeError):
        converter.convert("/no/existe/archivo.txt")
