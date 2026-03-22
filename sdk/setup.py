from setuptools import setup, find_packages

setup(
    name="context-clutch",
    version="0.1.0",
    description="Enterprise API Gateway & Sandbox Proxy to protect LLM context windows.",
    author="Scott Guida",
    packages=find_packages(),
    install_requires=[
        "httpx>=0.20.0"
    ],
    python_requires=">=3.8",
)
