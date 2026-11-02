"""Pure Gemini JSON-schema projection; full local contracts remain mandatory."""

from storyforge.domain.base import Contract
from storyforge.llm.schema import structured_schema


def gemini_schema(model: type[Contract]) -> dict:
    schema = structured_schema(model)

    def visit(node):
        if not isinstance(node, dict):
            return
        if "const" in node:
            node["enum"] = [node.pop("const")]
        for keyword in ("properties", "$defs"):
            for child in node.get(keyword, {}).values():
                visit(child)
        for keyword in ("items", "additionalProperties"):
            visit(node.get(keyword))
        for keyword in ("anyOf", "allOf", "oneOf"):
            for child in node.get(keyword, []):
                visit(child)

    visit(schema)
    return schema
