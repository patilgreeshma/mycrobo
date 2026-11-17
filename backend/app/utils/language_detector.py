"""
CodeSentinel - Language & Framework Detector
Automatically identifies programming languages and frameworks in a repository.
"""

from typing import Dict, List, Tuple
from collections import Counter
import re


# Extension to language mapping
EXTENSION_MAP: Dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "React JSX",
    ".tsx": "React TSX",
    ".java": "Java",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".go": "Go",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".cs": "C#",
    ".swift": "Swift",
    ".rb": "Ruby",
    ".php": "PHP",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".sql": "SQL",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".toml": "TOML",
    ".xml": "XML",
    ".sh": "Shell",
    ".bash": "Shell",
    ".dockerfile": "Dockerfile",
    ".tf": "Terraform",
}


def detect_languages(files: List[dict]) -> Dict[str, int]:
    """
    Detect programming languages used in the project.
    Returns a dict mapping language name to file count.
    """
    lang_counter = Counter()

    for file_info in files:
        ext = file_info.get("extension", "").lower()
        language = EXTENSION_MAP.get(ext)
        if language:
            lang_counter[language] += 1

    return dict(lang_counter.most_common())


def detect_frameworks(files: List[dict], dep_files: List[dict]) -> List[str]:
    """
    Detect frameworks and libraries by examining dependency files and imports.
    Returns a list of detected framework names.
    """
    frameworks = set()

    # Check dependency file contents
    for dep_file in dep_files:
        content = dep_file.get("content", "").lower()
        dep_type = dep_file.get("type", "")
        
        # Infer type from name/path if not explicitly provided
        if not dep_type:
            path_or_name = (dep_file.get("path") or dep_file.get("name") or "").lower()
            if "requirements" in path_or_name or "pipfile" in path_or_name or "pyproject" in path_or_name:
                dep_type = "python-pip"
            elif "package.json" in path_or_name:
                dep_type = "node-npm"

        if dep_type.startswith("python"):
            frameworks.update(_detect_python_frameworks(content))
        elif dep_type.startswith("node"):
            frameworks.update(_detect_node_frameworks(content))
        elif dep_type.startswith("java"):
            frameworks.update(_detect_java_frameworks(content))
        elif dep_type == "php-composer":
            frameworks.update(_detect_php_frameworks(content))
        elif dep_type == "ruby-bundler":
            frameworks.update(_detect_ruby_frameworks(content))
        elif dep_type == "go-mod":
            frameworks.update(_detect_go_frameworks(content))
        elif dep_type == "rust-cargo":
            frameworks.update(_detect_rust_frameworks(content))

    # Check for config files that indicate frameworks
    file_paths = {f["path"].lower() for f in files}
    frameworks.update(_detect_by_config_files(file_paths))

    return sorted(frameworks)


def _detect_python_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("django", "Django"), ("flask", "Flask"), ("fastapi", "FastAPI"),
        ("tornado", "Tornado"), ("pyramid", "Pyramid"), ("celery", "Celery"),
        ("sqlalchemy", "SQLAlchemy"), ("pytest", "Pytest"),
        ("tensorflow", "TensorFlow"), ("pytorch", "PyTorch"), ("torch", "PyTorch"),
        ("pandas", "Pandas"), ("numpy", "NumPy"), ("scikit-learn", "Scikit-learn"),
        ("streamlit", "Streamlit"), ("gradio", "Gradio"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_node_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("react", "React"), ("next", "Next.js"), ("vue", "Vue.js"),
        ("nuxt", "Nuxt.js"), ("angular", "Angular"), ("svelte", "Svelte"),
        ("express", "Express.js"), ("nestjs", "NestJS"), ("koa", "Koa"),
        ("fastify", "Fastify"), ("prisma", "Prisma"), ("mongoose", "Mongoose"),
        ("tailwindcss", "Tailwind CSS"), ("vite", "Vite"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_java_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("spring-boot", "Spring Boot"), ("spring", "Spring"),
        ("hibernate", "Hibernate"), ("junit", "JUnit"),
        ("micronaut", "Micronaut"), ("quarkus", "Quarkus"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_php_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("laravel", "Laravel"), ("symfony", "Symfony"),
        ("codeigniter", "CodeIgniter"), ("wordpress", "WordPress"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_ruby_frameworks(content: str) -> List[str]:
    matches = []
    checks = [("rails", "Ruby on Rails"), ("sinatra", "Sinatra")]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_go_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("gin-gonic", "Gin"), ("gorilla/mux", "Gorilla Mux"),
        ("echo", "Echo"), ("fiber", "Fiber"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_rust_frameworks(content: str) -> List[str]:
    matches = []
    checks = [
        ("actix", "Actix"), ("rocket", "Rocket"),
        ("axum", "Axum"), ("tokio", "Tokio"),
    ]
    for keyword, name in checks:
        if keyword in content:
            matches.append(name)
    return matches


def _detect_by_config_files(file_paths: set) -> List[str]:
    """Detect frameworks by the presence of config files."""
    matches = []
    config_checks = [
        ("next.config.js", "Next.js"), ("next.config.mjs", "Next.js"),
        ("nuxt.config.js", "Nuxt.js"), ("nuxt.config.ts", "Nuxt.js"),
        ("angular.json", "Angular"), ("svelte.config.js", "Svelte"),
        ("vue.config.js", "Vue.js"), ("vite.config.js", "Vite"),
        ("vite.config.ts", "Vite"), ("tailwind.config.js", "Tailwind CSS"),
        ("tailwind.config.ts", "Tailwind CSS"), ("webpack.config.js", "Webpack"),
        ("manage.py", "Django"), ("settings.py", "Django"),
        ("docker-compose.yml", "Docker"), ("dockerfile", "Docker"),
        (".github/workflows", "GitHub Actions"),
        ("terraform.tf", "Terraform"),
    ]
    for config_file, name in config_checks:
        if any(config_file in fp for fp in file_paths):
            matches.append(name)
    return matches
