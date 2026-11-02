"""Build the provider's strict structural schema; validate full contracts locally."""

import copy

from pydantic import BaseModel


def structured_schema(schema: type[BaseModel]) -> dict:
    """Strip validation-only keywords; retain types, refs, enums and nullability.

    All properties become required (nullable defaults stay nullable). Defaults
    are removed. Local Pydantic and Quality Gate checks retain all constraints.
    """
    result = copy.deepcopy(schema.model_json_schema())
    local_only = {"default", "title", "minLength", "maxLength", "pattern", "minimum", "maximum",
                  "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minItems", "maxItems"}
    def visit(node: object) -> None:
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            for key in tuple(node):
                if key in local_only:
                    node.pop(key)
            if node.get("type") == "object":
                node["additionalProperties"] = False
                node["required"] = list(node.get("properties", {}))
            for key in ("properties", "$defs"):
                for value in node.get(key, {}).values():
                    visit(value)
            for key in ("items", "anyOf", "oneOf", "allOf", "additionalProperties"):
                if key in node:
                    visit(node[key])
    visit(result)
    return result
