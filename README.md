# Keeps

This project provides an interactive command-line interface to analyze financial documents using the OpenRouter AI API.

## How it Works

The script presents an interactive menu, allowing the user to:

1.  **Analyze a random file:**
    *   Recursively scans the `examples` directory (and its subdirectories) to find all supported document files (`.pdf`, `.png`, `.jpg`, `.jpeg`).
    *   Selects one file at random from the discovered list.
    *   Encodes the chosen file into base64 format.
    *   Sends the file, along with a detailed system prompt (`prompt.txt`), a chart of accounts (`plan.json`), and a specified output format (`output_format.json`), to the OpenRouter API for analysis.
    *   Parses the JSON result received from the model, prints it directly to the console, and saves it as a JSON file in the `results` directory.
2.  **Exit:** Terminates the script.

## Setup

1.  **Create a `.env` file:** In the root of the project, create a file named `.env`.
2.  **Add your API Key and Model Name:** Add your OpenRouter API key and the desired model name to the `.env` file. The key should **not** be enclosed in quotes.

    ```
    OPENROUTER_API_KEY=your_actual_api_key_here
    MODEL_NAME=openai/gpt-4.1-mini
    ```

## Usage

To run the interactive script, use Docker Compose:

```bash
docker-compose run --rm app
```

This command will build the Docker image (if it doesn't exist or has changed) and run the container in an interactive mode, allowing you to choose options from the menu. The `--rm` flag ensures the container is removed after it exits.
