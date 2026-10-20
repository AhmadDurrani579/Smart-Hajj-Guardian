from app.services.gemini_service import GeminiService

gemini = GeminiService()

response = gemini.generate(
    "Reply with: Smart Hajj Guardian Gemini connection successful."
)

print(response)