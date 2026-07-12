from setuptools import setup, find_packages

setup(
    name="devorbit-cli",
    version="2.1.0b2",
    description="A multi-provider coding CLI with developer diagnostics, GitHub, MCP, research, and browser automation",
    packages=find_packages(include=["acli", "acli.*"]),
    install_requires=[
        "openai>=1.40.0",
        "python-dotenv>=1.0.1",
        "rich>=13.7.1",
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "playwright>=1.45.0",
        "pypdf>=4.0.0",
        "python-docx>=1.1.0",
        "python-pptx>=0.6.23",
        "openpyxl>=3.1.0",
        "Pillow>=10.0.0",
        "pytesseract>=0.3.10",
        "keyring>=25.0.0",
        "fastapi>=0.115.0",
        "uvicorn>=0.30.0",
        "websockets>=12.0",
    ],
    entry_points={
        "console_scripts": [
            "devorbit=acli.main:main",
            "acli=acli.main:main",
            "devorbit-desktop=acli.desktop.launch:main",
        ],
    },
    python_requires=">=3.9",
)
