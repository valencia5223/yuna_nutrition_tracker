import google.generativeai as genai
import os

# Use the key provided by the user in the prompt context (or env if set)
# I will use the one from the prompt for testing: AIzaSyC5WycguktOb3tDEvAOYqyFkDSRH2_acS0
api_key = "AIzaSyC5WycguktOb3tDEvAOYqyFkDSRH2_acS0"

try:
    genai.configure(api_key=api_key)
    print(f"Listing models for API Key ending in ...{api_key[-4:]}")
    models = genai.list_models()
    print("\nAvailable models:")
    for m in models:
        # Check if it supports generateContent
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name} (Supported methods: {m.supported_generation_methods})")
except Exception as e:
    print(f"\nError listing models: {e}")
