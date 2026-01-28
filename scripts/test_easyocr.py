try:
    import easyocr
    print("Init strict order...")
    reader = easyocr.Reader(['ch_tra', 'en'], gpu=False)
    print("Success ch_tra, en")
except Exception as e:
    print(f"Failed ch_tra, en: {e}")

try:
    print("Init en, ch_tra...")
    reader = easyocr.Reader(['en', 'ch_tra'], gpu=False)
    print("Success en, ch_tra")
except Exception as e:
    print(f"Failed en, ch_tra: {e}")
