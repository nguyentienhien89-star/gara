"""
app.py - Tự động đẩy (push) thư mục lên GitHub mỗi 30 phút.

Cách dùng:
1. Cài Git: https://git-scm.com/downloads
2. Tạo Personal Access Token trên GitHub (quyền "repo"):
   GitHub > Settings > Developer settings > Personal access tokens
3. Sửa 3 dòng cấu hình bên dưới (FOLDER, REPO_URL, BRANCH)
4. Đặt token vào biến môi trường GITHUB_TOKEN (khuyến nghị)
   - Windows (CMD):  setx GITHUB_TOKEN "ghp_xxx"   (rồi mở lại CMD)
   - Linux/macOS:    export GITHUB_TOKEN="ghp_xxx"
5. Chạy:  python app.py
"""

import logging
import os
import subprocess
import time
from datetime import datetime

# ====================== CẤU HÌNH ======================
#FOLDER = r"C:\Users\TenBan\Documents\thu_muc_can_up"   # Thư mục cần đồng bộ_Window
FOLDER = r"/home/it/Gara"   # Thư mục cần đồng bộ
#REPO_URL = "https://github.com/username/ten-repo.git"  # Link repo GitHub
REPO_URL = "https://github.com/nguyentienhien89-star/gara.git"  # Link repo GitHub
BRANCH = "main"                                        # Nhánh để push
INTERVAL_MINUTES = 30                                  # Chu kỳ cập nhật (phút)
TOKEN = os.environ.get("GITHUB_TOKEN", "")             # Hoặc dán thẳng token vào đây
# =======================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync.log"), encoding="utf-8"),
    ],
)
log = logging.getLogger("github-sync")


def auth_url() -> str:
    """URL có kèm token để push/pull (không lưu vào .git/config)."""
    if TOKEN and REPO_URL.startswith("https://"):
        return REPO_URL.replace("https://", f"https://x-access-token:{TOKEN}@", 1)
    return REPO_URL


def git(*args, check=True):
    """Chạy lệnh git trong thư mục FOLDER, ẩn token khỏi log."""
    result = subprocess.run(
        ["git", *args], cwd=FOLDER, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    out = (result.stdout + result.stderr).strip()
    if TOKEN:
        out = out.replace(TOKEN, "***")
    if check and result.returncode != 0:
        raise RuntimeError(f"git {args[0]} lỗi: {out}")
    return result.returncode, out


def setup_repo():
    if not os.path.isdir(FOLDER):
        raise SystemExit(f"Thư mục không tồn tại: {FOLDER}")

    if not os.path.isdir(os.path.join(FOLDER, ".git")):
        log.info("Khởi tạo git repo trong %s", FOLDER)
        git("init")

    git("checkout", "-B", BRANCH, check=False)

    code, _ = git("remote", "get-url", "origin", check=False)
    if code != 0:
        git("remote", "add", "origin", REPO_URL)
    else:
        git("remote", "set-url", "origin", REPO_URL)


def sync_once():
    git("add", "-A")
    _, status = git("status", "--porcelain")
    if not status:
        log.info("Không có thay đổi, bỏ qua.")
        return

    msg = f"Auto update {datetime.now():%Y-%m-%d %H:%M:%S}"
    git("commit", "-m", msg)

    # Lấy thay đổi từ remote trước (nếu có) để tránh xung đột khi push
    git("pull", "--rebase", "--autostash", auth_url(), BRANCH, check=False)

    git("push", auth_url(), f"HEAD:{BRANCH}")
    log.info("Đã push thành công: %s", msg)


def main():
    if not TOKEN:
        log.warning("Chưa có GITHUB_TOKEN, sẽ dùng thông tin đăng nhập git có sẵn trên máy.")
    setup_repo()
    log.info("Bắt đầu theo dõi %s -> %s (mỗi %d phút)", FOLDER, REPO_URL, INTERVAL_MINUTES)

    while True:
        try:
            sync_once()
        except Exception as e:
            log.error("Lỗi khi đồng bộ: %s", e)
        time.sleep(INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Đã dừng.")
