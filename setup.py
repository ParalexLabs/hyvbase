from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="hyvbase",
    version="0.1.0",
    author="Mir Sakib",
    author_email="sakib@paralexlabs.com",
    description="An on chain agent framework utilizing distributed inference and memory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ParalexLabs/hyvbase",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    python_requires=">=3.8",
    install_requires=[
        "langchain>=0.1.0",
        "langchain-openai>=0.0.2",
        "openai>=1.1.0",
        "starknet-py>=0.18.0",
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "loguru>=0.7.0",
        "pydantic>=2.0.0",
        "vectrs>=0.1.0",
        "numpy>=1.21.0",
        "pydantic-settings>=2.0.0",
        "python-telegram-bot>=20.0",
        "tweepy>=4.12.0",
        "aiohttp>=3.9.0",
        "discord.py>=2.3.2",
        "python-linkedin>=4.1",
        "google-api-python-client>=2.0.0",
        "playwright>=1.40.0",
        "beautifulsoup4>=4.12.0",
        "wolframalpha>=5.0.0",
        "solders>=0.18.0",
        "solana>=0.30.2",
        "base58>=2.1.1"
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "black>=23.0.0",
            "isort>=5.0.0",
        ]
    },
) 