import json
import re
import ast
import litellm

litellm.suppress_debug_info = True

def extract_json_from_text(text: str) -> dict | None:
    """AIが複数JSONを出力しても、最初の1つだけを確実に取り出す真のパーサー"""
    matches = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    
    if matches:
        json_str = matches[0]
    else:
        start_idx = text.find('{')
        if start_idx == -1:
            return None
            
        text_to_parse = text[start_idx:]
        try:
            decoder = json.JSONDecoder(strict=False)
            obj, _ = decoder.raw_decode(text_to_parse)
            return obj 
        except json.JSONDecodeError:
            end_idx = text.rfind('}')
            if end_idx == -1:
                return None
            json_str = text[start_idx:end_idx+1]

    try:
        return json.loads(json_str, strict=False)
    except json.JSONDecodeError:
        try:
            return ast.literal_eval(json_str)
        except (SyntaxError, ValueError):
            return None


def chat_with_llm(messages: list, model_name: str, provider: str = "ollama", is_ask_mode: bool = False) -> dict:
    """
    LiteLLMを使用して、あらゆるプロバイダー（Ollama, OpenAI, Anthropic等）と統一フォーマットで通信するFacade関数。
    """
    try:
        # LiteLLMのお作法: Ollama等ローカルの場合は "ollama/モデル名" のように指定する
        # OpenAIの場合はそのまま "gpt-4o" 等で動くが、統一のために openai/gpt-4o の形にしてもOK
        litellm_model = f"{provider}/{model_name}" if provider != "openai" else model_name

        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=0.1 
        )
        
        # どのプロバイダーを使っても、OpenAIと同じ形で結果が返ってくる
        raw_content = response.choices[0].message.content
        
        # 会話モードならパースせずにそのまま返す
        if is_ask_mode:
            return {"raw_response": raw_content}

        # JSONを抽出
        parsed_data = extract_json_from_text(raw_content)
        
        if parsed_data:
            return parsed_data
        else:
            return {
                "error": "JSON_PARSE_ERROR",
                "raw_response": raw_content
            }
            
    except Exception as e:
        return {
            "error": "LLM_CONNECTION_ERROR",
            "raw_response": f"LLMとの通信に失敗しました。\nモデル: {provider}/{model_name}\n詳細: {str(e)}"
        }


def stream_chat_with_llm(messages: list, model_name: str, provider: str = "ollama"):
    """
    /askモード専用: LLMのレスポンスをストリーミングで返すジェネレータ関数。
    各チャンクのテキストを逐次 yield する。
    """
    try:
        litellm_model = f"{provider}/{model_name}" if provider != "openai" else model_name
        
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            temperature=0.1,
            stream=True
        )
        
        for chunk in response:
            content = chunk.choices[0].delta.content
            if content:
                yield content
                
    except Exception as e:
        yield f"\n\nストリーミング中にエラーが発生しました: {e}"


def estimate_tokens(messages: list) -> int:
    """
    メッセージリストの概算トークン数を返す。
    日本語は1文字≈1.5トークン、英語は4文字≈1トークンの簡易推定。
    """
    import re
    total_tokens = 0
    for m in messages:
        content = m.get("content", "")
        # 日本語文字（ひらがな、カタカナ、漢字）をカウント
        ja_chars = len(re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF]', content))
        en_chars = len(content) - ja_chars
        total_tokens += int(ja_chars * 1.5) + int(en_chars / 4)
    return total_tokens