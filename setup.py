from setuptools import setup, find_packages

setup(
    name="universal-precommit",
    version="1.0.0",
    description="Universal Pre-Commit Validation Framework for multi-language projects",
    author="YoburajDTG",
    url="https://github.com/YoburajDTG/universal-pre-commit-hook",
    package_dir={"": "scripts"},
    py_modules=[
        "common",
        "config",
        "detect_project",
        "python_check",
        "react_check",
        "dotnet_check",
        "java_check",
        "cpp_check",
        "go_check",
        "rust_check",
        "docker_check",
        "reporter",
        "run_validation",
        "utils",
    ],
    install_requires=[
        "PyYAML>=6.0.1",
        "colorama>=0.4.6",
        "black>=24.0.0",
        "isort>=5.12.0",
        "ruff>=0.1.0",
        "pytest>=7.0.0",
        "bandit>=1.7.5",
        "pip-audit>=2.6.0",
    ],
    entry_points={
        "console_scripts": [
            "universal-validation=run_validation:main",
            "universal-precommit=run_validation:main",
        ],
    },
    python_requires=">=3.10",
)
