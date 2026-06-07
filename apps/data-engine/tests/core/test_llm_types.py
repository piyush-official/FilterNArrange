from filternarrange_engine.core.llm import (
    AICapability,
    AIInput,
    AIOutput,
    JsonSchema,
    LLMError,
    LLMProvider,
    LLMTimeoutError,
    SchemaValidationError,
    Vector,
)


def test_protocol_is_runtime_checkable():
    assert hasattr(LLMProvider, "_is_runtime_protocol")
    assert "name" in AICapability.__annotations__
    assert "run" in AICapability.__dict__


def test_ai_input_output_carry_payload_and_result():
    inp = AIInput(capability="auto_summary", payload={"foo": 1})
    assert inp.payload == {"foo": 1}
    out = AIOutput(capability="auto_summary", result={"summary": "ok"})
    assert out.result == {"summary": "ok"}
    assert out.cache_hit is False


def test_error_hierarchy():
    assert issubclass(LLMError, Exception)
    assert issubclass(SchemaValidationError, LLMError)
    assert issubclass(LLMTimeoutError, LLMError)


def test_vector_alias():
    v: Vector = [0.1, 0.2, 0.3]
    assert isinstance(v, list)


def test_json_schema_is_mapping():
    s: JsonSchema = {"type": "object"}
    assert s["type"] == "object"
