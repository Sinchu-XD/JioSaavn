def clean(text):
    if not text:
        return ""
    return (
        text.replace("&quot;", "'")
        .replace("&amp;", "&")
        .replace("&#039;", "'")
    )
