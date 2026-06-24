import json
from typing import Any, Optional, Protocol

import httpx

from app.config import Settings


class Classifier(Protocol):
    def classify(self, text: str, categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ...


def normalize_classifier_results(raw_items: list[dict[str, Any]], categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_slug = {str(category["slug"]): category for category in categories}
    seen: set[str] = set()
    results = []
    for item in raw_items:
        slug = str(item.get("slug") or "").strip()
        if slug not in by_slug or slug in seen:
            continue
        confidence = item.get("confidence", 0.5)
        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            confidence = 0.5
        confidence = min(max(confidence, 0.0), 1.0)
        category = by_slug[slug]
        results.append(
            {
                "category_id": category["id"],
                "slug": slug,
                "confidence": confidence,
                "method": "auto",
            }
        )
        seen.add(slug)
    return results


class LocalTaxonomyClassifier:
    def classify(self, text: str, categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        lowered = text.lower()
        raw_items = []
        for category in categories:
            slug = str(category.get("slug") or "")
            name = str(category.get("name") or "")
            slug_text = slug.replace("-", " ")
            if slug and (slug in lowered or slug_text in lowered or name.lower() in lowered):
                raw_items.append({"slug": slug, "confidence": 0.5})
        if not raw_items and any(category.get("slug") == "methods" for category in categories):
            raw_items.append({"slug": "methods", "confidence": 0.5})
        return normalize_classifier_results(raw_items, categories)


class OpenAICompatibleClassifier:
    def __init__(self, api_key: str, base_url: str, model: str, transport: Optional[httpx.BaseTransport] = None):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.transport = transport

    def classify(self, text: str, categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
        taxonomy = [
            {
                "slug": category.get("slug"),
                "name": category.get("name"),
                "description": category.get("description"),
            }
            for category in categories
        ]
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify the paper into zero or more registered taxonomy categories. "
                        "Return only compact JSON with shape "
                        '{"categories":[{"slug":"registered-slug","confidence":0.0}]}. '
                        "Do not invent slugs outside the taxonomy."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Taxonomy: {json.dumps(taxonomy, ensure_ascii=False)}\n\nPaper:\n{text}",
                },
            ],
            "temperature": 0,
        }
        with httpx.Client(transport=self.transport, timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        data = json.loads(strip_json_fence(content))
        raw_items = data.get("categories") or []
        if not isinstance(raw_items, list):
            raw_items = []
        return normalize_classifier_results(raw_items, categories)


def strip_json_fence(value: str) -> str:
    text = value.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def get_classifier(settings: Settings) -> Classifier:
    if settings.llm_api_key:
        return OpenAICompatibleClassifier(settings.llm_api_key, settings.llm_base_url, settings.llm_model)
    return LocalTaxonomyClassifier()
