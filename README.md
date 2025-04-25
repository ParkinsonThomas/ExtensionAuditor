# ExtensionAuditor

# Setting up Llama.cpp LLM
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp

mkdir build
cd build
cmake ..
cmake --build . --config Release

wget https://huggingface.co/TheBloke/CodeLlama-7B-GGUF/resolve/main/codellama-7b.Q4_K_M.gguf