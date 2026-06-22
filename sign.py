#!/usr/bin/env python3
"""
皎月连 (natpierce.cn) 自动签到脚本
====================================
功能：
1. 登录皎月连
2. 检查签到是否可用
3. 如果可用则尝试签到（若需要验证码则推送通知提醒手动处理）
4. 通过 邮箱 / Server酱 / Telegram Bot / Bark 等渠道推送通知

用法：
    export NATPIERCE_USER="手机号"
    export NATPIERCE_PASS="密码"
    # （可选）推送通知，至少配置一个
    export MAIL_USER="your@qq.com"             # 发件邮箱（推荐 QQ邮箱/163邮箱）
    export MAIL_PASS="邮箱授权码"               # SMTP 授权码（不是登录密码）
    export MAIL_TO="接收通知的邮箱"             # 可选，默认同 MAIL_USER
    export SCT_KEY="Server酱发送密钥"           # https://sct.ftqq.com
    export TG_BOT_TOKEN="Telegram Bot Token"
    export TG_CHAT_ID="Telegram Chat ID"
    export BARK_KEY="Bark Key"                  # https://day.app
    python sign.py
"""

import os
import sys
import json
import logging
import smtplib

# 自动加载 .env 文件（优先于环境变量，方便本地测试）
_env_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.isfile(_env_file):
    with open(_env_file, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k, _v = _k.strip(), _v.strip().strip("\"'")
                if _k not in os.environ:
                    os.environ[_k] = _v


import urllib.parse
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta
from http.cookiejar import LWPCookieJar

try:
    import requests
except ImportError:
    print("缺少 requests 库，请运行: pip install requests")
    sys.exit(1)

# ============================================================
# 配置
# ============================================================

BASE_URL = "https://www.natpierce.cn"
LOGIN_URL = f"{BASE_URL}/pc/login/login.html"
SIGN_CHECK_URL = f"{BASE_URL}/pc/sign/qiandao_bf.html"
SIGN_URL = f"{BASE_URL}/pc/sign/qiandao.html"
SIGN_PAGE_URL = f"{BASE_URL}/pc/sign/index.html"

# 从环境变量读取
USERNAME = os.environ.get("NATPIERCE_USER", "")
PASSWORD = os.environ.get("NATPIERCE_PASS", "")

# 推送通知渠道（至少配置一个）
MAIL_USER = os.environ.get("MAIL_USER", "")         # 邮箱账号
MAIL_PASS = os.environ.get("MAIL_PASS", "")          # SMTP 授权码
MAIL_TO = os.environ.get("MAIL_TO", "") or MAIL_USER # 接收邮箱，默认同发件
MAIL_SMTP_HOST = os.environ.get("MAIL_SMTP_HOST", "")  # SMTP 服务器（可自动识别）
MAIL_SMTP_PORT = int(os.environ.get("MAIL_SMTP_PORT", "0"))  # SMTP 端口
SCT_KEY = os.environ.get("SCT_KEY", "")           # Server酱
TG_BOT_TOKEN = os.environ.get("TG_BOT_TOKEN", "")  # Telegram
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")      # Telegram
BARK_KEY = os.environ.get("BARK_KEY", "")          # Bark (iOS)

# 时区
CST = timezone(timedelta(hours=8))

# ============================================================
# 日志
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("natpierce-sign")

# 同时输出到文件
LOG_FILE = "sign.log"
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log.addHandler(file_handler)


# ============================================================
# 邮箱推送
# ============================================================

def _auto_smtp_config(email: str):
    """根据邮箱自动推断 SMTP 服务器和端口"""
    domain = email.split("@")[-1].lower()
    configs = {
        "qq.com":     ("smtp.qq.com", 465),
        "foxmail.com": ("smtp.qq.com", 465),
        "163.com":    ("smtp.163.com", 465),
        "126.com":    ("smtp.126.com", 465),
        "yeah.net":   ("smtp.yeah.net", 465),
        "gmail.com":  ("smtp.gmail.com", 587),
        "outlook.com": ("smtp-mail.outlook.com", 587),
        "hotmail.com": ("smtp-mail.outlook.com", 587),
        "sina.com":   ("smtp.sina.com", 465),
        "sohu.com":   ("smtp.sohu.com", 465),
    }
    return configs.get(domain, ("", 0))


def send_mail(title: str, content: str) -> str:
    """通过 SMTP 发送邮件通知，返回状态描述"""
    if not MAIL_USER or not MAIL_PASS:
        return "邮件未配置 ⚠️"

    # 确定 SMTP 配置
    host = MAIL_SMTP_HOST
    port = MAIL_SMTP_PORT
    if not host:
        host, port = _auto_smtp_config(MAIL_USER)
    if not host:
        return f"邮件 ❌ 无法识别邮箱 {MAIL_USER.split('@')[-1]}，请设置 MAIL_SMTP_HOST 和 MAIL_SMTP_PORT"

    use_ssl = (port == 465)
    if port == 0:
        port = 465
        use_ssl = True

    try:
        msg = MIMEText(content, "plain", "utf-8")
        msg["From"] = MAIL_USER
        msg["To"] = Header(MAIL_TO, "utf-8")
        msg["Subject"] = Header(title, "utf-8")

        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as smtp:
                smtp.login(MAIL_USER, MAIL_PASS)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as smtp:
                smtp.starttls()
                smtp.login(MAIL_USER, MAIL_PASS)
                smtp.send_message(msg)

        log.info("邮件推送成功 -> %s", MAIL_TO)
        return "邮件 ✅"
    except smtplib.SMTPAuthenticationError:
        return "邮件 ❌ 登录失败，请检查邮箱账号/授权码是否正确"
    except smtplib.SMTPException as e:
        return f"邮件 ❌ SMTP错误: {e}"
    except Exception as e:
        return f"邮件 ❌ {e}"


# ============================================================
# 推送通知
# ============================================================

def push_notify(title: str, content: str, status: str = "⚙️"):
    """通过配置的渠道推送通知"""
    full_title = f"{status} 皎月连签到 {title}"
    full_content = f"{content}\n\n---\n时间: {datetime.now(CST).strftime('%Y-%m-%d %H:%M:%S')}"

    results = []

    # 邮件（优先推荐，完全免费）
    if MAIL_USER and MAIL_PASS:
        results.append(send_mail(full_title, full_content))

    # Server酱
    if SCT_KEY:
        try:
            r = requests.post(
                f"https://sctapi.ftqq.com/{SCT_KEY}.send",
                data={"title": full_title, "desp": full_content},
                timeout=15,
            )
            data = r.json()
            if data.get("code") == 0:
                results.append("Server酱 ✅")
            else:
                results.append(f"Server酱 ❌ {data.get('message', '未知错误')}")
        except Exception as e:
            results.append(f"Server酱 ❌ {e}")

    # Telegram
    if TG_BOT_TOKEN and TG_CHAT_ID:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": TG_CHAT_ID,
                    "text": f"<b>{full_title}</b>\n\n{full_content}",
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            if r.json().get("ok"):
                results.append("Telegram ✅")
            else:
                results.append(f"Telegram ❌ {r.json().get('description', '未知错误')}")
        except Exception as e:
            results.append(f"Telegram ❌ {e}")

    # Bark (iOS)
    if BARK_KEY:
        try:
            r = requests.get(
                f"https://api.day.app/{BARK_KEY}/{urllib.parse.quote(full_title)}/{urllib.parse.quote(full_content)}",
                timeout=15,
            )
            if r.status_code == 200:
                results.append("Bark ✅")
            else:
                results.append(f"Bark ❌ HTTP {r.status_code}")
        except Exception as e:
            results.append(f"Bark ❌ {e}")

    if not results:
        log.warning("未配置任何推送渠道，请设置 MAIL_USER+MAIL_PASS / SCT_KEY / TG_BOT_TOKEN+TG_CHAT_ID / BARK_KEY")
        results.append("未配置推送渠道 ⚠️")

    log.info("推送结果: %s", " | ".join(results))
    return results


# ============================================================
# 签到逻辑
# ============================================================

def login(session: requests.Session) -> bool:
    """登录并返回是否成功"""
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Origin": BASE_URL,
        "Referer": f"{BASE_URL}/pc/login/login.html",
    }

    data = {"username": USERNAME, "password": PASSWORD}

    try:
        r = session.post(LOGIN_URL, data=data, headers=headers, timeout=15)
        result = r.json()
        log.info("登录响应: %s", result)

        if result.get("code") == 200:
            log.info("✅ 登录成功")
            return True
        else:
            log.error("❌ 登录失败: %s", result.get("message", "未知错误"))
            return False
    except Exception as e:
        log.error("❌ 登录请求异常: %s", e)
        return False


