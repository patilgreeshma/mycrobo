import pytest
from app.utils.language_detector import detect_languages, detect_frameworks

def test_detect_languages():
    files = [
        {"path": "app/main.py", "extension": ".py", "lines": 50},
        {"path": "app/utils.py", "extension": ".py", "lines": 30},
        {"path": "frontend/src/App.jsx", "extension": ".jsx", "lines": 80},
        {"path": "frontend/src/index.ts", "extension": ".ts", "lines": 40},
    ]
    languages = detect_languages(files)
    assert "Python" in languages
    assert "JavaScript" in languages or "TypeScript" in languages
    assert languages["Python"] == 2

def test_detect_frameworks_fastapi_and_react():
    files = [
        {"path": "backend/app/main.py", "extension": ".py", "content": "from fastapi import FastAPI\napp = FastAPI()"},
        {"path": "frontend/src/App.jsx", "extension": ".jsx", "content": "import React from 'react';"},
    ]
    dep_files = [
        {"name": "package.json", "content": '{"dependencies": {"react": "^18.0.0"}}'},
        {"name": "requirements.txt", "content": "fastapi>=0.100.0\nuvicorn\n"},
    ]
    frameworks = detect_frameworks(files, dep_files)
    assert "FastAPI" in frameworks
    assert "React" in frameworks
