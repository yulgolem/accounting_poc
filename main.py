
import os
import base64
import requests
import json
import random
import fitz  # PyMuPDF
import io
import re

# --- Configuration ---
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MODEL_NAME = os.environ.get("MODEL_NAME")
INPUT_DIR = "examples"
OUTPUT_DIR = "results"
PROMPT_FILE = "prompt.txt"
PLAN_FILE = "plan.json"
OUTPUT_FORMAT_FILE = "output_format.json"

# --- Functions ---

def encode_image(image_path):
    """Encodes an image file (or the first page of a PDF) to base64."""
    file_extension = os.path.splitext(image_path)[1].lower()

    if file_extension == '.pdf':
        try:
            doc = fitz.open(image_path)
            page = doc.load_page(0)  # Load the first page
            pix = page.get_pixmap()  # Render page to an image
            png_data = pix.tobytes("png") # Get PNG data as bytes
            img_byte_arr = io.BytesIO(png_data)
            return base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        except Exception as e:
            print(f"Error processing PDF: {e}")
            return None
    else:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

def get_system_prompt():
    """Reads the system prompt from the prompt file."""
    with open(PROMPT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def get_plan():
    """Reads the plan of accounts from the plan file."""
    with open(PLAN_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def get_output_format():
    """Reads the desired output JSON format from the output_format file."""
    with open(OUTPUT_FORMAT_FILE, 'r', encoding='utf-8') as f:
        return f.read()

def analyze_document(file_path):
    """
    Analyzes a document (PDF or image) using the OpenRouter API.
    """
    print(f"Analyzing file: {file_path}")

    file_size_bytes = os.path.getsize(file_path)
    print(f"File size: {file_size_bytes / (1024 * 1024):.2f} MB")

    base64_content = encode_image(file_path)
    if base64_content is None:
        print(f"Failed to encode file: {file_path}")
        return None

    system_prompt = get_system_prompt()
    plan = get_plan()
    output_format = get_output_format()

    # Determine the content type based on file extension
    # Now, if it was a PDF, it's converted to PNG, so we always send image/png for converted PDFs
    file_extension = os.path.splitext(file_path)[1].lower()
    if file_extension == '.pdf':
        content_type = "image/png" # PDF is converted to PNG
    elif file_extension == '.png':
        content_type = "image/png"
    elif file_extension in ('.jpg', '.jpeg'):
        content_type = "image/jpeg"
    else:
        raise ValueError(f"Unsupported file type: {file_extension}")

    image_url_data = f"data:{content_type};base64,{base64_content}"

    # Construct the user prompt
    user_prompt = f"""Проанализируй следующий первичный документ и преобразуй его в проводки по главной книге. Отдай только JSON.

**План счетов:**
{plan}

**Рекомендации по учету:**

* **Использование аналитических счетов:** Всегда стремись использовать наиболее специфичные и подходящие счета из предоставленного плана счетов, а не только универсальные. Например, для операций с ЕС используй `5330` вместо общего `5310`, если он доступен.
* **Учет НДС по входящим счетам:** Для входящих счетов с НДС, если это требуется по методике (т.е., если НДС не включается в стоимость актива/расхода, а подлежит возмещению/зачету), **разбивай сумму на сумму без НДС и сумму НДС**. Сумму без НДС относи на соответствующий расходный или активный счет, а сумму НДС — на счет `57221` (PVN kreditori - pamatlikme). Если документ содержит обратный НДС, проводки должны отражать налоговую базу на соответствующих счетах расходов/активов и обязательство по НДС на счетах НДС, согласно латвийскому законодательству об обратном НДС.
* **Доходы и расходы по экспортным операциям и услугам:**
    * **Для доходов:** Вместо универсального `6110` (Ieņēmumi no pamatdarbības produkcijas un pakalpojumu pārdošanas), используй более специфичные счета, такие как `6221` (Ieņēmumi no preču pārdošanas 3.valstis) для продаж в третьи страны или `6220` (Ar nodokļiem apliekamie pārdošanas ieņēmumi) для облагаемых НДС продаж внутри ЕС/Латвии.
    * **Для расходов, связанных с экспортом/импортом услуг/товаров:** Используй наиболее подходящие счета, такие как `7170` (Samaksa par darbiem un pakalpojumiem), `7110` (Izejvielu un materiālu iepirkšanas un piegādes izdevumi) или другие специфичные счета из разделов 7ххх, избегая универсальных `7770` (Citi vadīšanas un administrācijas izdevumi) или `7710` (Sakaru izdevumi), если есть более точное соответствие.
* **Строгое соответствие:** Не фантазируй и не придумывай счета или проводки, которых нет в плане счетов или которые не соответствуют прямому смыслу документа. Если информация неоднозначна, используй поле 'Confidence_Score' для отражения неуверенности и, при необходимости, 'VAT_Reason' для пояснения ограничений.

**Формат вывода:**
Вывод должен быть строго в формате JSON. Каждый документ должен быть представлен как массив объектов JSON. Каждый объект в массиве должен представлять собой отдельную проводку.

```json
{output_format}
```
**Пример первичного документа для анализа:**
"""

    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            },
            data=json.dumps({
                "model": MODEL_NAME,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url_data
                                }
                            }
                        ]
                    }
                ]
            })
        )

        response.raise_for_status()  # Raise an exception for bad status codes
        response_json = response.json()
        generated_content = response_json['choices'][0]['message']['content']

        try:
            # Attempt to parse the generated content directly as JSON
            parsed_json = json.loads(generated_content)
            return parsed_json
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from markdown code block
            json_match = re.search(r'```json\n([\s\S]*?)\n```', generated_content)
            if json_match:
                json_string = json_match.group(1)
                try:
                    parsed_json = json.loads(json_string)
                    return parsed_json
                except json.JSONDecodeError:
                    print(f"Error: Extracted content is not valid JSON: {json_string}")
                    return None
            else:
                print(f"Error: No valid JSON or JSON markdown block found in generated content: {generated_content}")
                return None

    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        if e.response is not None:
            print(f"API Response: {e.response.text}")
        return None

import glob

def main():
    """
    Main function to provide an interactive menu for document analysis.
    """
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    while True:
        print("\nMenu:")
        print("1 - Analyze a random file")
        print("2 - Exit")

        choice = input("Enter your choice: ")

        if choice == '1':
            eligible_files = glob.glob(os.path.join(INPUT_DIR, "**", "*.*"), recursive=True)
            eligible_files = [f for f in eligible_files if f.lower().endswith(('.pdf', '.png', '.jpg', '.jpeg'))]

            if not eligible_files:
                print("No eligible files found to process.")
                continue

            file_path = random.choice(eligible_files)
            result = analyze_document(file_path)

            if result:
                print("\n--- Analysis Result ---")
                print(json.dumps(result, ensure_ascii=False, indent=4))
                print("-----------------------")

                # Save the result to a file
                filename = os.path.basename(file_path)
                output_filename = os.path.splitext(filename)[0] + ".json"
                output_path = os.path.join(OUTPUT_DIR, output_filename)
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(result, f, ensure_ascii=False, indent=4)
                print(f"Successfully saved result to {output_path}")
            else:
                print("Analysis failed.")

        elif choice == '2':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
