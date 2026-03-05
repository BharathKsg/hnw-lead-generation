"""
lib/llm.py
──────────
Azure OpenAI analyser for HNW lead extraction.
"""

import json
import logging
from openai import AzureOpenAI
from config.settings import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_DEPLOYMENT,
    AZURE_OPENAI_API_VERSION,
)

logger = logging.getLogger(__name__)



client = AzureOpenAI(
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            api_version=AZURE_OPENAI_API_VERSION,
        )

response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user",   "content": "Hi"},
                ],
                temperature=0.1,
            )
raw = response.choices[0].message.content.strip()
print(raw)
