import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def extract_from_pdf(path="files/demo4.pdf"):
    file = client.files.create(
        file=open(path, "rb"),
        purpose="user_data"
    )

    try:
        response = client.responses.create(
            model="gpt-5",
            input=[
            {
                "role": "user",
                "content": [
                {
                    "type": "input_file",
                    "file_id": file.id,
                },
                {
                    "type": "input_text",
                    "text": (
                    "Extract all menu items from this restaurant menu PDF and output each item in the following JSON format:\n"
                    '{\n  "item_name": <name>,\n  "status": <available/unavailable>,\n  "descriptions": <description>,\n  "image": null,\n  "category": <category>,\n  "price": <price>,\n  "discount": <discount_percent>,\n  "preparation_time": <hh:mm:ss>\n}\n'
                    "Return a list of such JSON objects for all items found.\n"
                    "If values are in other languages, keep them as is following the json format."
                    "If any fields are missing, please keep them null. "
                    "If OCR is not possible, generate a JSON file with an empty list []. "
                    "NEVER ADD ANY text other than the JSON output."
                    ),
                },
                ]
            }
            ],
            reasoning={"effort": "low"}
        )

        return response.output_text
    
    except Exception as e:
        raise RuntimeError(f"Failed to extract from PDF: {e}")
        