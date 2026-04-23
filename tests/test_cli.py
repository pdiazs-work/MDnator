import pytest

from cli import build_parser, main


def test_parser_requires_input():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_parser_single_input():
    parser = build_parser()
    args = parser.parse_args(["file.txt"])
    assert args.inputs == ["file.txt"]
    assert args.output is None


def test_parser_output_flag():
    parser = build_parser()
    args = parser.parse_args(["file.txt", "-o", "out.md"])
    assert args.output == "out.md"


def test_cli_missing_file_returns_error():
    result = main(["nonexistent_file_xyz.pdf"])
    assert result == 1


def test_cli_converts_txt_to_stdout(tmp_path, capsys):
    f = tmp_path / "sample.txt"
    f.write_text("Hello, world!")
    result = main([str(f)])
    assert result == 0
    captured = capsys.readouterr()
    assert "Hello" in captured.out


def test_cli_converts_txt_to_file(tmp_path):
    src = tmp_path / "sample.txt"
    src.write_text("Hello from CLI!")
    out = tmp_path / "output.md"
    result = main([str(src), "-o", str(out)])
    assert result == 0
    assert out.exists()
    assert "Hello from CLI!" in out.read_text(encoding="utf-8")


def test_cli_batch_multiple_files(tmp_path, capsys):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("File A content")
    b.write_text("File B content")
    result = main([str(a), str(b)])
    assert result == 0
    captured = capsys.readouterr()
    assert "a.txt" in captured.out
    assert "b.txt" in captured.out


def test_cli_partial_failure(tmp_path, capsys):
    good = tmp_path / "good.txt"
    good.write_text("Valid content")
    result = main([str(good), "nonexistent.pdf"])
    assert result == 1  # partial failure → exit 1
    captured = capsys.readouterr()
    assert "Valid content" in captured.out
