from flask import Flask, request, jsonify
import threading
import time
import requests
import re
import secrets
import random
import datetime
from hashlib import md5

app = Flask(__name__)

# Biến toàn cục để kiểm soát dừng các luồng và lưu trạng thái
current_stop_flag = threading.Event()
buff_status = {}  # Lưu trạng thái: {video_id: {"start_time": float, "initial_views": int, "target_seconds": int, "final_views": int or None, "completed": bool, "url": str}}

def get_tiktok_views(video_url):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    try:
        response = requests.get(video_url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None, f"Lỗi: Không truy cập được URL ({response.status_code})"
        
        html = response.text
        match = re.search(r'"playCount":(\d+)', html)
        if match:
            return int(match.group(1)), None
        else:
            return None, "Không tìm thấy lượt xem trong HTML."
    except Exception as e:
        return None, f"Lỗi: {str(e)}"

class Signature:
    def __init__(self, params: str, data: str, cookies: str) -> None:
        self.params = params
        self.data = data
        self.cookies = cookies

    def hash(self, data: str) -> str:
        return str(md5(data.encode()).hexdigest())

    def calc_gorgon(self) -> str:
        gorgon = self.hash(self.params)
        if self.data:
            gorgon += self.hash(self.data)
        else:
            gorgon += str("0"*32)
        if self.cookies:
            gorgon += self.hash(self.cookies)
        else:
            gorgon += str("0"*32)
        gorgon += str("0"*32)
        return gorgon

    def get_value(self):
        gorgon = self.calc_gorgon()
        return self.encrypt(gorgon)

    def encrypt(self, data: str):
        unix = int(time.time())
        len_val = 0x14
        key = [
            0xDF, 0x77, 0xB9, 0x40, 0xB9, 0x9B, 0x84, 0x83,
            0xD1, 0xB9, 0xCB, 0xD1, 0xF7, 0xC2, 0xB9, 0x85,
            0xC3, 0xD0, 0xFB, 0xC3,
        ]

        param_list = []
        for i in range(0, 12, 4):
            temp = data[8 * i : 8 * (i + 1)]
            for j in range(4):
                H = int(temp[j * 2 : (j + 1) * 2], 16)
                param_list.append(H)

        param_list.extend([0x0, 0x6, 0xB, 0x1C])
        H = int(hex(unix), 16)
        param_list.append((H & 0xFF000000) >> 24)
        param_list.append((H & 0x00FF0000) >> 16)
        param_list.append((H & 0x0000FF00) >> 8)
        param_list.append((H & 0x000000FF) >> 0)

        eor_result_list = []
        for A, B in zip(param_list, key):
            eor_result_list.append(A ^ B)

        for i in range(len_val):
            C = self.reverse(eor_result_list[i])
            D = eor_result_list[(i + 1) % len_val]
            E = C ^ D
            F = self.rbit(E)
            H = ((F ^ 0xFFFFFFFF) ^ len_val) & 0xFF
            eor_result_list[i] = H

        result = ""
        for param in eor_result_list:
            result += self.hex_string(param)

        return {"X-Gorgon": ("840280416000" + result), "X-Khronos": str(unix)}

    def rbit(self, num):
        result = ""
        tmp_string = bin(num)[2:]
        while len(tmp_string) < 8:
            tmp_string = "0" + tmp_string
        for i in range(0, 8):
            result = result + tmp_string[7 - i]
        return int(result, 2)

    def hex_string(self, num):
        tmp_string = hex(num)[2:]
        if len(tmp_string) < 2:
            tmp_string = "0" + tmp_string
        return tmp_string

    def reverse(self, num):
        tmp_string = self.hex_string(num)
        return int(tmp_string[1:] + tmp_string[:1], 16)

def send_view_thread(video_id: str):
    url_view = 'https://api16-core-c-alisg.tiktokv.com/aweme/v1/aweme/stats/?ac=WIFI&op_region=VN'
    sig = Signature(params='', data='', cookies='').get_value()
    while not current_stop_flag.is_set():
        random_hex = secrets.token_hex(16)
        headers_view = {
            'Host': 'api16-core-c-alisg.tiktokv.com',
            'Content-Length': '138',
            'Sdk-Version': '2',
            'Passport-Sdk-Version': '5.12.1',
            'X-Tt-Token': f'01{random_hex}0263ef2c096122cc1a97dec9cd12a6c75d81d3994668adfbb3ffca278855dd15c8056ad18161b26379bbf95d25d1f065abd5dd3a812f149ca11cf57e4b85ebac39d - 1.0.0',
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'TikTok 37.0.4 rv:174014 (iPhone; iOS 14.2; ar_SA@calendar=gregorian) Cronet',
            'X-Ss-Stub': '727D101256930EE8C1F61B112F038D96',
            'X-Tt-Store-Idc': 'alisg',
            'X-Tt-Store-Region': 'sa',
            'X-Ss-Dp': '1233',
            'X-Tt-Trace-Id': '00-33c8a619105fd09f13b65546057d04d1-33c8a619105fd09f-01',
            'Accept-Encoding': 'gzip, deflate',
            'X-Khronos': sig['X-Khronos'],
            'X-Gorgon': sig['X-Gorgon'],
            'X-Common-Params-V2': (
                "pass-region=1&pass-route=1"
                "&language=ar"
                "&version_code=17.4.0"
                "&app_name=musical_ly"
                "&vid=0F62BF08-8AD6-4A4D-A870-C098F5538A97"
                "&app_version=17.4.0"
                "&carrier_region=VN"
                "&channel=App%20Store"
                "&mcc_mnc=45201"
                "&device_id=6904193135771207173"
                "&tz_offset=25200"
                "&account_region=VN"
                "&sys_region=VN"
                "&aid=1233"
                "&residence=VN"
                "&screen_width=1125"
                "&uoo=1"
                "&openudid=c0c519b4e8148dec69410df9354e6035aa155095"
                "&os_api=18"
                "&os_version=14.2"
                "&app_language=ar"
                "&tz_name=Asia%2FHo_Chi_Minh"
                "¤t_region=VN"
                "&device_platform=iphone"
                "&build_number=174014"
                "&device_type=iPhone14,6"
                "&iid=6958149070179878658"
                "&idfa=00000000-0000-0000-0000-000000000000"
                "&locale=ar"
                "&cdid=D1D404AE-ABDF-4973-983C-CC723EA69906"
                "&content_language="
            ),
        }
        cookie_view = {'sessionid': random_hex}
        start = datetime.datetime(2020, 1, 1, 0, 0, 0)
        end = datetime.datetime(2024, 12, 31, 23, 59, 59)
        delta_seconds = int((end - start).total_seconds())
        random_offset = random.randint(0, delta_seconds)
        random_dt = start + datetime.timedelta(seconds=random_offset)
        data = {
            'action_time': int(time.time()),
            'aweme_type': 0,
            'first_install_time': int(random_dt.timestamp()),
            'item_id': video_id,
            'play_delta': 1,
            'tab_type': 4
        }
        try:
            r = requests.post(url_view, data=data, headers=headers_view, cookies=cookie_view, timeout=1)
            print(f"POST response status for video_id {video_id}: {r.status_code}")
            sig = Signature(params='ac=WIFI&op_region=VN', data=str(data), cookies=str(cookie_view)).get_value()
        except Exception as e:
            print(f"POST error for video_id {video_id}: {str(e)}")
            continue

@app.route('/buffviewtik', methods=['GET'])
def boost_tiktok():
    global current_stop_flag, buff_status
    current_stop_flag.clear()

    # Lấy tham số từ query string
    link = request.args.get('url')
    target_seconds = request.args.get('time')

    # Kiểm tra dữ liệu đầu vào
    if not link or not target_seconds:
        return jsonify({"status": "error", "message": "Thiếu url hoặc time"}), 400
    try:
        target_seconds = int(target_seconds)
        if target_seconds <= 0:
            raise ValueError("time phải là số nguyên dương")
        if target_seconds > 1000:
            target_seconds = 1000  # Giới hạn tối đa 1000 giây
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e) if str(e) != "time phải là số nguyên dương" else "time phải là số nguyên dương"}), 400

    # Kiểm tra ngầm lượt xem video và lấy số lượt xem ban đầu
    initial_views, error_message = get_tiktok_views(link)
    if initial_views is None:
        return jsonify({"status": "error", "message": error_message}), 400

    # Lấy ID video từ link
    headers_id = {
        'Connection': 'close',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
        'Accept': 'text/html'
    }
    try:
        page = requests.get(link, headers=headers_id, timeout=10).text
        match = re.search(r'"video":\{"id":"(\d+)"', page)
        if match:
            video_id = match.group(1)
            print(f"Extracted video_id in /buffviewtik: {video_id}")
        else:
            return jsonify({"status": "error", "message": "Không tìm thấy ID Video"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi khi lấy ID Video: {str(e)}"}), 500

    # Lưu trạng thái
    buff_status[video_id] = {
        "start_time": time.time(),
        "initial_views": initial_views,
        "target_seconds": target_seconds,
        "final_views": None,
        "completed": False,
        "url": link  # Lưu link TikTok để sử dụng trong /status
    }

    # Khởi tạo các luồng
    threads = []
    timer_thread = threading.Thread(target=lambda: (
        time.sleep(target_seconds),
        current_stop_flag.set(),
        buff_status[video_id].update({
            "final_views": get_tiktok_views(link)[0],
            "completed": True
        }),
        time.sleep(10),  # Giữ trạng thái thêm 5 phút
        buff_status.pop(video_id, None),  # Xóa trạng thái sau 5 phút
        print(f"Removed buff_status for video_id: {video_id}")
    ))
    timer_thread.daemon = True
    timer_thread.start()
    threads.append(timer_thread)

    for i in range(450):
        t = threading.Thread(target=send_view_thread, args=(video_id,))
        t.daemon = True
        t.start()
        threads.append(t)

    # Trả về phản hồi ngay lập tức
    return jsonify({
        "status": "success",
        "message": f"Đang chạy {target_seconds} giây cho {link}"
    })

@app.route('/status', methods=['GET'])
def get_status():
    link = request.args.get('url') or request.args.get('video')
    if not link:
        return jsonify({"status": "error", "message": "Thiếu url hoặc video"}), 400

    # Lấy ID video từ link
    headers_id = {
        'Connection': 'close',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36',
        'Accept': 'text/html'
    }
    try:
        page = requests.get(link, headers=headers_id, timeout=10).text
        match = re.search(r'"video":\{"id":"(\d+)"', page)
        if match:
            video_id = match.group(1)
            print(f"Extracted video_id in /status: {video_id}")
        else:
            return jsonify({"status": "error", "message": "Không tìm thấy ID Video"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": f"Lỗi khi lấy ID Video: {str(e)}"}), 500

    if video_id not in buff_status:
        return jsonify({"status": "error", "message": "Không tìm thấy trạng thái buff cho video này"}), 404

    status = buff_status[video_id]
    if not status["completed"]:
        elapsed_time = time.time() - status["start_time"]
        remaining_time = max(0, int(status["target_seconds"] - elapsed_time))
        return jsonify({
            "status": "success",
            "url": link,
            "remaining_time": remaining_time
        }, headers={"Cache-Control": "no-cache"})
    else:
        initial_views = status["initial_views"]
        final_views = status["final_views"]
        views_increase = final_views - initial_views if final_views is not None else None
        return jsonify({
            "status": "success",
            "message": f"Đã chạy đủ {status['target_seconds']} giây cho {status['url']}, dừng chạy!",
            "initial_views": initial_views,
            "views_increase": views_increase,
            "final_views": final_views
        }, headers={"Cache-Control": "no-cache"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
