import zipfile
import tempfile
from tgup.video import get_mime_type


def test_get_mime_type():
    with tempfile.TemporaryFile(suffix=".zip") as temp_file:
        with zipfile.ZipFile(temp_file, "w") as zip_file:
            zip_file.writestr("test.txt", "This is a test file.")
        
        assert get_mime_type(zipfile.Path(temp_file.name)) == "application/zip"
        
