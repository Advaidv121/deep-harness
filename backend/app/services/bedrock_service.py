import json
import asyncio
from typing import AsyncGenerator, List, Dict, Any, Optional
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from backend.app.config import get_settings

settings = get_settings()

class BedrockService:
    """
    AWS Bedrock Runtime wrapper — verified against my-second-account (273366118212, us-east-1).
    Chat: converse + converse_stream (inference profiles required for Llama 3.3/4).
    Embed: Titan v2 (Cohere blocked — marketplace payment instrument needed).
    """
    def __init__(self):
        self.region = settings.AWS_REGION
        self.profile = settings.AWS_PROFILE
        self.chat_model = settings.BEDROCK_CHAT_MODEL_ID  # us.meta.llama3-3-70b-instruct-v1:0
        self.fallback_model = settings.BEDROCK_FALLBACK_MODEL_ID
        self.embed_model = settings.BEDROCK_EMBED_MODEL_ID
        self._rt = None  # lazy

    def _client(self):
        if self._rt is None:
            session = boto3.Session(profile_name=self.profile) if self.profile else boto3.Session()
            self._rt = session.client("bedrock-runtime", region_name=self.region)
        return self._rt

    def _to_converse_messages(self, messages: List[Dict[str, str]]) -> tuple[Optional[str], List[Dict]]:
        system_text = None
        converse_msgs = []
        for m in messages:
            role = m.get("role")
            content = m.get("content", "")
            if role == "system":
                # Bedrock system is separate param; concat if multiple
                system_text = (system_text + "\n" + content) if system_text else content
            elif role in ("user", "assistant"):
                converse_msgs.append({"role": role, "content": [{"text": content}]})
        return system_text, converse_msgs

    async def stream_chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 1024) -> AsyncGenerator[str, None]:
        system_text, converse_msgs = self._to_converse_messages(messages)
        # boto3 is sync — run in thread, bridge to async generator
        loop = asyncio.get_running_loop()
        model_to_try = [self.chat_model, self.fallback_model]
        last_err = None
        for mid in model_to_try:
            try:
                call_kwargs = {"modelId": mid, "messages": converse_msgs, "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature}}
                if system_text:
                    call_kwargs["system"] = [{"text": system_text}]
                response = await loop.run_in_executor(None, lambda k=call_kwargs: self._client().converse_stream(**k))
                stream = response.get("stream")
                if stream is None:
                    continue
                for event in stream:
                    if "contentBlockDelta" in event:
                        delta = event["contentBlockDelta"]["delta"].get("text", "")
                        if delta:
                            yield delta
                    elif "messageStop" in event:
                        break
                return
            except (ClientError, BotoCoreError) as e:
                last_err = e
                # try fallback model
                continue
        # if all fail, raise so caller falls back to local
        if last_err:
            raise last_err

    async def invoke_chat(self, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 1024) -> str:
        system_text, converse_msgs = self._to_converse_messages(messages)
        loop = asyncio.get_running_loop()
        for mid in [self.chat_model, self.fallback_model]:
            try:
                kwargs = {"modelId": mid, "messages": converse_msgs, "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature}}
                if system_text:
                    kwargs["system"] = [{"text": system_text}]
                resp = await loop.run_in_executor(None, lambda k=kwargs: self._client().converse(**k))
                return resp["output"]["message"]["content"][0]["text"]
            except (ClientError, BotoCoreError):
                continue
        raise RuntimeError("Bedrock converse failed on all models")

    def embed_sync(self, text: str, normalize: bool = True) -> Optional[list]:
        """Sync Titan v2 embed — 1024d. Returns list[float] or None."""
        if not text or not text.strip():
            return None
        try:
            body = json.dumps({"inputText": text, "dimensions": settings.BEDROCK_EMBED_DIMENSION, "normalize": normalize})
            resp = self._client().invoke_model(
                modelId=self.embed_model, body=body, contentType="application/json", accept="application/json"
            )
            data = json.loads(resp["body"].read())
            vec = data.get("embedding")
            if vec:
                return vec
        except Exception:
            pass
        return None

    async def embed(self, text: str) -> Optional[list]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self.embed_sync(text))

bedrock_service = BedrockService()
