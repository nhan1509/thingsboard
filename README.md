# LAB 01 — Raspberry Pi 4 + ThingsBoard Cloud

> Hướng dẫn từ lắp mạch, cài Python trên Raspberry Pi, kết nối ThingsBoard Cloud, tạo Dashboard, widget điều khiển servo bằng RPC và cảnh báo nhiệt độ.  
> Phạm vi: **một Raspberry Pi 4**, DHT11, HC-SR04, servo SG90. Không cài ThingsBoard Server trên laptop.

## 1. Mục tiêu và luồng hoạt động

**Luồng telemetry:** DHT11 / HC-SR04 → Python trên Pi → MQTT TLS → ThingsBoard Cloud → Latest Telemetry → Dashboard/biểu đồ.

**Luồng điều khiển:** Nút RPC trên Dashboard → ThingsBoard gửi `setServoAngle` → Pi nhận MQTT → điều khiển SG90 → phản hồi RPC và gửi attribute `servoAngle`.

**Luồng cảnh báo:** Telemetry `temperature` → điều kiện `temperature > 30` trên ThingsBoard → tạo alarm `High Temperature`; khi `temperature <= 30` → xóa alarm theo rule.

Lưu ý: Rule Engine **chỉ tạo/xóa cảnh báo** trong bài này; servo do người dùng điều khiển qua Dashboard. `servoAngle` là **góc đã ra lệnh**, không phải góc được đo bằng encoder.

## 2. Phần cứng và đấu nối

### 2.1. Danh sách

- Raspberry Pi 4 (Raspberry Pi OS/Debian 13, đã có Internet và SSH).
- DHT11 module 3 chân (nếu dùng cảm biến DHT11 rời 4 chân, cần điện trở kéo lên DATA).
- HC-SR04; 1 điện trở **1 kΩ** và 1 điện trở **2 kΩ** để chia áp Echo.
- Servo SG90; nguồn **5 V riêng, đủ dòng**, dây nối chung GND với Pi.
- Breadboard, dây jumper.

### 2.2. Bảng chân BCM (khác với số chân vật lý)

| Thiết bị | Chân | Nối đến |
|---|---|---|
| DHT11 module | VCC | Pi 3.3 V, **pin vật lý 1** |
| DHT11 module | DATA | **GPIO4**, pin vật lý 7 |
| DHT11 module | GND | Pi GND, pin vật lý 6 |
| HC-SR04 | VCC | Pi 5 V, pin vật lý 2 |
| HC-SR04 | TRIG | **GPIO23**, pin vật lý 16 |
| HC-SR04 | ECHO | **Qua chia áp** đến **GPIO24**, pin vật lý 18 |
| HC-SR04 | GND | Pi GND, pin vật lý 14 |
| SG90 | Signal (cam/vàng) | **GPIO18**, pin vật lý 12 |
| SG90 | VCC (đỏ) | +5 V của **nguồn riêng** |
| SG90 | GND (nâu/đen) | GND nguồn riêng **và nối GND chung với Pi** |

**Mạch chia áp HC-SR04:**

```text
HC-SR04 ECHO (5 V)
        |
       1 kΩ
        |
        +---------------- GPIO24 (Pi)
        |
       2 kΩ
        |
       GND ---------------- GND Pi
```

Không nối ECHO 5 V trực tiếp vào GPIO Pi. Không nối +5 V của nguồn servo riêng vào GPIO hoặc nguồn 3.3 V Pi. Tắt nguồn trước khi đấu dây. Nếu servo rung, kiểm tra nguồn riêng và GND chung; PWM phần mềm cũng có thể gây rung.

## 3. Chuẩn bị ThingsBoard Cloud

1. Mở **https://thingsboard.cloud/entities/devices/all** và đăng nhập.
2. Vào **Entities → Devices** (tên menu có thể khác đôi chút theo giao diện).
3. Nhấn **Add device** / dấu `+` → đặt tên **RaspberryPi_Lab01** → lưu.
4. Mở thiết bị → **Credentials** / **Manage credentials** → lấy **Access Token**.
5. Giữ token bí mật. **Không đưa token vào ảnh chụp, GitHub hoặc slide**.

