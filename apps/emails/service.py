from django.template.loader import render_to_string
from django.template import TemplateDoesNotExist
import logging

logger = logging.getLogger(__name__)


class EmailRenderer:
    TEMPLATES_DIR = 'emails'
    FALLBACK_CACHE = {}

    @classmethod
    def render(cls, template_name, context=None):
        context = context or {}
        safe_context = {
            'business_name': 'Auron Suite',
            'logo_url': '',
            'title': '',
            'content': '',
            'cta_url': '',
            'cta_label': 'Abrir enlace',
            'year': __import__('datetime').datetime.now().year,
            **(context or {}),
        }
        template_path = f'{cls.TEMPLATES_DIR}/{template_name}'
        try:
            return render_to_string(template_path, safe_context)
        except TemplateDoesNotExist:
            logger.warning('Template %s not found, using fallback', template_path)
            return cls._fallback_html(safe_context)

    @classmethod
    def _fallback_html(cls, ctx):
        logo = ''
        if ctx.get('logo_url'):
            logo = f'<img src="{ctx["logo_url"]}" alt="Logo" style="max-height:64px;max-width:180px;object-fit:contain;margin-bottom:12px;">'
        cta = ''
        if ctx.get('cta_url'):
            cta = f'<p style="margin:24px 0;"><a href="{ctx["cta_url"]}" style="background:#2563eb;color:#fff;text-decoration:none;padding:10px 16px;border-radius:8px;display:inline-block;font-weight:600;">{ctx.get("cta_label", "Abrir enlace")}</a></p>'
        return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;background:#f8fafc;font-family:Arial,sans-serif;">
<div style="max-width:620px;margin:0 auto;background:#fff;border:1px solid #e5e7eb;border-radius:12px;padding:24px;">
<div style="text-align:center;border-bottom:1px solid #e5e7eb;padding-bottom:12px;margin-bottom:16px;">
{logo}
<h2 style="margin:0;color:#111827;">{ctx["business_name"]}</h2>
</div>
<h3 style="margin:0 0 12px;color:#111827;">{ctx["title"]}</h3>
<div style="color:#374151;font-size:14px;line-height:1.6;">{ctx["content"]}</div>
{cta}
</div>
</body>
</html>"""