def check_sign(session: requests.Session) -> dict:
    """检查签到是否可用，返回响应 JSON"""
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": SIGN_PAGE_URL,
    }

    try:
        r = session.post(SIGN_CHECK_URL, headers=headers, timeout=15)
        result = r.json()
        log.info("签到检查响应: %s", result)
        return result
    except Exception as e:
        log.error("❌ 签到检查异常: %s", e)
        return {"code": -1, "message": f"请求异常: {e}"}


def do_sign(session: requests.Session) -> dict:
    """执行签到，返回响应 JSON"""
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": SIGN_PAGE_URL,
    }

    try:
        r = session.post(SIGN_URL, headers=headers, timeout=15)
        result = r.json()
        log.info("签到响应: %s", result)
        return result
    except Exception as e:
        log.error("❌ 签到请求异常: %s", e)
        return {"code": -1, "message": f"请求异常: {e}"}


def get_service_info(session: requests.Session) -> dict:
    """从签到页面解析服务信息"""
    try:
        r = session.get(SIGN_PAGE_URL, timeout=15)
        text = r.text

        info = {}

        # 解析服务到期时间
        import re
        expire_match = re.search(r'服务到期时间[：:]\s*([\d\-:\s]+)', text)
        if expire_match:
            info["expire_time"] = expire_match.group(1).strip()

        # 解析下次可签到时间
        next_sign_match = re.search(r'下次可签到时间[：:]\s*([\d\-:\s]+)', text)
        if next_sign_match:
            info["next_sign_time"] = next_sign_match.group(1).strip()

        return info
    except Exception as e:
        log.warning("解析服务信息失败: %s", e)
        return {}


