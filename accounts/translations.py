from django.conf import settings
import deepl

auth_key = "4cf43b39-44aa-4ade-ba2c-05d21de0c9a6:fx"

translator = deepl.Translator(auth_key)


def translate_text(text, target_lang):
    try:
        if target_lang.upper() == "EN":
            target_lang = "EN-US"
        result = translator.translate_text(text, target_lang=target_lang.upper())
        return result.text
    except Exception as e:
        return f"Error: {e}"
    