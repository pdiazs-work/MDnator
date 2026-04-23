from src.config.settings import MAX_BATCH_FILES


def test_max_batch_files_constant():
    assert MAX_BATCH_FILES >= 1


def test_batch_limit_value():
    # Free-tier constraint: keep batch small to avoid overloading the queue
    assert MAX_BATCH_FILES <= 10


def test_batch_files_constant_is_int():
    assert isinstance(MAX_BATCH_FILES, int)