# ============================================================
# 主函数
# ============================================================

def main():
    log.info("=" * 50)
    log.info("皎月连签到脚本启动")
    log.info("=" * 50)

    # 验证配置
    if not USERNAME or not PASSWORD:
        msg = "未设置 NATPIERCE_USER 和 NATPIERCE_PASS 环境变量"
        log.error("❌ %s", msg)
        push_notify("配置错误", msg, "❌")
        sys.exit(1)

    # 脱敏日志
    log.info("账号: %s****", USERNAME[:3] if len(USERNAME) > 3 else USERNAME[:1])

    session = requests.Session()

    # Step 1: 登录
    if not login(session):
        push_notify("登录失败", "请检查账号密码是否正确", "❌")
        sys.exit(1)

    # Step 2: 获取服务信息
    service_info = get_service_info(session)
    if service_info:
        log.info("服务到期: %s", service_info.get("expire_time", "未知"))
        log.info("下次签到: %s", service_info.get("next_sign_time", "未知"))

    # Step 3: 检查签到
    check_result = check_sign(session)
    code = check_result.get("code")
    message = check_result.get("message", "")

    if code == 200:
        # 签到可用！尝试签到
        log.info("🎯 签到可用，尝试签到...")
        sign_result = do_sign(session)

        if sign_result.get("code") == 200:
            msg = f"✅ 签到成功！\n{sign_result.get('message', '')}"
            log.info(msg)
            push_notify("签到成功", msg, "✅")
        elif sign_result.get("code") == 400 and "验证" in sign_result.get("message", ""):
            # 需要验证码
            msg = (
                f"⚠️ 签到需要验证码（网易易盾）\n"
                f"请手动打开链接签到：\n{SIGN_PAGE_URL}\n\n"
                f"服务器返回: {sign_result.get('message', '')}"
            )
            log.warning(msg)
            push_notify("需要验证码", msg, "⚠️")
        else:
            msg = f"❌ 签到失败: {sign_result.get('message', '未知错误')}"
            log.error(msg)
            push_notify("签到失败", msg, "❌")

    elif code == 400 and "无需签到" in message:
        # 服务尚未到期，无需签到
        next_time = service_info.get("next_sign_time", "未知")
        expire_time = service_info.get("expire_time", "未知")
        msg = (
            f"ℹ️ 当前无需签到\n"
            f"服务到期: {expire_time}\n"
            f"下次可签到: {next_time}"
        )
        log.info(msg)
        # 可以推也可以不推，避免频繁打扰
        # 仅当到期时间在3天内时推送提醒
        if expire_time != "未知":
            try:
                expire_dt = datetime.strptime(expire_time, "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                days_left = (expire_dt - now).days
                if 0 <= days_left <= 3:
                    push_notify("服务即将到期", msg, "⏰")
                else:
                    log.info("跳过推送（到期还早）")
            except:
                pass

    elif code == 400:
        # 其他业务错误
        msg = f"ℹ️ {message}"
        log.info(msg)

    else:
        msg = f"❌ 未知响应: code={code}, message={message}"
        log.error(msg)

    log.info("=" * 50)
    log.info("签到脚本执行完毕")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