**Hostname của tài khoản này là `thingsboard.cloud`, không phải URL đầy đủ.**

## 4. Chuyển code lên Pi

Sau khi giải nén `thingsboard_lab01.zip` trên Windows, ví dụ thư mục:

`C:\Users\LENOVO\Desktop\thingsboard_lab01`

Trong **PowerShell Windows**:

```powershell
scp -r "C:\Users\LENOVO\Desktop\thingsboard_lab01" pi@192.168.137.144:/home/pi/
ssh pi@192.168.137.144
```

`192.168.137.144` chỉ là **ví dụ IP cũ**; thay bằng IP hiện tại của Pi. Nếu code đã nằm trên Pi, bỏ qua bước SCP.

## 5. Cài Python và thư viện trên Pi

Trong **terminal Raspberry Pi**:

```bash
cd ~/thingsboard_lab01
sudo apt update
sudo apt install -y python3-venv python3-dev python3-lgpio
python3 -m venv --system-site-packages .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
```

Kiểm tra import:

```bash
.venv/bin/python -c "import paho.mqtt.client, gpiozero, board, adafruit_dht; print('IMPORT OK')"
```

Nếu lỗi `lgpio`/`RPi.GPIO`, kiểm tra phiên bản Debian và môi trường venv; `--system-site-packages` cho phép dùng gói GPIO đã cài bằng apt. **Không** cài pip bằng `sudo` vào Python hệ thống.

### 5.1. Cấu hình `.env`

```bash
cp .env.example .env
nano .env
```

Sửa thành:

```dotenv
TB_HOST=thingsboard.cloud
TB_PORT=8883
TB_TOKEN=PASTE_YOUR_DEVICE_ACCESS_TOKEN_HERE
SEND_INTERVAL=2
```

Thay `PASTE_YOUR_DEVICE_ACCESS_TOKEN_HERE` bằng token thực. Không nhập `https://` vào `TB_HOST`. Cổng `8883` dùng MQTT qua TLS; Pi cần Internet và thời gian hệ thống đúng để xác thực chứng chỉ.

Lưu nano: `Ctrl+O` → Enter → `Ctrl+X`.

### 5.2. Khởi chạy

```bash
chmod +x run.sh
./run.sh
```

Terminal dự kiến:

```text
[MQTT] Connected to thingsboard.cloud
Lab01 started. Ctrl+C to exit.
[SENSOR] {'temperature': 29.0, 'humidity': 65.0, 'distance': 24.5}
```

Giá trị là **ví dụ**, không phải số đo thực tế. Dừng bằng `Ctrl+C`.

**Nếu không kết nối:** kiểm tra `TB_HOST`, token, Wi-Fi/Internet, ngày giờ Pi (`date`), DNS (`getent hosts thingsboard.cloud`) và kết nối TLS (`openssl s_client -connect thingsboard.cloud:8883 -servername thingsboard.cloud`). Không tắt xác thực TLS để chữa lỗi chứng chỉ.

## 6. Kiểm tra telemetry trên ThingsBoard

1. Để `./run.sh` chạy trên Pi.
2. Mở **Entities → Devices → RaspberryPi_Lab01**.
3. Chọn tab **Latest telemetry**.
4. Kiểm tra các key `temperature`, `humidity`, `distance` và thời điểm cập nhật.
5. Nếu DHT11 lỗi một chu kỳ, có thể chỉ thấy `distance`; kiểm tra log `[DHT11]` trên terminal.

JSON gửi bởi Pi có dạng:

```json
{"temperature":29.0,"humidity":65.0,"distance":24.5}
```

Topic MQTT: `v1/devices/me/telemetry`.

## 7. Tạo Dashboard giám sát

### 7.1. Tạo Dashboard

