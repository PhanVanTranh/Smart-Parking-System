from flask import Flask, request, jsonify, render_template, send_file
import json
import os
from datetime import datetime
from openpyxl import Workbook
import firebase_admin
from firebase_admin import credentials, db

app = Flask(__name__)

DB_FILE = "database.json"
HISTORY_FILE = "history.json"
actions = []

# ===== 1. KẾT NỐI FIREBASE =====
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://smartparkingsystem-1e749-default-rtdb.asia-southeast1.firebasedatabase.app/'
})

# ===== LOAD/SAVE JSON LOCAL =====
def load_json(file_path, default):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default
    return default

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

database = load_json(DB_FILE, [])
history = load_json(HISTORY_FILE, [])

@app.route('/')
def home():
    return render_template("index.html", total=len(database), cars=database)

# ===== XE VÀO (CHỈ LƯU SỔ SÁCH, KHÔNG MỞ CỔNG) =====
@app.route('/car_in', methods=['POST'])
def car_in():
    data = request.get_json(silent=True) or {}
    plate = str(data.get("plate", "")).strip()
    if not plate: return jsonify({"status": "error", "message": "Thiếu biển số"}), 400

    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    
    # Nếu xe chưa có trong bãi thì thêm vào
    if plate not in [car["plate"] for car in database]:
        database.append({"plate": plate, "time_in": now})
        save_json(DB_FILE, database)
        
        history.append({"plate": plate, "time_in": now, "time_out": "", "status": "Trong bãi"})
        save_json(HISTORY_FILE, history)

    print(f"[KẾ TOÁN] Ghi nhận xe VÀO: {plate}")
    return jsonify({"status": "ok"})

# ===== XE RA (CHỈ LƯU SỔ SÁCH, KHÔNG MỞ CỔNG) =====
@app.route('/car_out', methods=['POST'])
def car_out():
    data = request.get_json(silent=True) or {}
    plate = str(data.get("plate", "")).strip()
    if not plate: return jsonify({"status": "error", "message": "Thiếu biển số"}), 400

    now = datetime.now().strftime("%H:%M:%S %d-%m-%Y")
    found = False
    
    for car in database:
        if car["plate"] == plate:
            database.remove(car)
            save_json(DB_FILE, database)
            
            # Tìm lượt vào gần nhất để ghi giờ ra
            for item in reversed(history):
                if item.get("plate") == plate and item.get("time_out", "") == "":
                    item["time_out"] = now
                    item["status"] = "Đã ra"
                    break
            save_json(HISTORY_FILE, history)
            found = True
            break
            
    if not found:
        history.append({"plate": plate, "time_in": "", "time_out": now, "status": "Từ chối"})
        save_json(HISTORY_FILE, history)

    print(f"[KẾ TOÁN] Ghi nhận xe RA: {plate}")
    return jsonify({"status": "ok"})

# ===== ĐIỀU KHIỂN THỦ CÔNG (TÁC ĐỘNG LÊN FIREBASE ĐỂ ESP32 NHẬN LỆNH) =====
@app.route('/manual_open_in')
def manual_open_in():
    db.reference('ParkingSystem/GateControl/EntryGate').update({"servo": "open", "manual": 1})
    return jsonify({"status": "ok", "message": "Đã mở cổng vào thủ công"})

@app.route('/manual_close_in')
def manual_close_in():
    db.reference('ParkingSystem/GateControl/EntryGate').update({"servo": "close", "manual": 0})
    return jsonify({"status": "ok", "message": "Đã đóng cổng vào thủ công"})

@app.route('/manual_open_out')
def manual_open_out():
    db.reference('ParkingSystem/GateControl/ExitGate').update({"servo": "open", "manual": 1})
    return jsonify({"status": "ok", "message": "Đã mở cổng ra thủ công"})

@app.route('/manual_close_out')
def manual_close_out():
    db.reference('ParkingSystem/GateControl/ExitGate').update({"servo": "close", "manual": 0})
    return jsonify({"status": "ok", "message": "Đã đóng cổng ra thủ công"})

# ===== CÁC HÀM PHỤ TRỢ (LẤY DANH SÁCH, LỊCH SỬ, EXPORT) =====
@app.route('/list')
def list_car():
    return jsonify({"total": len(database), "cars": database})

@app.route('/history')
def get_history():
    keyword = request.args.get("plate", "").strip().lower()
    filtered = [i for i in history if keyword in i.get("plate", "").lower()] if keyword else history
    return jsonify({"total": len(filtered), "history": filtered[::-1]})

@app.route('/export_excel')
def export_excel():
    wb = Workbook()
    ws = wb.active
    ws.append(["STT", "Biển số xe", "Thời gian vào", "Thời gian ra", "Trạng thái"])
    for i, item in enumerate(history, start=1):
        ws.append([i, item.get("plate", ""), item.get("time_in", ""), item.get("time_out", ""), item.get("status", "")])
    file_name = "lich_su_bai_xe.xlsx"
    wb.save(file_name)
    return send_file(file_name, as_attachment=True)

# ===== RESET (LOCAL JSON + FIREBASE ĐỒNG BỘ) =====
@app.route('/reset')
def reset():
    # 1. Dọn sạch dữ liệu trên máy tính (Local JSON)
    database.clear()
    history.clear()
    actions.clear()

    save_json(DB_FILE, database)
    save_json(HISTORY_FILE, history)

    # 2. Reset toàn bộ cấu trúc trên Firebase (Trả cổng về close, dọn rác)
    try:
        db.reference('ParkingSystem').set({
            "CurrentVehicle": {
                "placeholder": {"license_plate": "---", "time_in": 0, "status": 0} 
            },
            "GateControl": {
                "action": "none",
                "EntryGate": {"ir_gate": 0, "servo": "close", "manual": 0},
                "ExitGate": {"ir_gate": 0, "servo": "close", "manual": 0}
            },
            "Sensors": {
                "Slots": {"slot1": 0, "slot2": 0, "slot3": 0, "slot4": 0},
                "Environment": {"fire1": 0, "fire2": 0, "light": 500, "flame_alert": False}
            },
            "History": {
                "Sample": {"license_plate": "30A-7666", "time_in": "00:00:00", "time_out": "", "status": "Dữ liệu mẫu"}
            }
        })
        print("[HỆ THỐNG] Đã reset đồng bộ Local và Firebase thành công!")
    except Exception as e:
        print("[LỖI] Không thể reset Firebase:", e)

    return jsonify({"status": "ok", "message": "Đã khôi phục toàn bộ hệ thống về mặc định!"})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)