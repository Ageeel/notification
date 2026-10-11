import os
import uuid
import mimetypes

import flet as ft
from supabase import create_client

from config import SUPABASE_URL, SUPABASE_ANON_KEY

BUCKET = "tamara"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


def main(page: ft.Page):
    page.title = "رفع صورة"
    page.rtl = True
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    status = ft.Text("", size=14)
    url_text = ft.Text("", selectable=True, size=12)
    ring = ft.ProgressRing(visible=False)
    preview = ft.Image(visible=False, width=300, fit=ft.ImageFit.CONTAIN)

    def set_busy(busy: bool):
        ring.visible = busy
        upload_btn.disabled = busy
        page.update()

    def show_error(msg: str):
        status.value = f"❌ {msg}"
        status.color = ft.colors.RED
        set_busy(False)

    def do_upload(data: bytes, filename: str):
        """يرفع bytes إلى Supabase Storage داخل bucket باسم tamara"""
        ext = os.path.splitext(filename)[1].lower() or ".jpg"
        # اسم عشوائي آمن (الأسماء العربية والمسافات تسبب مشاكل في Storage)
        remote_name = f"{uuid.uuid4().hex}{ext}"
        content_type = mimetypes.guess_type(filename)[0] or "image/jpeg"
        try:
            supabase.storage.from_(BUCKET).upload(
                remote_name,
                data,
                {"content-type": content_type, "upsert": "true"},
            )
            public_url = supabase.storage.from_(BUCKET).get_public_url(remote_name)
        except Exception as ex:
            show_error(f"فشل الرفع: {ex}")
            return

        status.value = "✅ تم رفع الصورة بنجاح"
        status.color = ft.colors.GREEN
        url_text.value = public_url
        preview.src = public_url
        preview.visible = True
        set_busy(False)

    def on_pick(e: ft.FilePickerResultEvent):
        if not e.files:
            return
        f = e.files[0]
        status.value = "جاري الرفع..."
        status.color = None
        set_busy(True)

        if f.path:
            # وضع التطبيق (ديسكتوب / موبايل): الملف متاح مباشرة بمساره
            try:
                with open(f.path, "rb") as fh:
                    data = fh.read()
            except Exception as ex:
                show_error(f"تعذر قراءة الملف: {ex}")
                return
            do_upload(data, f.name)
        else:
            # وضع الويب (هكذا يعمل Flet غالباً داخل Pydroid3):
            # يُرفع الملف أولاً إلى مجلد uploads ثم يُرسل إلى Supabase
            try:
                picker.upload(
                    [
                        ft.FilePickerUploadFile(
                            f.name,
                            upload_url=page.get_upload_url(f.name, 600),
                        )
                    ]
                )
            except Exception as ex:
                show_error(f"تعذر بدء الرفع: {ex}")

    def on_upload(e: ft.FilePickerUploadEvent):
        if e.error:
            show_error(f"خطأ أثناء رفع الملف: {e.error}")
            return
        if e.progress is not None and e.progress < 1:
            status.value = f"جاري الرفع... {int(e.progress * 100)}%"
            page.update()
            return

        local_path = os.path.join(UPLOAD_DIR, e.file_name)
        try:
            with open(local_path, "rb") as fh:
                data = fh.read()
        except Exception as ex:
            show_error(f"تعذر قراءة الملف المرفوع: {ex}")
            return
        finally:
            try:
                os.remove(local_path)
            except OSError:
                pass
        do_upload(data, e.file_name)

    picker = ft.FilePicker(on_result=on_pick, on_upload=on_upload)
    page.overlay.append(picker)

    upload_btn = ft.ElevatedButton(
        "اختيار صورة ورفعها",
        icon=ft.icons.UPLOAD,
        on_click=lambda _: picker.pick_files(
            file_type=ft.FilePickerFileType.IMAGE,
            allow_multiple=False,
        ),
    )

    page.add(
        ft.Text("رفع صورة إلى Supabase", size=22, weight=ft.FontWeight.BOLD),
        upload_btn,
        ring,
        status,
        preview,
        url_text,
    )


ft.app(target=main, upload_dir=UPLOAD_DIR)
