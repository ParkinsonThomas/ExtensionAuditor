from llama_cpp import Llama
import time

start_time = time.time()

llm = Llama(model_path="/mnt/c/Users/tpark/llama.cpp/models/codellama-13b.Q4_K_S.gguf", n_ctx=2048, verbose=False)

response = llm.create_completion(prompt="What is 2 + 2?", max_tokens = 25)
end_time = time.time()

print(response)

print("")

elapsed_time = end_time - start_time
print(f"Execution time: {elapsed_time:.6f} seconds")

