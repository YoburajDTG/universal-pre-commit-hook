from setuptools import setup

setup(
    name="universal-precommit",
    version="1.0.0",
    description="Universal Pre-Commit Validation Framework",
    package_dir={"": "scripts"},
    py_modules=[
        "common",
        "config",
        "detect_project",
        "python_check",
        "react_check",
        "dotnet_check",
        "java_check",
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
        ],
    },
    python_requires=">=3.12",
)
