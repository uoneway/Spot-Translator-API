def isKoreanIncluded(text):
    """
    Check whether the text have korean unicode or not
    https://arisri.tistory.com/267
    """

    for i in text:
        if (
            ord(i) > int("0x1100", 16)
            and ord(i) < int("0x11ff", 16)
            or ord(i) > int("0x3131", 16)
            and ord(i) < int("0x318e", 16)
            or ord(i) > int("0xa960", 16)
            and ord(i) < int("0xa97c", 16)
            or ord(i) > int("0xac00", 16)
            and ord(i) < int("0xd7a3", 16)
            or ord(i) > int("0xd7b0", 16)
            and ord(i) < int("0xd7fb", 16)
        ):
            return True

    return False
