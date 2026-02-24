from supabase import create_client, Client
import os

SUPABASE_URL = "https://iynwmytfroatvzhbkodf.supabase.co"
SUPABASE_KEY = "sb_publishable_xqDTA5Hv2qcXC9ACkKBcgg_W5FaD-yG"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

class SupabaseAPI:
    @staticmethod
    def get_system_config(config_name):
        res = supabase.table("system_configs").select("config_value").eq("config_name", config_name).single().execute()
        return res.data.get("config_value") if res.data else None

    @staticmethod
    def get_all_active_accounts():
        res = supabase.table("accounts").select("*").eq("active", True).execute()
        return res.data

    @staticmethod
    def get_account_by_id(tiktok_id):
        res = supabase.table("accounts").select("*").eq("tiktok_id", tiktok_id).single().execute()
        return res.data

    @staticmethod
    def update_channel_tracking(tiktok_id, channel_url, last_url, new_index):
        res = supabase.table("accounts").select("channels").eq("tiktok_id", tiktok_id).single().execute()
        channels = res.data.get("channels", [])
        updated = False
        for channel in channels:
            if channel.get("url") == channel_url:
                channel["last_video_url"] = last_url
                channel["video_index"] = new_index
                updated = True
                break
        if updated:
            supabase.table("accounts").update({"channels": channels}).eq("tiktok_id", tiktok_id).execute()
            return True
        return False

    @staticmethod
    def download_asset(bucket_name, storage_path, local_dir, file_name):
        if not file_name: return None
        try:
            os.makedirs(local_dir, exist_ok=True)
            local_path = os.path.join(local_dir, file_name)
            full_storage_path = f"{storage_path}/{file_name}"
            res = supabase.storage.from_(bucket_name).download(full_storage_path)
            with open(local_path, "wb") as f:
                f.write(res)
            return local_path
        except Exception as e:
            print(f"   ⚠️ Không thể tải {file_name} từ Supabase (Có thể file chưa có trên Storage): {e}")
            return os.path.join(local_dir, file_name)