from PIL import Image, ImageDraw, ImageFont
import io
import base64
import os
from datetime import datetime
from typing import Optional, Tuple


class WishCardGenerator:
    def __init__(self, width: int = 800, height: int = 1000):
        self.width = width
        self.height = height
        self.default_bg_colors = [
            "#FFE4E1",
            "#E0F7FA",
            "#F0FFF0",
            "#FFF8DC",
            "#F5F5DC",
            "#E6E6FA",
            "#FFEFD5",
            "#F0FFFF"
        ]
        self.decoration_colors = [
            "#FF6B6B",
            "#4ECDC4",
            "#45B7D1",
            "#96CEB4",
            "#FFEAA7",
            "#DDA0DD",
            "#98D8C8"
        ]

    def _get_font(self, size: int, font_type: str = "regular") -> ImageFont.FreeTypeFont:
        font_paths = [
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/simhei.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/PingFang.ttc"
        ]
        for path in font_paths:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size, encoding="utf-8")
                except:
                    continue
        return ImageFont.load_default()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        lines = []
        current_line = ""
        for char in text:
            test_line = current_line + char
            if font.getlength(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        if current_line:
            lines.append(current_line)
        return lines

    def _draw_decorations(self, draw: ImageDraw.ImageDraw):
        import random
        random.seed(datetime.now().microsecond)

        for _ in range(8):
            x = random.randint(0, self.width)
            y = random.randint(0, self.height)
            size = random.randint(15, 40)
            color = random.choice(self.decoration_colors)

            shape_type = random.choice(["circle", "star", "heart"])
            if shape_type == "circle":
                draw.ellipse([x, y, x + size, y + size], fill=color + "40", outline=color + "80", width=2)
            elif shape_type == "star":
                self._draw_star(draw, x, y, size, color + "60")
            elif shape_type == "heart":
                self._draw_heart(draw, x, y, size, color + "50")

    def _draw_star(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str):
        points = []
        for i in range(10):
            angle = i * 36 - 90
            import math
            radius = size / 2 if i % 2 == 0 else size / 4
            px = x + size / 2 + radius * math.cos(math.radians(angle))
            py = y + size / 2 + radius * math.sin(math.radians(angle))
            points.append((px, py))
        draw.polygon(points, fill=color)

    def _draw_heart(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str):
        import math
        points = []
        for t in range(0, 360, 5):
            rad = math.radians(t)
            px = x + size / 2 + 16 * (math.sin(rad) ** 3) * (size / 40)
            py = y + size / 2 - (13 * math.cos(rad) - 5 * math.cos(2 * rad) - 2 * math.cos(3 * rad) - math.cos(4 * rad)) * (size / 40)
            points.append((px, py))
        draw.polygon(points, fill=color)

    def _draw_rounded_rect(self, draw: ImageDraw.ImageDraw, xy: Tuple[int, int, int, int], radius: int, fill: str, outline: Optional[str] = None, width: int = 1):
        draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

    def generate_card(
        self,
        title: str,
        content: str,
        category: str,
        bg_color: Optional[str] = None,
        author_name: Optional[str] = None,
        created_at: Optional[datetime] = None
    ) -> str:
        if bg_color is None:
            import random
            bg_color = random.choice(self.default_bg_colors)

        bg_rgb = self._hex_to_rgb(bg_color)
        image = Image.new("RGB", (self.width, self.height), bg_rgb)
        draw = ImageDraw.Draw(image)

        self._draw_decorations(draw)

        padding = 60
        content_width = self.width - padding * 2
        y_offset = 80

        category_font = self._get_font(24, "bold")
        category_bg = "#FFFFFFC0"
        category_box_width = category_font.getlength(category) + 40
        self._draw_rounded_rect(
            draw,
            (padding, y_offset, padding + category_box_width, y_offset + 50),
            radius=25,
            fill=category_bg,
            outline="#33333340",
            width=1
        )
        draw.text(
            (padding + 20, y_offset + 12),
            category,
            font=category_font,
            fill="#333333"
        )
        y_offset += 80

        title_font = self._get_font(48, "bold")
        title_lines = self._wrap_text(title, title_font, content_width)
        for line in title_lines:
            draw.text(
                (padding, y_offset),
                line,
                font=title_font,
                fill="#2C3E50"
            )
            y_offset += 60
        y_offset += 20

        draw.line(
            [(padding, y_offset), (self.width - padding, y_offset)],
            fill="#33333330",
            width=2
        )
        y_offset += 40

        content_font = self._get_font(32)
        content_lines = self._wrap_text(content, content_font, content_width)
        for line in content_lines:
            draw.text(
                (padding, y_offset),
                line,
                font=content_font,
                fill="#555555"
            )
            y_offset += 50

        y_offset = self.height - 120

        if created_at:
            date_font = self._get_font(20)
            date_str = created_at.strftime("%Y年%m月%d日")
            draw.text(
                (padding, y_offset),
                date_str,
                font=date_font,
                fill="#888888"
            )

        if author_name:
            author_font = self._get_font(24, "bold")
            author_text = f"— {author_name}"
            author_width = author_font.getlength(author_text)
            draw.text(
                (self.width - padding - author_width, y_offset - 10),
                author_text,
                font=author_font,
                fill="#666666"
            )

        footer_bg = "#FFFFFF60"
        self._draw_rounded_rect(
            draw,
            (padding, self.height - 60, self.width - padding, self.height - 30),
            radius=15,
            fill=footer_bg
        )
        watermark_font = self._get_font(18)
        watermark = "✨ 许愿墙 · WishBloom ✨"
        wm_width = watermark_font.getlength(watermark)
        draw.text(
            ((self.width - wm_width) / 2, self.height - 55),
            watermark,
            font=watermark_font,
            fill="#999999"
        )

        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        img_bytes = buffer.getvalue()
        base64_str = base64.b64encode(img_bytes).decode("utf-8")

        return base64_str


def generate_wish_card(
    title: str,
    content: str,
    category: str,
    bg_color: Optional[str] = None,
    author_name: Optional[str] = None,
    created_at: Optional[datetime] = None
) -> str:
    generator = WishCardGenerator()
    return generator.generate_card(
        title=title,
        content=content,
        category=category,
        bg_color=bg_color,
        author_name=author_name,
        created_at=created_at
    )
