def extract_json(text):
    start = text.find("{")
    if start == -1:
        return None

    stack = 0

    for i in range(start, len(text)):
        if text[i] == "{":
            stack += 1
        elif text[i] == "}":
            stack -= 1

        if stack == 0:
            return text[start:i + 1]

    return None
