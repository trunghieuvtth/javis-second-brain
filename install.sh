#!/bin/bash
# ==============================================================================
# Javis Second Brain - 1-Click Installer for Linux & JavisOS
# ==============================================================================

set -e

INSTALL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="javis-second-brain"
PORT="${PORT:-8090}"

echo "=================================================================="
echo "   CÀI ĐẶT JAVIS SECOND BRAIN - KHO TRI THỨC SỐ & SOẠN THẢO NĐ 30"
echo "=================================================================="

# 1. Kiểm tra Python
if ! command -v python3 &>/dev/null; then
    echo "[!] Lỗi: Máy tính chưa cài đặt Python 3. Vui lòng cài Python 3 trước."
    exit 1
fi

# 2. Tạo môi trường ảo venv nếu chưa có
if [ ! -d "$INSTALL_DIR/venv" ]; then
    echo "[*] Đang khởi tạo môi trường ảo Python venv..."
    python3 -m venv "$INSTALL_DIR/venv"
fi

# 3. Kích hoạt venv và cài đặt thư viện
echo "[*] Đang cài đặt các thư viện cần thiết..."
"$INSTALL_DIR/venv/bin/pip" install --upgrade pip --quiet
"$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt" --quiet

# 4. Tạo thư mục dữ liệu
mkdir -p "$INSTALL_DIR/data/personal_brain/files"
mkdir -p "$INSTALL_DIR/data/drafts"

# 5. Cấu hình Systemd User Service tự khởi động cùng máy
SYSTEMD_USER_DIR="$HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_USER_DIR"

cat <<EOF > "$SYSTEMD_USER_DIR/$SERVICE_NAME.service"
[Unit]
Description=Javis Second Brain - Standalone Knowledge & ND30 Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment=PORT=$PORT
Environment=PYTHONUNBUFFERED=1
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/app.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

# 6. Kích hoạt và bật dịch vụ
echo "[*] Đang kích hoạt dịch vụ chạy ngầm..."
systemctl --user daemon-reload
systemctl --user enable "$SERVICE_NAME.service"
systemctl --user restart "$SERVICE_NAME.service"

# Kích hoạt linger để chạy ngầm 24/7 kể cả khi logout
loginctl enable-linger "$USER" 2>/dev/null || true

echo "=================================================================="
echo " [OK] CÀI ĐẶT THÀNH CÔNG JAVIS SECOND BRAIN!"
echo " Cổng truy cập cục bộ: http://127.0.0.1:$PORT"
echo " Trạng thái dịch vụ: systemctl --user status $SERVICE_NAME.service"
echo "=================================================================="
