# Hướng dẫn thêm action "save_facebook" vào Google Apps Script

## Bước 1: Mở Apps Script
Truy cập Google Sheet → Extensions → Apps Script
(hoặc mở link script trực tiếp)

## Bước 2: Tìm function doPost(e) trong code hiện tại

## Bước 3: Thêm đoạn code sau VÀO TRONG function doPost(e), trước dòng `return ...error..."Unknown action"`

```javascript
  // ═══════════════════════════════════════════════
  //  FACEBOOK NEWS PIPELINE
  // ═══════════════════════════════════════════════

  if (action === "save_facebook") {
    var sheetName = data.sheet_name || "facebook";
    var sheet = ss.getSheetByName(sheetName);
    
    // Tạo sheet "facebook" nếu chưa có
    if (!sheet) {
      sheet = ss.insertSheet(sheetName);
      sheet.getRange(1, 1, 1, 12).setValues([[
        "Link gốc",       // A
        "Hook",            // B
        "Title TikTok",    // C
        "Main Idea",       // D
        "Content Style",   // E
        "Duration (s)",    // F
        "Scenes",          // G
        "Source",           // H
        "Script Voice",    // I
        "Voice Link",      // J
        "Drive Link",      // K
        "Status"           // L
      ]]);
      // Bold header
      sheet.getRange(1, 1, 1, 12).setFontWeight("bold");
    }
    
    var lastRow = sheet.getLastRow() + 1;
    sheet.getRange(lastRow, 1).setValue(data.link || "");            // A: Link gốc
    sheet.getRange(lastRow, 2).setValue(data.hook || "");            // B: Hook
    sheet.getRange(lastRow, 3).setValue(data.title_tiktok || "");    // C: Title
    sheet.getRange(lastRow, 4).setValue(data.main_idea || "");       // D: Main Idea
    sheet.getRange(lastRow, 5).setValue(data.content_style || "");   // E: Content Style
    sheet.getRange(lastRow, 6).setValue(data.estimated_duration || 30); // F: Duration
    sheet.getRange(lastRow, 7).setValue(data.scenes || "");          // G: Scenes
    sheet.getRange(lastRow, 8).setValue(data.source_name || "");     // H: Source
    sheet.getRange(lastRow, 9).setValue(data.script_voice || "");    // I: Script Voice
    sheet.getRange(lastRow, 12).setValue("pending");                 // L: Status
    
    return ContentService.createTextOutput(
      JSON.stringify({status: "success", row: lastRow, sheet: sheetName})
    ).setMimeType(ContentService.MimeType.JSON);
  }

  // ═══ Cập nhật voice link ═══
  if (action === "update_fb_voice") {
    var sheetName = data.sheet_name || "facebook";
    var sheet = ss.getSheetByName(sheetName);
    if (sheet && data.row) {
      sheet.getRange(parseInt(data.row), 10).setValue(data.voice_link || ""); // J
      return ContentService.createTextOutput(
        JSON.stringify({status: "success"})
      ).setMimeType(ContentService.MimeType.JSON);
    }
  }

  // ═══ Cập nhật drive link ═══
  if (action === "update_fb_drive") {
    var sheetName = data.sheet_name || "facebook";
    var sheet = ss.getSheetByName(sheetName);
    if (sheet && data.row) {
      sheet.getRange(parseInt(data.row), 11).setValue(data.drive_link || ""); // K
      return ContentService.createTextOutput(
        JSON.stringify({status: "success"})
      ).setMimeType(ContentService.MimeType.JSON);
    }
  }

  // ═══ Cập nhật status ═══
  if (action === "update_fb_status") {
    var sheetName = data.sheet_name || "facebook";
    var sheet = ss.getSheetByName(sheetName);
    if (sheet && data.row) {
      sheet.getRange(parseInt(data.row), 12).setValue(data.status || ""); // L
      return ContentService.createTextOutput(
        JSON.stringify({status: "success"})
      ).setMimeType(ContentService.MimeType.JSON);
    }
  }
```

## Bước 4: Deploy lại
- Bấm "Triển khai" → "Quản lý triển khai"
- Bấm biểu tượng bút chỉnh sửa (✏️)
- Version → "Triển khai mới" 
- Bấm "Triển khai"

## Bước 5: Test lại
```bash
cd /home/giang-adsup/Documents/mannyAccount/fb-news-pipeline
source ../.venv/bin/activate
python3 test_sheet_upload.py
```
