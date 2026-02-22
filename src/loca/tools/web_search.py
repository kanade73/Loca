from ddgs import DDGS

def search_web(query: str, max_results: int = 3) -> str:
    """
    DuckDuckGoを使用してWeb検索を行い、結果を文字列で返す。
    AIが最新の情報を取得するために使用する。
    """
    try:
        results = DDGS().text(query, max_results=max_results)
        
        if not results:
            return f"検索結果が見つかりませんでした: '{query}'"
            
        formatted_results = f"Web Search Results for '{query}':\n\n"
        for i, res in enumerate(results, 1):
            title = res.get('title', 'No Title')
            href = res.get('href', 'No URL')
            body = res.get('body', 'No Description')
            
            formatted_results += f"{i}. {title}\n"
            formatted_results += f"   URL: {href}\n"
            formatted_results += f"   Snippet: {body}\n\n"
            
        return formatted_results.strip()
        
    except Exception as e:
        return f"検索中にエラーが発生しました: {e}"

# --- テスト用 ---
if __name__ == "__main__":
    print(search_web("uv python package manager"))