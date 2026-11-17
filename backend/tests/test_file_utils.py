import os
import tempfile
import pytest
from app.utils.file_utils import get_source_files, find_dependency_files, read_file_safe

def test_get_source_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create sample files
        py_file = os.path.join(tmpdir, "test.py")
        with open(py_file, "w") as f:
            f.write("print('hello world')\n")

        js_file = os.path.join(tmpdir, "app.js")
        with open(js_file, "w") as f:
            f.write("console.log('test');\n")

        # Hidden file or ignored directory
        git_dir = os.path.join(tmpdir, ".git")
        os.makedirs(git_dir)
        with open(os.path.join(git_dir, "config"), "w") as f:
            f.write("git config")

        files = get_source_files(tmpdir)
        file_paths = [f["path"] for f in files]
        assert "test.py" in file_paths
        assert "app.js" in file_paths
        assert not any(".git" in p for p in file_paths)

def test_find_dependency_files():
    with tempfile.TemporaryDirectory() as tmpdir:
        req_file = os.path.join(tmpdir, "requirements.txt")
        with open(req_file, "w") as f:
            f.write("requests==2.25.0\n")

        dep_files = find_dependency_files(tmpdir)
        names = [d["name"] for d in dep_files]
        assert "requirements.txt" in names
