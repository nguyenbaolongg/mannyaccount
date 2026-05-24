import sqlite3

db_path = "../Documents/voice/voiceHA_Long_Hung/data/voicebox.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Insert the profile if it doesn't exist
try:
    cursor.execute("""
        INSERT INTO profiles (id, name, language, voice_type, default_engine, rvc_model_path, rvc_index_path, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    """, ("847040", "847040_custom", "vi", "rvc", "viterbox", "voices/847040/model.pth", "voices/847040/model.index"))
    conn.commit()
    print("Inserted profile 847040 successfully!")
except sqlite3.IntegrityError as e:
    print("IntegrityError:", e)
except Exception as e:
    print("Error:", e)

conn.close()
