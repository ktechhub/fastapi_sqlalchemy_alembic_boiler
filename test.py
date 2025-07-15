# import openai

# client = openai.OpenAI(
#     base_url="https://ollama.v2.mediatranscribe.com/v1",
#     api_key="ollama",  # Dummy key
# )

# stream = client.chat.completions.create(
#     model="gemma:2b",
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "Explain what blockchain is in simple terms."},
#     ],
#     stream=True,
# )

# full_response = ""
# for chunk in stream:
#     content = chunk.choices[0].delta.content or ""
#     full_response += content
#     print(content, end="", flush=True)

# print("\n\nAssistant:", full_response)


# import openai

# client = openai.OpenAI(
#     base_url="https://ollama.v2.mediatranscribe.com/v1",
#     api_key="ollama",
# )

# stream = client.chat.completions.create(
#     model="gemma:2b",
#     messages=[
#         {
#             "role": "system",
#             "content": (
#                 "You are a helpful assistant. Always respond only in the following JSON format:\n\n"
#                 "{\n"
#                 '  "concept": "<short summary>",\n'
#                 '  "analogy": "<analogy anyone can understand>",\n'
#                 '  "keywords": ["<keyword1>", "<keyword2>", "<keyword3>"]\n'
#                 "}\n"
#                 "Only output valid JSON, nothing else."
#             ),
#         },
#         {
#             "role": "user",
#             "content": "Explain blockchain in simple terms.",
#         },
#     ],
#     stream=True,
# )

# full_response = ""
# for chunk in stream:
#     content = chunk.choices[0].delta.content or ""
#     full_response += content
#     print(content, end="", flush=True)

# print("\n\nParsed JSON response:")
# import json

# try:
#     parsed = json.loads(full_response)
#     print(json.dumps(parsed, indent=2))
# except json.JSONDecodeError as e:
#     print("\n❌ Invalid JSON response:", e)


# {
#   "concept": "A distributed ledger of transactions",
#   "analogy": "Think of a library where everyone has copies of a book, but the books are stored in different locations.",
#   "keywords": ["blockchain", "distributed ledger", "transactions"]
# }

# Parsed JSON response:
# {
#   "concept": "A distributed ledger of transactions",
#   "analogy": "Think of a library where everyone has copies of a book, but the books are stored in different locations.",
#   "keywords": [
#     "blockchain",
#     "distributed ledger",
#     "transactions"
#   ]
# }