1. Vào **Dashboards** ở menu trái.
2. Chọn **Add dashboard** (hoặc dấu `+`).
3. Đặt tên **Raspberry Pi Lab01 Monitoring**.
4. Mở dashboard và chọn **Edit** (biểu tượng bút chì).
5. Chọn **Add widget** / **+**.

### 7.2. Thêm widget nhiệt độ

1. Trong thư viện widget, chọn nhóm phù hợp như **Cards**, **Latest values** hoặc **Digital gauges** (tên phụ thuộc phiên bản).
2. Chọn widget hiển thị **giá trị hiện tại** (Value card, Latest value, Digital gauge...).
3. Ở **Data source**: chọn **Entity** hoặc **Device**, chọn `RaspberryPi_Lab01`.
4. Ở **Data key**: loại **Timeseries** / **Telemetry**, key **`temperature`**.
5. Đặt nhãn `Nhiệt độ`, đơn vị `°C`, số thập phân `1`.
6. **Add/Apply** và lưu Dashboard.

**Lưu ý:** Nếu dropdown key trống, hãy xác nhận `temperature` đã xuất hiện trong **Latest telemetry** trước.

### 7.3. Thêm widget độ ẩm và khoảng cách

Lặp lại các bước trên:

| Widget | Data key | Đơn vị |
|---|---|---|
| Nhiệt độ | `temperature` | °C |
| Độ ẩm | `humidity` | % |
| Khoảng cách | `distance` | cm |

### 7.4. Thêm biểu đồ lịch sử

1. Trong Edit dashboard → **Add widget**.
2. Chọn nhóm **Charts** / **Time series**.
3. Chọn **Time series chart** hoặc **Line chart**.
4. Data source: `RaspberryPi_Lab01`.
5. Thêm Timeseries key `temperature` (có thể thêm `humidity`, nhưng nên dùng trục riêng nếu cần).
6. Chọn khoảng thời gian như **Last 1 hour** ở bộ chọn thời gian của dashboard/widget.
7. Apply → Save dashboard.

### 7.5. Hiển thị góc servo đã ra lệnh

1. Tạo thêm widget **Latest value**.
2. Data source: `RaspberryPi_Lab01`.
3. Data key type: **Attribute** (thường là client attribute).
4. Key: **`servoAngle`**.
5. Đặt nhãn `Góc servo đã ra lệnh`, đơn vị `°`.

Key `servoAngle` chỉ xuất hiện **sau khi đã gửi RPC thành công ít nhất một lần**.

## 8. Thêm widget điều khiển servo (RPC)

**Không cần tìm widget tên “Servo Control”.** ThingsBoard dùng widget điều khiển RPC tổng quát. Với code này, cách dễ nhất là **ba nút 0° / 90° / 180°**.

### 8.1. Thêm nút RPC đầu tiên

1. Mở Dashboard → **Edit** → **Add widget**.
2. Tìm nhóm **Control widgets** hoặc **Buttons**.
3. Tìm widget có tên **RPC Button** hoặc **Command button**. Nếu không thấy, dùng ô tìm kiếm `RPC`, `button`, `command`.
4. Chọn widget và đặt **Data source / Target device** = `RaspberryPi_Lab01`.
5. Mở tab **Settings**, **Behavior** hoặc **RPC settings** tùy loại widget.
6. Điền các giá trị tương đương dưới đây (nhãn trường có thể khác):

| Thuộc tính | Giá trị |
|---|---|
| Title / Label | `Servo 0°` |
| RPC type | **Server-side RPC** |
| Method | `setServoAngle` |
| Parameters / Params | `{"angle":0}` |
| One-way command | **OFF**, nếu có |
| Timeout | `5000` ms |

7. Chọn **Apply/Add** → **Save** Dashboard.

**Quan trọng:** Nếu widget có trường `RPC method params` nhận JSON, nhập **`{"angle":0}`**, không nhập toàn bộ JSON gồm `method` và `params`. ThingsBoard sẽ tự tạo gói RPC bao ngoài.

### 8.2. Thêm hai nút còn lại

