MAX_FILE_SIZE_MB = 20
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

ALLOWED_EXTENSIONS = frozenset(
    {
        ".pdf",
        ".docx",
        ".xlsx",
        ".pptx",
        ".txt",
        ".csv",
        ".html",
        ".md",
        ".json",
        ".xml",
    }
)

APP_TITLE = "MDnator - Universal Markdown Converter"
APP_DESCRIPTION = "Convert any document to clean Markdown in seconds."
MAX_CONCURRENT_USERS = 2
