import fitz  # PyMuPDF
import cv2
import numpy as np
import os

def extract_visual_image_regions(pdf_path, output_dir="visual_images", dpi=300):
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    image_count = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Step 1: 渲染整页为高分辨率图像
        zoom = dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Step 2: 用 OpenCV 读取并检测图像区域
        img = pixmap_to_cv2(pix)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 方法：用 Canny 边缘检测 + 轮廓筛选（适合流程图、框图）
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        regions = []
        min_area = 2000  # 像素²，过滤小噪点
        h_img, w_img = img.shape[:2]

        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            area = w * h
            if area > min_area and w > 50 and h > 50:
                # 扩大一点边界
                pad = 10
                x0 = max(0, x - pad)
                y0 = max(0, y - pad)
                x1 = min(w_img, x + w + pad)
                y1 = min(h_img, y + h + pad)
                regions.append((x0, y0, x1, y1))

        # 合并重叠区域（可选）
        regions = merge_overlapping_rects(regions)

        # Step 3: 裁剪并保存
        for (x0, y0, x1, y1) in regions:
            cropped = img[y0:y1, x0:x1]
            out_path = os.path.join(output_dir, f"vis_image_{image_count:03d}.png")
            cv2.imwrite(out_path, cropped)
            print(f"✅ Saved {out_path} from page {page_num + 1}")
            image_count += 1

    doc.close()
    print(f"\n🎉 Extracted {image_count} visual regions to '{output_dir}'")

# 辅助函数：合并重叠矩形
def merge_overlapping_rects(rects, iou_threshold=0.2):
    if not rects:
        return []
    boxes = np.array(rects, dtype="float")
    picked = []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    idxs = np.argsort(y2)

    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        picked.append(i)
        suppress = [last]

        for pos in range(0, last):
            j = idxs[pos]
            xx1 = max(x1[i], x1[j])
            yy1 = max(y1[i], y1[j])
            xx2 = min(x2[i], x2[j])
            yy2 = min(y2[i], y2[j])

            w = max(0, xx2 - xx1 + 1)
            h = max(0, yy2 - yy1 + 1)
            overlap = float(w * h) / area[j]
            if overlap > iou_threshold:
                suppress.append(pos)

        idxs = np.delete(idxs, suppress)
    return [rects[i] for i in picked]

# 将 Pixmap 转为 NumPy 数组（无需保存文件！）
def pixmap_to_cv2(pix):
    # 获取 bytes
    img_data = pix.samples
    # 注意通道数
    if pix.n == 4:  # RGBA
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 4)
        img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
    elif pix.n == 3:  # RGB
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    else:  # 灰度
        img = np.frombuffer(img_data, dtype=np.uint8).reshape(pix.h, pix.w)
    return img

if __name__ == "__main__":
    extract_visual_image_regions(pdf_path=r"D:\data-space\pythonProject\AIGC03_extract_picture\files\2024MCguidline.pdf",
                                   output_dir=r"D:\data-space\pythonProject\AIGC03_extract_picture\output")