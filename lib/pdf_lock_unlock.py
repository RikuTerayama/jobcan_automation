# -*- coding: utf-8 -*-
"""
PDF ロック解除・ロック付与（サーバ側）
- 案B採用: 復号/暗号化をサーバで実行。パスワードはログ・永続化しない。
- 正しいパスワードを知っている前提のみ。推測/迂回は行わない。
"""
from io import BytesIO

from pypdf import PdfReader, PdfWriter


# 設計メモ: 案B（サーバ併用）を採用。
# 理由: 保護付与は pdf-lib でクライアント実装が困難なため、サーバで pypdf により確実に実装する。
# 保護解除も同一エンドポイントで行い、パスワードをログに出さず一時メモリのみで処理する。


def decrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """
    パスワード保護されたPDFを復号してバイト列で返す。
    非暗号化PDFの場合はそのまま返す。暗号化PDFでパスワード未入力は need_password、
    誤りは invalid_password を投げる。パスワードはログに一切出さない。
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    if not reader.is_encrypted:
        return pdf_bytes
    if not (password and password.strip()):
        raise ValueError("need_password")
    try:
        ok = reader.decrypt(password)
    except Exception:
        raise ValueError("invalid_password")
    if ok == 0:
        raise ValueError("invalid_password")
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()


def encrypt_pdf(pdf_bytes: bytes, password: str) -> bytes:
    """
    PDFにユーザーパスワードを付与して暗号化し、バイト列で返す。
    パスワードはログに一切出さない。
    """
    reader = PdfReader(BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password)
    out = BytesIO()
    writer.write(out)
    return out.getvalue()
