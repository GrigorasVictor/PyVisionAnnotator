import sys
import json
import traceback

def main():
    try:
        from llama_cpp import Llama
    except ImportError:
        print(json.dumps({"error": "Missing llama_cpp_python"}))
        sys.exit(1)

    try:
        req = json.loads(sys.stdin.read())
        model_path = req.get("model_path")
        messages = req.get("messages", [])
        n_ctx = req.get("n_ctx", 8192)
        n_tokens = req.get("max_tokens", 1500)
        temp = req.get("temperature", 0.8)
        top_p = req.get("top_p", 0.95)
        repeat_penalty = req.get("repeat_penalty", 1.05)

        llm = Llama(model_path=model_path, n_ctx=n_ctx, verbose=False)
        stream = llm.create_chat_completion(
            messages=messages,
            temperature=temp,
            top_p=top_p,
            max_tokens=n_tokens,
            repeat_penalty=repeat_penalty,
            stream=True,
        )

        for chunk in stream:
            delta = chunk["choices"][0].get("delta", {})
            token = delta.get("content", "")
            if token:
                print(json.dumps({"token": token}), flush=True)

    except Exception as e:
        err = f"{str(e)}\n{traceback.format_exc()}"
        print(json.dumps({"error": err}), flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

