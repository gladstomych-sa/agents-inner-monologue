"""ChatOpenAI that keeps the proxy's `reasoning_content`.

langchain-openai deliberately drops non-OpenAI fields, so through LiteLLM the model's
thinking never reaches the Adrian SDK. This lifts it into `additional_kwargs["reasoning"]`,
which `adrian.handler._extract_reasoning` reads. Use in place of ChatOpenAI; nothing else changes.
"""
from langchain_openai import ChatOpenAI


class ReasoningChatOpenAI(ChatOpenAI):
    def _create_chat_result(self, response, generation_info=None):
        result = super()._create_chat_result(response, generation_info)
        try:
            rc = (response.choices[0].message.model_extra or {}).get("reasoning_content")
            if rc:
                result.generations[0].message.additional_kwargs["reasoning"] = rc
        except (AttributeError, IndexError):
            pass
        return result


if __name__ == "__main__":  # self-check, no network
    from openai.types.chat import ChatCompletion
    cc = ChatCompletion.model_validate({"id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": "hi", "reasoning_content": "because"}}]})
    m = ReasoningChatOpenAI(model="m", api_key="k")._create_chat_result(cc).generations[0].message
    assert m.additional_kwargs["reasoning"] == "because", m.additional_kwargs
    print("ok")
