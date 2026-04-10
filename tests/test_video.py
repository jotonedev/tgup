import os
import zipfile
import tempfile
from tgup.video import get_mime_type


def test_get_mime_type():
    # Setup
    temp_file = tempfile.NamedTemporaryFile(suffix=".zip", delete=False)
    temp_file.close()

    temp_file_path = temp_file.name

    with zipfile.ZipFile(temp_file_path, "w") as zip_file:
        zip_file.writestr("test.txt", "This is a test file.")
    
    # Check
    assert get_mime_type(temp_file_path) == "application/x-zip-compressed"
        
    # Teardown
    os.remove(temp_file_path)