Tạo/nhân bản nút và đổi:

| Nút | Method | Params |
|---|---|---|
| Servo 0° | `setServoAngle` | `{"angle":0}` |
| Servo 90° | `setServoAngle` | `{"angle":90}` |
| Servo 180° | `setServoAngle` | `{"angle":180}` |

Khi nhấn nút **Servo 90°**, payload gửi đến Pi có dạng:

```json
{"method":"setServoAngle","params":{"angle":90}}
```

Code `main.py` nhận lệnh và trả về:

```json
{"success":true,"angle":90.0}
```

Pi cũng gửi client attribute:

```json
{"servoAngle":90.0}
```

### 8.3. Nếu widget chỉ hỗ trợ `setValue` hoặc gửi số trực tiếp

Code hiện tại chấp nhận cả:

```json
{"method":"setServoAngle","params":90}
```

và:

```json
{"method":"setServoAngle","params":{"angle":90}}
```

Nhưng **method phải là `setServoAngle`**. Nếu widget cố định method `setValue`, cần chọn widget RPC khác hoặc sửa Python cho khớp; không nên đoán payload.

### 8.4. Slider 0–180° (tùy chọn)

Sau khi ba nút chạy được, có thể tìm widget **Slider** trong Control widgets. Chỉ dùng nếu phần cài đặt cho phép:
- Min `0`, Max `180`, Step `1`;
- Gửi **Server-side RPC**;
- Method `setServoAngle`;
- Params dạng `{"angle": <giá trị slider>}` hoặc số trực tiếp.

Một số slider mặc định chỉ ghi attribute hoặc dùng method khác. Nếu không cấu hình được, **giữ ba nút RPC**; đây là cách hoàn chỉnh cho Lab 01.

### 8.5. Kiểm tra trên terminal Pi

Giữ `./run.sh` chạy, nhấn **Servo 90°**:

```text
[RPC] Servo commanded to: 90.0
```

## 9. Tạo cảnh báo nhiệt độ trên ThingsBoard

Mục tiêu: **temperature > 30°C → tạo `High Temperature`**, khi `temperature <= 30°C` → clear alarm.

Tùy phiên bản ThingsBoard Cloud và quyền tài khoản, bạn có thể dùng **Device Profile Alarm Rules** hoặc **Rule Engine / Rule Chain**.

### 9.1. Cách ưu tiên: Alarm Rules trong Device Profile

1. Vào **Profiles → Device profiles** (hoặc **Device profiles**).
2. Mở profile mà `RaspberryPi_Lab01` đang sử dụng. Nếu là profile dùng chung, cân nhắc **tạo profile riêng cho Lab01** để không ảnh hưởng thiết bị khác.
3. Tìm tab **Alarm rules / Alarms**.
4. **Add alarm rule**:
   - Alarm type: `High Temperature`
   - Severity: `Warning`
   - Create condition: telemetry `temperature` **greater than 30**
   - Clear condition: telemetry `temperature` **less than or equal to 30**
5. Lưu profile và xác nhận `RaspberryPi_Lab01` được gán profile này.
6. Trên Dashboard, Add widget → nhóm **Alarms** → chọn **Alarms table** / widget danh sách alarm; data source là `RaspberryPi_Lab01`.

### 9.2. Nếu không thấy Alarm Rules

Trong **Rule Engine**, cần rule chain xử lý **POST_TELEMETRY** từ thiết bị, kiểm tra `temperature`, và các nhánh **Create alarm** / **Clear alarm**. Giao diện và node phụ thuộc phiên bản; không tự ý chỉnh rule chain mặc định đang dùng cho các thiết bị khác. Có thể tạo chain riêng cho Lab01 và cấu hình routing phù hợp.

**Để demo mà không làm nóng cảm biến:** tạm đổi ngưỡng trên ThingsBoard thành thấp hơn nhiệt độ phòng, kiểm tra alarm xuất hiện, sau đó đặt lại `30°C`. Không cần sửa code Pi.


