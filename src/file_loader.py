from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PROMPTS_DIR = BASE_DIR / "prompts"


def load_prompt(filename="classifier_prompt.txt"):
    """
    Loads a prompt file from the prompts folder.
    """

    prompt_path = PROMPTS_DIR / filename

    with open(prompt_path, "r", encoding="utf-8") as file:
        return file.read()


def load_email():
    with open("sample_email.txt", "r", encoding="utf-8") as file:
        return file.read()