import requests

try:
    res = requests.get("http://127.0.0.1:8080/profiles")
    if res.status_code == 200:
        profiles = res.json()
        for p in profiles:
            if p["name"] == "847040":
                print("FOUND UUID:", p["id"])
                break
        else:
            print("PROFILE 847040 NOT FOUND")
    else:
        print("API ERROR:", res.status_code)
except Exception as e:
    print("ERR:", e)
