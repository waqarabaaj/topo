import os
from PIL import Image, ImageDraw

ASSETS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'assets')
os.makedirs(ASSETS_DIR, exist_ok=True)


def create_yellow_router_icon(filename="router.png", size=(160, 160)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size[0] // 2, size[1] // 2 - 4
    rx, ry = 64, 34
    h_cyl = 24

    draw.ellipse([cx - rx - 4, cy - ry + h_cyl + 4, cx + rx + 4, cy + ry + h_cyl + 8], fill=(0, 0, 0, 80))
    draw.ellipse([cx - rx, cy - ry + h_cyl, cx + rx, cy + ry + h_cyl], fill=(161, 98, 7, 255))
    draw.rectangle([cx - rx, cy, cx + rx, cy + h_cyl], fill=(161, 98, 7, 255))

    for h in range(h_cyl, 0, -1):
        ratio = h / h_cyl
        r = int(234 + (161 - 234) * ratio)
        g = int(179 + (98 - 179) * ratio)
        b = int(8 + (7 - 8) * ratio)
        draw.ellipse([cx - rx, cy - ry + h, cx + rx, cy + ry + h], fill=(r, g, b, 255))

    draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(250, 204, 21, 255), outline=(254, 240, 138, 255), width=3)
    draw.ellipse([cx - rx + 4, cy - ry + 3, cx + rx - 4, cy + ry - 3], outline=(254, 249, 195, 210), width=1)

    ac = (30, 41, 59, 255)
    draw.line([(cx - 44, cy), (cx - 16, cy)], fill=ac, width=4)
    draw.polygon([(cx - 14, cy), (cx - 24, cy - 7), (cx - 24, cy + 7)], fill=ac)

    draw.line([(cx + 44, cy), (cx + 16, cy)], fill=ac, width=4)
    draw.polygon([(cx + 14, cy), (cx + 24, cy - 7), (cx + 24, cy + 7)], fill=ac)

    draw.line([(cx, cy - 5), (cx, cy - 20)], fill=ac, width=4)
    draw.polygon([(cx, cy - 24), (cx - 7, cy - 15), (cx + 7, cy - 15)], fill=ac)

    draw.line([(cx, cy + 5), (cx, cy + 20)], fill=ac, width=4)
    draw.polygon([(cx, cy + 24), (cx - 7, cy + 15), (cx + 7, cy + 15)], fill=ac)

    out_path = os.path.join(ASSETS_DIR, filename)
    img.save(out_path)
    return out_path


def create_blue_switch_icon(filename="switch.png", size=(160, 160)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w, h, depth = 114, 52, 20
    x0, y0 = (size[0] - w) // 2, (size[1] - h) // 2 - 6

    draw.rounded_rectangle([x0 - 3, y0 + depth + 4, x0 + w + 3, y0 + h + depth + 8], radius=10, fill=(0, 0, 0, 75))
    draw.rounded_rectangle([x0, y0 + depth, x0 + w, y0 + h + depth], radius=8, fill=(29, 78, 216, 255), outline=(30, 58, 138, 255), width=2)
    draw.rectangle([x0, y0 + h // 2, x0 + w, y0 + h + depth - 4], fill=(37, 99, 235, 255))

    for px in range(x0 + 12, x0 + w - 14, 14):
        draw.rectangle([px, y0 + h + 4, px + 8, y0 + h + 11], fill=(15, 23, 42, 255), outline=(147, 197, 253, 255))
        draw.rectangle([px + 2, y0 + h + 1, px + 5, y0 + h + 3], fill=(74, 222, 128, 255))

    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=(59, 130, 246, 255), outline=(191, 219, 254, 255), width=2)

    ac = (255, 255, 255, 255)
    draw.line([(x0 + 22, y0 + 18), (x0 + w - 26, y0 + 18)], fill=ac, width=4)
    draw.polygon([(x0 + w - 18, y0 + 18), (x0 + w - 28, y0 + 12), (x0 + w - 28, y0 + 24)], fill=ac)

    draw.line([(x0 + 26, y0 + 34), (x0 + w - 22, y0 + 34)], fill=ac, width=4)
    draw.polygon([(x0 + 18, y0 + 34), (x0 + 28, y0 + 28), (x0 + 28, y0 + 40)], fill=ac)

    out_path = os.path.join(ASSETS_DIR, filename)
    img.save(out_path)
    return out_path


def create_red_firewall_icon(filename="firewall.png", size=(160, 160)):
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    w, h, depth = 104, 64, 16
    x0, y0 = (size[0] - w) // 2, (size[1] - h) // 2 - 4

    draw.rounded_rectangle([x0 - 3, y0 + depth + 4, x0 + w + 3, y0 + h + depth + 8], radius=8, fill=(0, 0, 0, 80))
    draw.rounded_rectangle([x0, y0 + depth, x0 + w, y0 + h + depth], radius=8, fill=(153, 27, 27, 255), outline=(127, 29, 29, 255), width=2)
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=8, fill=(220, 38, 38, 255), outline=(254, 202, 202, 255), width=2)

    mortar = (254, 202, 202, 220)
    r1 = y0 + h // 3
    r2 = y0 + (2 * h) // 3
    draw.line([(x0 + 2, r1), (x0 + w - 2, r1)], fill=mortar, width=2)
    draw.line([(x0 + 2, r2), (x0 + w - 2, r2)], fill=mortar, width=2)

    draw.line([(x0 + w // 3, y0 + 2), (x0 + w // 3, r1)], fill=mortar, width=2)
    draw.line([(x0 + (2 * w) // 3, y0 + 2), (x0 + (2 * w) // 3, r1)], fill=mortar, width=2)

    draw.line([(x0 + w // 6, r1), (x0 + w // 6, r2)], fill=mortar, width=2)
    draw.line([(x0 + w // 2, r1), (x0 + w // 2, r2)], fill=mortar, width=2)
    draw.line([(x0 + (5 * w) // 6, r1), (x0 + (5 * w) // 6, r2)], fill=mortar, width=2)

    draw.line([(x0 + w // 3, r2), (x0 + w // 3, y0 + h - 2)], fill=mortar, width=2)
    draw.line([(x0 + (2 * w) // 3, r2), (x0 + (2 * w) // 3, y0 + h - 2)], fill=mortar, width=2)

    out_path = os.path.join(ASSETS_DIR, filename)
    img.save(out_path)
    return out_path


def generate_all_icons():
    create_yellow_router_icon()
    create_blue_switch_icon()
    create_red_firewall_icon()


if __name__ == '__main__':
    generate_all_icons()
